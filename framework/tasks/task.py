#!/usr/bin/env python
##
## TODO: update project's name
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program. If not, see <http://www.gnu.org/licenses/>.
##

import os
from datetime import datetime
from framework import logger
from framework import config
import time
import docker


class Task():
    
    default_image = None
    default_daemon = False
    default_config_file = None
    default_mount_point = '/home'

    def __init__(self, test_dir, configuration, controller, netMode):
        self.netMode = netMode
        self.controller = controller
        self.config = configuration
        self.test_dir = test_dir
        self.container = None
        self.root_password = None
        self.name = self.config.get("name", self.__class__.__name__)
        self.image = self.config.get("image", self.default_image)
        self.ip = self.config.get("ip")
        self.delay_start = self.config.get("delay_start", 0)
        self.mount_point = self.config.get("mount_point", self.default_mount_point)
        self.config_file = self.config.get("config_file", self.default_config_file)
        if self.config_file and not os.path.isabs(self.config_file):
            self.config_file = os.path.join(self.mount_point, self.config_file)
        self.daemon = self.config.get("daemon", self.default_daemon)
        if self.image is None:
            raise Exception("task {} does not have an image available".
                    format(self.name))

    def __str__(self):
        return self.name

    def get_task_args(self):
        return []

    def get_extra_params(self):
        """Returns extra parameters from the config"""
        if "extra_params" in self.config:
            extra_params = self.config["extra_params"].split(" ")
        else:
            extra_params = []
        return extra_params

    def get_ports(self):
        r = {}
        if "ports" in self.config:
            for p in self.config["ports"]:
                port, proto = p.split("/")
                r[p] = port
        return r
    

    def get_args(self):
        return self.get_task_args() + self.get_extra_params()

    def get_task_env(self):
        return {}

    def get_mount_point(self):
        return self.mount_point

    def run(self):
        #logger.slog.debug(str(datetime.utcnow()))
        logger.slog.debug("- Name: {}".format(self))
        logger.slog.debug("- Image: {}".format(self.image))
        logger.slog.debug("- Args: {}".format(self.get_args()))

        volumes = { self.test_dir: {
            "bind": self.get_mount_point(),
            "mode": "ro"
            }}
        ports = self.get_ports()
        env = self.get_task_env()
        logger.slog.debug("- Env: {}".format(env))
        net_mode = self.getNetMode()
        self.container = self.controller.docker.containers.create(
                self.image,
                self.get_args(),
                detach=True,
                volumes=volumes,
                ports=ports,
                name=self.name,
                environment=env,
                network_mode=net_mode)

        if net_mode == "bridge":
            try:
                self.connect()
            except docker.errors.APIError as err:
                logger.slog.critical(type(err))
        else: pass

        time.sleep(self.delay_start)
        try:
            self.container.start()
        except docker.errors.APIError as err:
            logger.slog.critical(type(err))
        

    def connect(self):
        if self.ip:
            self.controller.docker.networks.get(self.netMode).\
                    connect(self.container, ipv4_address = self.ip)    

    def getNetMode(self):
        if self.netMode == "host":
            return "host"
        else:
            return "bridge"

    def stop(self):
        self.container.stop()

    def get_exit_code(self):
        return self.container.attrs["State"]["ExitCode"]

    def update(self):
        self.container.reload()

    def remove(self):
        #self.container.remove()
        self.container = None

    def __del__(self):
        if self.container:
            self.container.stop()
            self.container.remove()

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
