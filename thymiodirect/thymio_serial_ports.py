# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
List of serial ports recognized as connected to a Thymio, or, if not
supported by the platform, of all serial ports.

Usage
-----

from thymiodirect.thymio_serial_ports import ThymioSerialPort
ports = ThymioSerialPort.get_ports()
port0 = ports[0]
device = port0.device

print(f"Thymio{' wireless' if port0.wireless else ''} ({device})")

or just

from thymiodirect.thymio_serial_ports import ThymioSerialPort
device = ThymioSerialPort.default_device()

"""

from typing import List, Optional, Tuple
import serial.tools.list_ports_common

USB_VID_EPFL = "0617"
USB_PID_THYMIO = "000A"
USB_PID_THYMIO_WIRELESS = "000C"
USB_VID_PID = {
    (USB_VID_EPFL, USB_PID_THYMIO),
    (USB_VID_EPFL, USB_PID_THYMIO_WIRELESS),
}


class ThymioSerialPort:

    def __init__(self,
                 port: Optional[serial.tools.list_ports_common.ListPortInfo] = None,
                 device: Optional[str] = None,
                 wireless: Optional[bool] = False):
        self.port = port
        self.device = device if device else port.device if port else None
        self.wireless = wireless

    def __str__(self):
        return ("Serial port" if self.port is None
                else "Thymio wireless" if self.wireless
                else "Thymio")

    def __repr__(self):
        return f"ThymioSerialPort(port={repr(self.port)}, device={repr(self.device)}, wireless={self.wireless})"

    @staticmethod
    def get_ports() -> List["ThymioSerialPort"]:
        """Get the list of serial ports a Thymio is connected to.
        """

        def check_hwid(hwid: str) -> Tuple[str, str]:
            for vid, pid in USB_VID_PID:
                if vid in hwid and pid in hwid:
                    return vid, pid

        try:
            from serial.tools.list_ports import comports
            ports = [
                ThymioSerialPort(port=port,
                                 wireless=check_hwid(port.hwid)[1] == USB_PID_THYMIO_WIRELESS)
                for port in comports()
                if check_hwid(port.hwid)
            ]
        except ValueError:
            # Probably thymiodirect.thymio_serial_ports isn't supported,
            # e.g. on macOS 11 as of December 2020
            from thymiodirect.connection import Connection
            ports = [
                ThymioSerialPort(device=device)
                for device in Connection.serial_ports()
            ]
        return ports

    @staticmethod
    def default_device() -> str:
        """Get the device string of the first Thymio serial port.
        """
        ports = ThymioSerialPort.get_ports()
        if len(ports) < 1:
            raise Exception("No serial device for Thymio found")
        return ports[0].device
