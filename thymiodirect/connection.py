# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Communication with Thymio via serial port or tcp
Author: Yves Piguet, EPFL
"""

import asyncio
import threading
import time
from typing import List, Optional, Set, Tuple

from thymiodirect.message import Message


class InputThread(threading.Thread):
    """Thread which reads messages asynchronously.
    """

    def __init__(self, io, loop=None, handle_msg=None):
        threading.Thread.__init__(self)
        self.running = True
        self.io = io
        self.loop = loop
        self.handle_msg = handle_msg
        self.comm_error = None

    def terminate(self) -> None:
        self.running = False

    def read_uint16(self) -> int:
        """Read an unsigned 16-bit number.
        """
        b = self.io.read(2)
        if len(b) == 0:
            raise TimeoutError()
        elif len(b) == 1:
            b1 = self.io.read(1)
            if len(b1) == 0:
                raise TimeoutError()
            return b[0] + 256 * b1[0]
        else:
            return b[0] + 256 * b[1]

    def read_message(self) -> Message:
        """Read a complete message.
        """
        try:
            payload_len = self.read_uint16()
            source_node = self.read_uint16()
            id = self.read_uint16()
            payload = self.io.read(payload_len)
            msg = Message(id, source_node, payload)
            return msg
        except Exception as error:
            self.comm_error = error
            raise error

    def run(self) -> None:
        """Input thread code.
        """
        while self.running:
            try:
                msg = self.read_message()
                msg.decode()
                if self.loop and self.handle_msg:
                    asyncio.ensure_future(self.handle_msg(msg), loop=self.loop)
            except TimeoutError:
                pass


class RemoteNode:
    """Remote node description and state.
    """

    def __init__(self, node_id: Optional[int] = None, version: Optional[int] = None):
        self.node_id = node_id
        self.version = version
        self.device_name = None
        self.device_uuid = None
        self.rf_network_id = None
        self.rf_node_id = None
        self.rf_channel = None
        self.last_msg_time = 0  # time.time()
        self.handshake_done = False
        self.name = None
        self.max_var_size = None
        self.num_named_var = None
        self.num_local_events = None
        self.num_native_fun = None
        self.var_total_size = 0
        self.named_variables = []  # names
        self.var_offset = {}  # indexed by name
        self.var_size = {}  # indexed by name
        self.var_data = []
        self.expected_var_end = 0  # beyond last var requested by ID_GET_VARIABLES
        self.var_received = False  # True if last set_var_data reached expected_var_end
        self.local_events = []  # names
        self.native_functions = []  # names
        self.native_functions_arg_sizes = {}  # indexed by name

    def __str__(self) -> str:
        return f"RemoteNode node_id={self.node_id} uuid={self.device_uuid}"

    def __repr__(self) -> str:
        return str(self)

    def add_var(self, name: str, size: int) -> None:
        """Add the definition of a variable.
        """
        self.named_variables.append(name)
        self.var_offset[name] = self.var_total_size
        self.var_size[name] = size
        self.var_total_size += size

    def reset_var_data(self) -> None:
        """Reset the variable data to 0.
        """
        self.var_data = [0 for i in range(self.var_total_size)]

    def get_var(self, name: str, index: int = 0) -> int:
        """Get the value of a scalar variable or an item in an array variable.
        """
        return self.var_data[self.var_offset[name] + index]

    def get_var_array(self, name: str) -> List[int]:
        """Get the value of an array variable.
        """
        if name not in self.var_offset:
            raise KeyError(name)
        offset = self.var_offset[name]
        return self.var_data[offset:offset + self.var_size[name]]

    def set_var(self, name: str, val: int, index: Optional[int] = 0) -> None:
        """Set the value of a scalar variable or an item in an array variable.
        """
        self.var_data[self.var_offset[name] + index] = val

    def set_var_array(self, name: str, val: List[int]) -> None:
        """Set the value of an array variable.
        """
        offset = self.var_offset[name]
        self.var_data[offset:offset + len(val)] = val

    def set_var_data(self, offset: int, data: List[int]) -> int:
        """Set values in the variable data array.
        """
        self.var_data[offset:offset + len(data)] = data
        self.var_received = offset + len(data) >= self.expected_var_end

    def data_span_for_variables(self, variables: Set[str]) -> Tuple[int, int]:
        """Find the offset and length of the span covering the set of variables.
        """
        offset = None
        length = 0
        for name in variables:
            if name not in self.var_offset:
                raise KeyError(name)
            if offset is None:
                offset = self.var_offset[name]
                length = self.var_size[name]
            elif self.var_offset[name] < offset:
                length += offset - self.var_offset[name]
                offset = self.var_offset[name]
                length = max(length, self.var_size[name])
            else:
                length = max(length, self.var_offset[name] + self.var_size[name] - offset)
        return offset, length

class Connection:
    """Connection to one or multiple devices.
    """

    class ThymioConnectionError(OSError):
        pass

    def __init__(self,
                 io,
                 host_node_id=1,
                 refreshing_rate=None, refreshing_coverage=None, discover_rate=None,
                 debug=False,
                 loop=None):
        self.loop = loop or asyncio.new_event_loop()
        self.terminating = False
        self.io = io
        self.debug = debug
        self.timeout = 3
        self.comm_error = None
        self.host_node_id = host_node_id
        self.auto_handshake = False
        self.remote_node_set = set()  # set of id of nodes with handshake done
        self.remote_nodes = {}  # key: node_id

        self.input_lock = threading.Lock()
        self.input_thread = InputThread(self.io, self.loop,
                                        lambda msg: self.handle_message(msg))
        self.input_thread.start()

        self.output_lock = threading.Lock()
        self.refreshing_timeout = None
        self.refreshing_data_coverage = None    # or set of variables to fetch
        self.refreshing_data_span = None   # or (offset, length) (based on refreshing_data_coverage)
        self.refreshing_triggers = []   # threading.Event
        if refreshing_rate is not None:
            self.set_refreshing_rate(refreshing_rate)
        if refreshing_coverage is not None:
            self.set_refreshing_coverage(refreshing_coverage)

        # callback for (dis)connection
        # async fun(node_id, connect)
        self.on_connection_changed = None

        # callback for notification that variables have been received
        # async fun(node_id)
        self.on_variables_received = None

        # callback for notification about execution state
        # async fun(node_id, pc, flags)
        self.on_execution_state_changed = None

        # callback for notification that an event has been emitted
        # async fun(node_id, event_id, event_args)
        self.on_user_event = None

        # callback for communication error notification
        # fun(error)
        self.on_comm_error = None

        # discover coroutine
        if discover_rate is not None:
            async def discover():
                while not self.terminating:
                    self.handshake()
                    await asyncio.sleep(discover_rate)
            self.loop.create_task(discover())

    def close(self) -> None:
        """Close connection.
        """
        if not self.io.closed:
            self.io.close()

    def shutdown(self) -> None:
        """Shutdown everything.
        """
        self.terminating = True
        self.input_thread.terminate()

    def run_forever(self) -> None:
        """Run asyncio loop forever.
        """
        self.loop.run_forever()

    def __del__(self) -> None:
        self.shutdown()
        self.close()

    def __enter__(self) -> None:
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.close()

    @staticmethod
    def serial_ports() -> List[str]:
        """Get the list of serial ports for the current platform.
        """
        import sys
        import os
        if sys.platform == "linux":
            devices = [
                "/dev/" + filename
                for filename in os.listdir("/dev")
                if filename.startswith("ttyACM")
            ]
        elif sys.platform == "darwin":
            devices = [
                "/dev/" + filename
                for filename in os.listdir("/dev")
                if filename.startswith("cu.usb")
            ]
        elif sys.platform == "win32":
            import subprocess, re
            mode_output = subprocess.check_output("mode", shell=True).decode()
            devices = [
                re.search(r"(COM\d+):", line).groups()[0]
                for line in mode_output.split("\n")
                if re.search(r"(COM\d+):", line)
            ]
        else:
            raise Connection.ThymioConnectionError("Unsupported platform")
        return devices

    @staticmethod
    def serial_default_port() -> str:
        """Get the name of the default Thymio serial port for the current
        platform.
        """
        import sys
        devices = Connection.serial_ports()
        if len(devices) < 1:
            raise Connection.ThymioConnectionError("No serial device for Thymio found")
        if sys.platform == "win32":
            return devices[len(devices) - 1]
        else:
            return devices[0]

    @staticmethod
    def serial(port: Optional[str] = None, **kwargs) -> "Connection":
        """Create Thymio object with a serial connection.
        """
        import serial  # pip3 install pyserial
        if port is None:
            port = Connection.serial_default_port()
        th = Connection(serial.Serial(port, timeout=1), **kwargs)
        return th

    @staticmethod
    def tcp(host: Optional[str] = "127.0.0.1", port: Optional[int] = 33333, **kwargs) -> "Connection":
        """Create Thymio object with a TCP connection.
        """
        import socket, io

        class TCPClientIO(io.RawIOBase):

            def __init__(self, host, port):
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((host, port))

            def read(self, n):
                return self.socket.recv(n)

            def write(self, b):
                self.socket.sendall(b)

        s = TCPClientIO(host, port)
        th = Connection(s, **kwargs)
        return th

    @staticmethod
    def null(host_node_id: Optional[int] = 1, **kwargs) -> "Connection":
        """Create Thymio object without connection.
        """
        import io

        class NullIO(io.RawIOBase):

            def read(self, n):
                return None

            def write(self, b):
                pass

        return Connection(NullIO(), host_node_id)

    def handshake(self) -> None:
        self.auto_handshake = True
        self.list_nodes()

    def wait_for_handshake(self, n: Optional[int] = 1, timeout: Optional[int] = 5) -> None:
        """Wait until n remote nodes have finished handshake
        """
        if len(self.remote_node_set) < n and not self.auto_handshake:
            self.handshake()
        count = timeout // 0.1
        while len(self.remote_node_set) < n:
            time.sleep(0.1)
            count -= 1
            if count < 0:
                raise TimeoutError()

    def one_remote_node_id(self) -> int:
        """Get the node id of one of the connected nodes.
        """
        return next(iter(self.remote_node_set))

    def set_refreshing_rate(self, rate: float) -> None:
        """Change the auto-refresh rate to update variables.
        """
        self.refreshing_timeout = rate
        if rate is not None:
            # refresh now
            for event in self.refreshing_triggers:
                event.set()

    def set_refreshing_coverage(self, variables: Optional[Set[str]] = None) -> None:
        """Set the variables which should be covered by auto-refresh
        (default: all).
        """
        self.refreshing_data_coverage = variables
        self.refreshing_data_span = None

    async def handle_message(self, msg: Message) -> None:
        """Handle an input message.
        """
        if self.debug:
            print("<", msg)
        source_node = msg.source_node
        if msg.id == Message.ID_NODE_PRESENT:
            will_do_handshake = False
            with self.input_lock:
                if source_node not in self.remote_nodes:
                    self.remote_nodes[source_node] = RemoteNode(source_node,
                                                                msg.version)
                    will_do_handshake = self.auto_handshake
            if will_do_handshake:
                if msg.version >= 6:
                    self.get_device_info(source_node)
                self.get_node_description(source_node)
        elif msg.id == Message.ID_DEVICE_INFO:
            change = False
            with self.input_lock:
                remote_node = self.remote_nodes[source_node]
                if msg.device_info == Message.DEVICE_INFO_NAME:
                    if remote_node.device_name != msg.device_name:
                        remote_node.device_name = msg.device_name
                        change = True
                elif msg.device_info == Message.DEVICE_INFO_UUID:
                    if remote_node.device_uuid != msg.device_uuid:
                        remote_node.device_uuid = msg.device_uuid
                        change = True
                elif msg.device_info == Message.DEVICE_INFO_THYMIO2_RF_SETTINGS:
                    if (remote_node.rf_network_id != msg.network_id
                        or remote_node.rf_node_id != msg.node_id
                        or remote_node.rf_channel != msg.channel):
                        remote_node.rf_network_id = msg.network_id
                        remote_node.rf_node_id = msg.node_id
                        remote_node.rf_channel = msg.channel
                        change = True
        elif msg.id == Message.ID_DESCRIPTION:
            with self.input_lock:
                self.remote_nodes[source_node].name = msg.node_name
                self.remote_nodes[source_node].bytecode_size = msg.bytecode_size
                self.remote_nodes[source_node].stack_size = msg.stack_size
                self.remote_nodes[source_node].max_var_size = msg.max_var_size
                self.remote_nodes[source_node].num_named_var = msg.num_named_var
                self.remote_nodes[source_node].num_local_events = msg.num_local_events
                self.remote_nodes[source_node].num_native_fun = msg.num_native_fun
        elif msg.id == Message.ID_NAMED_VARIABLE_DESCRIPTION:
            with self.input_lock:
                remote_node = self.remote_nodes[source_node]
                remote_node.add_var(msg.var_name, msg.var_size)
                if len(remote_node.named_variables) >= remote_node.num_named_var:
                    # all variables are known, can start refreshing
                    remote_node.reset_var_data()
                    async def do_refresh():
                        while not self.terminating:
                            if self.refreshing_timeout is None:
                                await asyncio.sleep(0.1)
                            else:
                                await asyncio.sleep(self.refreshing_timeout)
                                if self.refreshing_data_coverage is None:
                                    self.get_variables(source_node)
                                else:
                                    if self.refreshing_data_span is None:
                                        # update now that remote_node's variables are known
                                        self.refreshing_data_span = remote_node.data_span_for_variables(self.refreshing_data_coverage)
                                    if self.refreshing_data_span[1] > 0:
                                        self.get_variables(source_node, self.refreshing_data_span[0], self.refreshing_data_span[1])
                            # assume disconnection upon timeout
                            current_time = time.time()
                            terminating_nodes = set()
                            for node_id in self.remote_node_set:
                                with self.input_lock:
                                    terminated_node = self.remote_nodes[node_id]
                                    if current_time - terminated_node.last_msg_time > self.timeout:
                                        terminating_nodes.add(node_id)
                            for node_id in terminating_nodes:
                                self.remote_node_set.remove(node_id)
                                if self.on_connection_changed:
                                    await self.on_connection_changed(node_id, False)
                                del self.remote_nodes[node_id]
                        self.loop.stop()
                    self.loop.create_task(do_refresh())
        elif msg.id == Message.ID_VARIABLES:
            with self.input_lock:
                remote_node = self.remote_nodes[source_node]
                remote_node.set_var_data(msg.var_offset, msg.var_data)
            if self.on_variables_received and remote_node.var_received:
                await self.on_variables_received(source_node)
        elif msg.id == Message.ID_NATIVE_FUNCTION_DESCRIPTION:
            with self.input_lock:
                remote_node = self.remote_nodes[source_node]
                remote_node.native_functions.append(msg.fun_name)
                remote_node.native_functions_arg_sizes[msg.fun_name] = msg.param_sizes
            if len(remote_node.native_functions) >= remote_node.num_native_fun:
                # all messages sent as reply to GET_NODE_DESCRIPTION received
                self.remote_nodes[source_node].handshake_done = True
                if source_node not in self.remote_node_set:
                    self.remote_node_set.add(source_node)
                    if self.on_connection_changed:
                        await self.on_connection_changed(source_node, True)
        elif msg.id == Message.ID_LOCAL_EVENT_DESCRIPTION:
            with self.input_lock:
                remote_node = self.remote_nodes[source_node]
                remote_node.local_events.append(msg.event_name)
        elif msg.id == Message.ID_EXECUTION_STATE_CHANGED:
            if self.on_execution_state_changed:
                await self.on_execution_state_changed(source_node, msg.pc, msg.flags)
        elif msg.id < Message.ID_FIRST_ASEBA_ID:
            # user event sent by emit
            if self.on_user_event:
                await self.on_user_event(source_node, msg.id, msg.user_event_arg)
        self.remote_nodes[source_node].last_msg_time = time.time()

    def uuid_to_node_id(self, uuid: str) -> int:
        """Get node id from device uuid.
        """
        for node in self.remote_nodes.values():
            if node.device_uuid == uuid:
                return node.node_id

    def send(self, msg: Message) -> None:
        """Send a message.
        """
        with self.output_lock:
            if self.debug:
                print(">", msg)
            try:
                self.io.write(msg.serialize())
            except Exception as error:
                self.comm_error = error
                if self.on_comm_error:
                    self.on_comm_error(error)
                raise error

    def get_target_node_var_total_size(self, target_node_id):
        """Get the total size of variables.
        """
        with self.input_lock:
            return self.remote_nodes[target_node_id].var_total_size

    def list_nodes(self):
        """Send a LIST_NODES message.
        """
        payload = Message.uint16array_to_bytes([Message.PROTOCOL_VERSION])
        msg = Message(Message.ID_LIST_NODES, self.host_node_id, payload)
        self.send(msg)

    def get_node_description(self, target_node_id):
        """Send a GET_NODE_DESCRIPTION message.
        """
        payload = Message.uint16array_to_bytes([
            target_node_id,
            Message.PROTOCOL_VERSION
        ])
        msg = Message(Message.ID_GET_NODE_DESCRIPTION, self.host_node_id, payload)
        self.send(msg)

    def get_node_description_fragment(self, target_node_id, fragment):
        """Send a ID_GET_NODE_DESCRIPTION_FRAGMENT message.
        """
        payload = Message.uint16array_to_bytes([
            target_node_id,
            Message.PROTOCOL_VERSION,
            fragment
        ])
        msg = Message(Message.ID_GET_NODE_DESCRIPTION_FRAGMENT, self.host_node_id, payload)
        self.send(msg)

    def get_variables(self, target_node_id, chunk_offset=0, chunk_length=None):
        """Send a GET_VARIABLES message.
        """
        if target_node_id is not None:
            if chunk_length is None:
                chunk_length = (self.get_target_node_var_total_size(target_node_id)
                                - chunk_offset)
            payload = Message.uint16array_to_bytes([
                target_node_id,
                chunk_offset,
                chunk_length
            ])
            msg = Message(Message.ID_GET_VARIABLES, self.host_node_id, payload)
            self.remote_nodes[target_node_id].expected_var_end = chunk_offset + chunk_length
            self.send(msg)

    def set_variables(self, target_node_id, chunk_offset, chunk):
        """Send a SET_VARIABLES message.
        """
        payload = Message.uint16array_to_bytes([
            target_node_id,
            chunk_offset
        ] + chunk)
        msg = Message(Message.ID_SET_VARIABLES, self.host_node_id, payload)
        self.send(msg)

    def variable_description(self, target_node_id):
        """Get an array with the description of all variables, with fields
        "name", "offset" and "size".
        """
        node = self.remote_nodes[target_node_id]
        return [
            {
                "name": key,
                "offset": node.var_offset[key],
                "size": node.var_size[key]
            }
            for key in node.var_offset.keys()
        ]

    def get_var(self, target_node_id, name, index=0):
        """Get the value of a scalar variable from the local copy.
        """
        node = self.remote_nodes[target_node_id]
        with self.input_lock:
            return node.get_var(name, index)

    def get_var_array(self, target_node_id, name):
        """Get the value of an array variable from the local copy.
        """
        node = self.remote_nodes[target_node_id]
        try:
            with self.input_lock:
                return node.get_var_array(name)
        except KeyError:
            raise KeyError(name)

    def set_var(self, target_node_id, name, val, index=0):
        """Set the value of a scalar variable in the local copy and send it.
        """
        node = self.remote_nodes[target_node_id]
        with self.input_lock:
            node.set_var(name, val, index)
        self.set_variables(target_node_id, node.var_offset[name] + index, [val])

    def set_var_array(self, target_node_id, name, val):
        """Set the value of an array variable in the local copy and send it.
        """
        node = self.remote_nodes[target_node_id]
        with self.input_lock:
            node.set_var_array(name, val)
        self.set_variables(target_node_id, node.var_offset[name], val)

    def __getitem__(self, key):
        class Node:

            def __init__(self_node, connection, node_id):
                self_node.connection = connection
                self_node.node_id = node_id

            def __getitem__(self_node, name):
                try:
                    val = self_node.connection.get_var_array(self_node.node_id, name)
                    return val if len(val) != 1 else val[0]
                except KeyError:
                    raise KeyError(name)

            def __setitem__(self_node, name, val):
                try:
                    if isinstance(val, list):
                        self_node.connection.set_var_array(self_node.node_id, name, val)
                    else:
                        self_node.connection.set_var(self_node.node_id, name, val)
                except KeyError:
                    raise KeyError(name)

        return Node(self, key)

    def set_bytecode(self, target_node_id, bytecode, address=0):
        """Set the bytecode by sending one or more SET_BYTECODE messages.
        """
        size = len(bytecode)
        i = 0
        while i < size:
            size_chunk = min(size - i, 256)
            payload = Message.uint16array_to_bytes([
                target_node_id,
                address + i
            ] + bytecode[i:i + size_chunk])
            msg = Message(Message.ID_SET_BYTECODE, self.host_node_id, payload)
            self.send(msg)
            i += size_chunk

    def reset(self, target_node_id):
        """Reset the Thymio.
        """
        payload = Message.uint16array_to_bytes([
            target_node_id,
        ])
        msg = Message(Message.ID_RESET, self.host_node_id, payload)
        self.send(msg)

    def run(self, target_node_id):
        """Run the code on the Thymio.
        """
        payload = Message.uint16array_to_bytes([
            target_node_id,
        ])
        msg = Message(Message.ID_RUN, self.host_node_id, payload)
        self.send(msg)

    def get_device_info(self, target_node_id, info=None):
        """Request device info (all available by default).
        """
        if info is None:
            self.get_device_info(target_node_id,
                                 Message.DEVICE_INFO_NAME)
            self.get_device_info(target_node_id,
                                 Message.DEVICE_INFO_THYMIO2_RF_SETTINGS)
            self.get_device_info(target_node_id,
                                 Message.DEVICE_INFO_UUID)
        else:
            payload = Message.uint16array_to_bytes([
                target_node_id,
                info
            ])
            msg = Message(Message.ID_GET_DEVICE_INFO, self.host_node_id, payload)
            self.send(msg)
