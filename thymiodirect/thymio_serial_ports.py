# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
List of serial ports recognized as connected to a Thymio.

Usage
-----

from thymiodirect.thymio_serial import ThymioSerialPort
ports = ThymioSerialPort.get_ports()
port0 = ports[0]
device = port0.device

print(f"Thymio{' wireless' if port0.wireless else ''} ({device})")

"""

import serial.tools.list_ports_common
from serial.tools.list_ports import comports
from typing import Awaitable, Callable, List, Optional, Set, Tuple

USB_VID_EPFL = "0617"
USB_PID_THYMIO = "000A"
USB_PID_THYMIO_WIRELESS = "000C"
USB_VID_PID = {
    (USB_VID_EPFL, USB_PID_THYMIO),
    (USB_VID_EPFL, USB_PID_THYMIO_WIRELESS),
}

class ThymioSerialPort:

    def __init__(self, port: serial.tools.list_ports_common.ListPortInfo, wireless: bool):
        self.port = port
        self.device = port.device
        self.wireless = wireless

    def __repr__(self):
        return f"Thymio{' wireless' if self.wireless else ''} .device={self.device}"

    @staticmethod
    def get_ports() -> List["ThymioSerialPort"]:
        """Get the list of serial ports a Thymio is connected to.
        """

        def check_hwid(hwid: str) -> Tuple[str, str]:
            for vid, pid in USB_VID_PID:
                if vid in hwid and pid in hwid:
                    return vid, pid

        devices = [
            ThymioSerialPort(port, check_hwid(port.hwid)[1] == USB_PID_THYMIO_WIRELESS)
            for port in comports()
            if check_hwid(port.hwid)
        ]
        return devices