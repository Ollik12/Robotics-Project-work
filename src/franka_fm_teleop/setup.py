from setuptools import find_packages, setup

package_name = 'franka_fm_teleop'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='developer',
    maintainer_email='188858515+iikkaop@users.noreply.github.com',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'ps5_teleop_node = franka_fm_teleop.ps5_teleop:main',
            'keyboard_teleop_node = franka_fm_teleop.keyboard_teleop:main',
        ],
    },
)
