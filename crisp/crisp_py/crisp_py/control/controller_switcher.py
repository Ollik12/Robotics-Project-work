"""Script to switch to a different ros2_controller."""

import rclpy
from controller_manager_msgs.srv import (
    ConfigureController,
    LoadController,
    SwitchController,
)
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.node import Node
from std_srvs.srv import Trigger
from types import SimpleNamespace
import json


class ControllerSwitcherClient:
    """ControllerSwitcher class allows user to communicate with the controller_manager and manage controllers in an easy way."""

    def __init__(
        self,
        node: Node,
    ):
        """Initialize the ControllerSwitcher.

        Args:
            node (Node): Node used for the communication with the controller_manager.
        """
        self.node = node

        self.load_client = node.create_client(
            LoadController,
            "controller_manager/load_controller",
            callback_group=ReentrantCallbackGroup(),
        )
        self.configure_client = node.create_client(
            ConfigureController,
            "controller_manager/configure_controller",
            callback_group=ReentrantCallbackGroup(),
        )
        # Own custom controller_manager_bridge package is used to list controllers through a compatibility bridge
        # The bridge is needed because the Docker side list_controllers service is not compatible with CRISP controller-msgs 4.25
        self.list_client = node.create_client(
            Trigger,
            "/crisp_compat/list_controllers",
            callback_group=ReentrantCallbackGroup(),
        )
        self.switch_client = node.create_client(
            SwitchController,
            "controller_manager/switch_controller",
            callback_group=ReentrantCallbackGroup(),
        )

    def is_server_ready(self) -> bool:
        """Return True if all services are ready."""
        return (
            self.load_client.wait_for_service(timeout_sec=5.0)
            and self.configure_client.wait_for_service(timeout_sec=5.0)
            and self.list_client.wait_for_service(timeout_sec=5.0)
            and self.switch_client.wait_for_service(timeout_sec=5.0)
        )

    # Modified version of the get_controller_list method that uses the compatibility bridge to 
    # retrieve the list of controllers
    def get_controller_list(self) -> list:
        """Get controllers through the compatibility bridge."""

        if not self.list_client.wait_for_service(timeout_sec=5.0):
            raise RuntimeError("Controller list bridge unavailable.")

        future = self.list_client.call_async(Trigger.Request())

        while not future.done():
            pass

        response = future.result()

        if response is None or not response.success:
            raise RuntimeError("Failed to retrieve controller list.")

        controllers = json.loads(response.message)

        return [
            SimpleNamespace(**controller)
            for controller in controllers
        ]

    def load_controller(self, controller_name: str) -> bool:
        """Load a controller using a service."""
        request = LoadController.Request()
        request.name = controller_name
        future = self.load_client.call_async(request)

        while not future.done():
            self.node.get_logger().debug(
                "Waiting for load controller answer...", throttle_duration_sec=1.0
            )
        response = future.result()

        return response.ok

    def configure_controller(self, controller_name: str) -> bool:
        """Configure a controller using a service."""
        request = ConfigureController.Request()
        request.name = controller_name
        future = self.configure_client.call_async(request)

        while not future.done():
            self.node.get_logger().debug(
                "Waiting for configure controller answer...", throttle_duration_sec=1.0
            )
        response = future.result()

        return response.ok

    def _switch_controller(self, to_deactivate: list[str], to_activate: list[str]) -> bool:
        """Switch to a different ros2_controller using a service."""
        request = SwitchController.Request()
        request.deactivate_controllers = to_deactivate
        request.activate_controllers = to_activate
        request.strictness = SwitchController.Request.BEST_EFFORT
        request.activate_asap = True
        request.timeout = rclpy.duration.Duration(seconds=5).to_msg()

        future = self.switch_client.call_async(request)

        while not future.done():
            self.node.get_logger().debug(
                "Waiting for switch controller answer...", throttle_duration_sec=1.0
            )
        response = future.result()

        return response.ok

    def switch_controller(
        self,
        controller_name: str,
        controllers_that_should_be_active: list[str] | None = None,
    ) -> bool | None:
        """Switch to a different ros2_controller that is already loaded using a service.

        First we request a list of current controllers.
        If the desired controller is not loaded, then we request to load it and configure it.
        Then we prepare a list of controllers to deactivate (all active controllers except broadcasters and those that should remain active).
        We also prepare a list of controllers to activate (the desired controller and those that should remain active).
        Finally, we request to switch to the desired controllers.

        Args:
            controller_name (str): Name of the controller to switch to.
            controllers_that_should_be_active (list[str] | None): List of controller names to keep active or activate in the switch. Defaults to None.
        """
        if controllers_that_should_be_active is None:
            controllers_that_should_be_active = []

        controllers = self.get_controller_list()

        active_controllers = [
            controller.name for controller in controllers if controller.state == "active"
        ]
        inactive_controllers = [
            controller.name for controller in controllers if controller.state == "inactive"
        ]

        if controller_name in active_controllers:
            self.node.get_logger().debug(f"Controller {controller_name} is already active.")
            return True

        if controller_name not in inactive_controllers:
            self._try_loading_and_configuring_controller(controller_name)

        to_deactivate = []
        for active_controller in active_controllers:
            if active_controller in controllers_that_should_be_active:
                continue  # Keep this controller active

            if active_controller.endswith("broadcaster"):  # Do not deactivate broadcasters
                continue

            to_deactivate.append(active_controller)

        to_activate = [
            inactive_controller
            for inactive_controller in inactive_controllers
            if inactive_controller in controllers_that_should_be_active
        ] + [controller_name]

        ok = self._switch_controller(to_deactivate, to_activate)

        if not ok:
            self.node.get_logger().error(f"Failed to switch to controller {controller_name}.")
            raise RuntimeError(f"Failed to switch to controller {controller_name}.")

        return True

    def _try_loading_and_configuring_controller(self, controller_name: str) -> None:
        """Try to load and configure a controller.

        Args:
            controller_name (str): Name of the controller to load and configure.
        """
        ok = self.load_controller(controller_name)
        if not ok:
            self.node.get_logger().error(
                f"Failed to load controller {controller_name}. Are you sure the controller exists?"
            )
            raise RuntimeError(f"Failed to load controller {controller_name}.")

        ok = self.configure_controller(controller_name)
        if not ok:
            self.node.get_logger().error(f"Failed to configure controller {controller_name}.")
            raise RuntimeError(f"Failed to configure controller {controller_name}.")
