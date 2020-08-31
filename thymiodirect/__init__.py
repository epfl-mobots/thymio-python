# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Communication with Thymio II robot
==================================

This module provides support to connect to a Thymio II robot with its native
binary protocol via a serial port (virtual port over a wired USB or wireless
USB dongle) or a TCP port (asebaswitch or Thymio simulator).

Example
-------

# import the required classes
from thymiodirect import Connection
from thymiodirect import Thymio

# set the serial port the Thymio is connected to
# (depending on your configuration, the default port is not what you want)
port = Connection.serial_default_port()

# create a Thymio connection object with a callback to be notified when
# the robot is ready and start the connection (or just wait a few seconds)
th = Thymio(serial_port=port,
            on_connect=lambda node_id:print(f"{node_id} is connected"))
th.connect()

# get id of the first (or only) Thymio
id = th.first_node()

# get a variable
th[id]["prox.horizontal"]

# set a variable (scalar or array)
th[id]["leds.top"] = [0, 0, 32]

# define a function called after new variable values have been fetched
prox_prev = 0
def obs(node_id):
    global prox_prev
    prox = (th[node_id]["prox.horizontal"][5]
            - th[node_id]["prox.horizontal"][2]) // 10
    if prox != prox_prev:
        th[node_id]["motor.left.target"] = prox
        th[node_id]["motor.right.target"] = prox
        print(prox)
        if prox > 5:
            th[id]["leds.top"] = [0, 32, 0]
        elif prox < -5:
            th[id]["leds.top"] = [32, 32, 0]
        elif abs(prox) < 3:
            th[id]["leds.top"] = [0, 0, 32]
        prox_prev = prox
    if th[node_id]["button.center"]:
        print("button.center")
        os._exit(0) # forced exit despite coroutines

# install this function
th.set_variable_observer(id, obs)
"""

from thymiodirect.connection import Connection
from thymiodirect.thymio import Thymio
