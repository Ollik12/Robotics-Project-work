#!/usr/bin/env python3

import json
import threading

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from std_srvs.srv import Trigger
from controller_manager_msgs.srv import ListControllers


class ControllerListBridge(Node):

    def __init__(self):
        super().__init__("controller_list_bridge")

        self.callback_group = ReentrantCallbackGroup()

        self.controller_client = self.create_client(
            ListControllers,
            "/controller_manager/list_controllers",
            callback_group=self.callback_group,
        )

        self.bridge_service = self.create_service(
            Trigger,
            "/crisp_compat/list_controllers",
            self.handle_request,
            callback_group=self.callback_group,
        )

        self.get_logger().info("Controller list bridge ready")

    def handle_request(self, request, response):

        if not self.controller_client.wait_for_service(timeout_sec=2.0):
            response.success = False
            response.message = "Controller manager unavailable"
            return response

        future = self.controller_client.call_async(
            ListControllers.Request()
        )

        completed = threading.Event()
        future.add_done_callback(lambda _: completed.set())

        if not completed.wait(timeout=5.0):
            response.success = False
            response.message = "Controller list request timed out"
            return response

        try:
            result = future.result()

            controllers = [
                {
                    "name": controller.name,
                    "state": controller.state,
                }
                for controller in result.controller
            ]

            response.success = True
            response.message = json.dumps(controllers)

        except Exception as exc:
            response.success = False
            response.message = str(exc)

        return response


def main():
    rclpy.init()
    node = ControllerListBridge()
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()