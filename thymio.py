# Communication with Thymio via serial port or tcp
# Author: Yves Piguet, EPFL

import asyncio
import threading
import time
import uuid

class Message:
    """Aseba message data.
    """

    # v5
    ID_BOOTLOADER_RESET = 0x8000
    ID_BOOTLOADER_READ_PAGE = 0x8001
    ID_BOOTLOADER_WRITE_PAGE = 0x8002
    ID_BOOTLOADER_PAGE_DATA_WRITE = 0x8003
    ID_BOOTLOADER_DESCRIPTION = 0x8004
    ID_BOOTLOADER_PAGE_DATA_READ = 0x8005
    ID_BOOTLOADER_ACK = 0x8006
    ID_DESCRIPTION = 0x9000
    ID_NAMED_VARIABLE_DESCRIPTION = 0x9001
    ID_LOCAL_EVENT_DESCRIPTION = 0x9002
    ID_NATIVE_FUNCTION_DESCRIPTION = 0x9003
    ID_VARIABLES = 0x9005
    ID_EXECUTION_STATE_CHANGED = 0x900a
    ID_NODE_PRESENT = 0x900c
    ID_DEVICE_INFO = 0x900d
    ID_CHANGED_VARIABLES = 0x900e
    ID_GET_DESCRIPTION = 0xa000
    ID_SET_BYTECODE = 0xa001
    ID_RESET = 0xa002
    ID_RUN = 0xa003
    ID_PAUSE = 0xa004
    ID_STEP = 0xa005
    ID_STOP = 0xa006
    ID_GET_EXECUTION_STATE = 0xa007
    ID_BREAKPOINT_SET = 0xa008
    ID_BREAKPOINT_CLEAR = 0xa009
    ID_BREAKPOINT_CLEAR_ALL = 0xa00a
    ID_GET_VARIABLES = 0xa00b
    ID_SET_VARIABLES =  0xa00c
    ID_GET_NODE_DESCRIPTION = 0xa010
    ID_LIST_NODES = 0xa011
    # v6
    ID_GET_DEVICE_INFO = 0xa012
    ID_SET_DEVICE_INFO = 0xa013
    # v7
    ID_GET_CHANGED_VARIABLES = 0xa014
    # v8
    ID_GET_NODE_DESCRIPTION_FRAGMENT = 0xa015

    PROTOCOL_VERSION = 5

    DEVICE_INFO_UUID = 1
    DEVICE_INFO_NAME = 2
    DEVICE_INFO_THYMIO2_RF_SETTINGS = 3

    def __init__(self, id, source_node, payload):
        self.id = id
        self.source_node = source_node
        self.payload = payload

    def get_uint8(self, offset):
        """Get an unsigned 8-bit integer in the payload.
        """
        return self.payload[offset], offset + 1

    def get_uint16(self, offset):
        """Get an unsigned 16-bit integer in the payload.
        """
        return self.payload[offset] + 256 * self.payload[offset + 1], offset + 2

    def get_string(self, offset):
        """Get a string in the payload.
        """
        len = self.payload[offset]
        str = self.payload[offset + 1 : offset + 1 + len]
        return str.decode('utf-8'), offset + 1 + len

    @staticmethod
    def uint16_to_bytes(word):
        """Convert an unsigned 16-bit integer to bytes.
        """
        return bytes([word % 256, word // 256])

    @staticmethod
    def uint16array_to_bytes(a):
        """Convert an array of unsigned 16-bit integer to bytes.
        """
        bytes = b"";
        for word in a:
            bytes += Message.uint16_to_bytes(word)
        return bytes

    def decode(self):
        """Decode message properties from its payload.
        """
        if self.id == Message.ID_DESCRIPTION:
            self.node_name, offset = self.get_string(0)
            self.protocol_version, offset = self.get_uint16(offset)
            self.bytecode_size, offset = self.get_uint16(offset)
            self.stack_size, offset = self.get_uint16(offset)
            self.max_var_size, offset = self.get_uint16(offset)
            self.num_named_var, offset = self.get_uint16(offset)
            self.num_local_events, offset = self.get_uint16(offset)
            self.num_native_fun, offset = self.get_uint16(offset)
        elif self.id == Message.ID_NAMED_VARIABLE_DESCRIPTION:
            self.var_size, offset = self.get_uint16(0)
            self.var_name, offset = self.get_string(offset)
        elif self.id == Message.ID_LOCAL_EVENT_DESCRIPTION:
            self.event_name, offset = self.get_string(0)
            self.description, offset = self.get_string(offset)
        elif self.id == Message.ID_NATIVE_FUNCTION_DESCRIPTION:
            self.fun_name, offset = self.get_string(0)
            self.description, offset = self.get_string(offset)
            num_params, offset = self.get_uint16(offset)
            self.param_names = []
            self.param_sizes = []
            for i in range(num_params):
                size, offset = self.get_uint16(offset)
                name, offset = self.get_string(offset)
                self.param_names.append(name)
                self.param_sizes.append(size)
        elif self.id == Message.ID_VARIABLES:
            self.var_offset, offset = self.get_uint16(0)
            self.var_data = []
            for i in range(len(self.payload) // 2 - 1):
                word, offset = self.get_uint16(offset)
                self.var_data.append(word)
        elif self.id == Message.ID_NODE_PRESENT:
            self.version, offset = self.get_uint16(0)
        elif self.id == Message.ID_DEVICE_INFO:
            self.device_info, offset = self.get_uint8(0)
            if self.device_info == Message.DEVICE_INFO_NAME:
                self.device_name, offset = self.get_string(offset)
            elif self.device_info == Message.DEVICE_INFO_UUID:
                data_len, offset = self.get_uint8(offset)
                data = self.payload[offset : offset + data_len]
                self.device_uuid = str(uuid.UUID(bytes=data))
            elif self.device_info == Message.DEVICE_INFO_THYMIO2_RF_SETTINGS:
                data_len, offset = self.get_uint8(offset)
                if data_len == 6:
                    self.network_id, offset = self.get_uint16(offset)
                    self.node_id, offset = self.get_uint16(offset)
                    self.channel, offset = self.get_uint16(offset)
        elif self.id == Message.ID_SET_BYTECODE:
            self.target_node_id, offset = self.get_uint16(0)
            self.bc_offset, offset = self.get_uint16(offset)
            val = []
            for i in range(4, len(self.payload), 2):
                instr, offset = get_uint16(offset)
                val.append(instr)
            self.bc = val
        elif (self.id == Message.ID_BREAKPOINT_CLEAR_ALL or
              self.id == Message.ID_RESET or
              self.id == Message.ID_RUN or
              self.id == Message.ID_PAUSE or
              self.id == Message.ID_STEP or
              self.id == Message.ID_STOP or
              self.id == Message.ID_GET_EXECUTION_STATE):
            self.target_node_id, offset = self.get_uint16(0)
        elif (self.id == Message.ID_BREAKPOINT_SET or
              self.id == Message.ID_BREAKPOINT_CLEAR):
            self.target_node_id, offset = self.get_uint16(0)
            self.pc, offset = self.get_uint16(offset)
        elif self.id == Message.ID_GET_VARIABLES:
            self.target_node_id, offset = self.get_uint16(0)
            self.var_offset, offset = self.get_uint16(offset)
            self.var_count, offset = self.get_uint16(offset)
        elif self.id == Message.ID_SET_VARIABLES:
            self.target_node_id, offset = self.get_uint16(0)
            self.var_offset, offset = self.get_uint16(offset)
            val = []
            for i in range(4, len(self.payload), 2):
                v, offset = get_uint16(offset)
                val.append(v)
            self.var_val = val
        elif self.id == Message.ID_LIST_NODES:
            self.version, offset = self.get_uint16(0)

    def serialize(self):
        """Serialize message to bytes.
        """
        return (self.uint16_to_bytes(len(self.payload)) +
                self.uint16_to_bytes(self.source_node) +
                self.uint16_to_bytes(self.id) +
                self.payload)

    @staticmethod
    def id_to_str(id):
        """Convert message id to its name string.
        """
        try:
            return {
                Message.ID_DESCRIPTION: "DESCRIPTION",
                Message.ID_NAMED_VARIABLE_DESCRIPTION: "ID_NAMED_VARIABLE_DESCRIPTION",
                Message.ID_LOCAL_EVENT_DESCRIPTION: "ID_LOCAL_EVENT_DESCRIPTION",
                Message.ID_NATIVE_FUNCTION_DESCRIPTION: "ID_NATIVE_FUNCTION_DESCRIPTION",
                Message.ID_VARIABLES: "ID_VARIABLES",
                Message.ID_EXECUTION_STATE_CHANGED: "ID_EXECUTION_STATE_CHANGED",
                Message.ID_NODE_PRESENT: "ID_NODE_PRESENT",
                Message.ID_GET_DESCRIPTION: "ID_GET_DESCRIPTION",
                Message.ID_SET_BYTECODE: "ID_SET_BYTECODE",
                Message.ID_RESET: "ID_RESET",
                Message.ID_RUN: "ID_RUN",
                Message.ID_PAUSE: "ID_PAUSE",
                Message.ID_STEP: "ID_STEP",
                Message.ID_STOP: "ID_STOP",
                Message.ID_GET_EXECUTION_STATE: "ID_GET_EXECUTION_STATE",
                Message.ID_BREAKPOINT_SET: "ID_BREAKPOINT_SET",
                Message.ID_BREAKPOINT_CLEAR: "ID_BREAKPOINT_CLEAR",
                Message.ID_BREAKPOINT_CLEAR_ALL: "ID_BREAKPOINT_CLEAR_ALL",
                Message.ID_GET_VARIABLES: "ID_GET_VARIABLES",
                Message.ID_SET_VARIABLES: "ID_SET_VARIABLES",
                Message.ID_GET_NODE_DESCRIPTION: "ID_GET_NODE_DESCRIPTION",
                Message.ID_LIST_NODES: "ID_LIST_NODES",
                Message.ID_GET_DEVICE_INFO: "ID_GET_DEVICE_INFO",
                Message.ID_SET_DEVICE_INFO: "ID_SET_DEVICE_INFO",
                Message.ID_GET_CHANGED_VARIABLES: "ID_GET_CHANGED_VARIABLES",
                Message.ID_GET_NODE_DESCRIPTION_FRAGMENT: "ID_GET_NODE_DESCRIPTION_FRAGMENT",
            }[id]
        except KeyError as error:
            return f"ID {id}"

    def __str__(self):
        str = f"Message id={self.id_to_str(self.id)} src={self.source_node}"
        if self.id == Message.ID_DESCRIPTION:
            str += f" name={self.node_name}"
            str += f" vers={self.protocol_version}"
            str += f" bc_size={self.bytecode_size}"
            str += f" stack_size={self.stack_size}"
            str += f" var_size={self.var_size}"
            str += f" #var={self.num_named_var}"
            str += f" #ev={self.num_local_events}"
            str += f" #nat={self.num_native_fun}"
        elif self.id == Message.ID_NAMED_VARIABLE_DESCRIPTION:
            str += f" name={self.var_name} size={self.var_size}"
        elif self.id == Message.ID_LOCAL_EVENT_DESCRIPTION:
            str += f" name={self.event_name} descr={self.description}"
        elif self.id == Message.ID_NATIVE_FUNCTION_DESCRIPTION:
            str += f" name={self.fun_name} descr={self.description} p=("
            for i in range(len(self.param_names)):
                str += f"{self.param_names[i]}[{self.param_sizes[i] if self.param_sizes[i] != 65535 else '?'}],"
            str += ")"
        elif self.id == Message.ID_VARIABLES:
            str += f" offset={self.var_offset} data=("
            for word in self.var_data:
                str += f"{word},"
            str += ")"
        elif self.id == Message.ID_NODE_PRESENT:
            str += f" version={self.version}"
        return str


class InputThread(threading.Thread):
    """Thread which reads messages asynchronously.
    """

    def __init__(self, io, loop=None, handle_msg=None):
        threading.Thread.__init__(self)
        self.running = True
        self.io = io
        self.loop = loop
        self.handle_msg = handle_msg

    def terminate(self):
        self.running = False

    def read_uint16(self):
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

    def read_message(self):
        """Read a complete message.
        """
        payload_len = self.read_uint16()
        source_node = self.read_uint16()
        id = self.read_uint16()
        payload = self.io.read(payload_len)
        msg = Message(id, source_node, payload)
        return msg

    def run(self):
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

    def __init__(self, node_id=None, version=None):
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

    def __str__(self):
        return f"RemoteNode node_id={self.node_id} uuid={self.device_uuid}"

    def __repr__(self):
        return str(self)

    def add_var(self, name, size):
        """Add the definition of a variable.
        """
        self.named_variables.append(name)
        self.var_offset[name] = self.var_total_size
        self.var_size[name] = size
        self.var_total_size += size

    def reset_var_data(self):
        """Reset the variable data to 0.
        """
        self.var_data = [0 for i in range(self.var_total_size)]

    def get_var(self, name, index=0):
        """Get the value of a scalar variable or an item in an array variable.
        """
        return self.var_data[self.var_offset[name] + index]

    def get_var_array(self, name):
        """Get the value of an array variable.
        """
        if name not in self.var_offset:
            raise KeyError(name)
        offset = self.var_offset[name]
        return self.var_data[offset : offset + self.var_size[name]]

    def set_var(self, name, val, index=0):
        """Set the value of a scalar variable or an item in an array variable.
        """
        self.var_data[self.var_offset[name] + index] = val

    def set_var_array(self, name, val):
        """Set the value of an array variable.
        """
        offset = self.var_offset[name]
        self.var_data[offset : offset + len(val)] = val

    def set_var_data(self, offset, data):
        """Set values in the variable data array.
        """
        self.var_data[offset : offset + len(data)] = data
        self.var_received = offset + len(data) >= self.expected_var_end


class Connection:
    """Connection to one or multiple devices.
    """

    def __init__(self,
                 io,
                 host_node_id=1, refreshing_rate=None, discover_rate=None,
                 loop=None):
        self.loop = loop or asyncio.new_event_loop()
        self.terminating = False
        self.io = io
        self.timeout = 3
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
        self.refreshing_triggers = []   # threading.Event
        if refreshing_rate is not None:
            self.set_refreshing_rate(refreshing_rate)

        # callback for (dis)connection
        # async fun(node_id, connect)
        self.on_connection_changed = None

        # callback for notification that variables have been received
        # async fun(node_id)
        self.on_variables_received = None

        # discover coroutine
        if discover_rate is not None:
            async def discover():
                while not self.terminating:
                    self.handshake()
                    await asyncio.sleep(discover_rate)
            self.loop.create_task(discover())

    def close(self):
        """Close connection.
        """
        if not self.io.closed:
            self.io.close()

    def shutdown(self):
        """Shutdown everything.
        """
        self.terminating = True
        self.input_thread.terminate()

    def run_forever(self):
        """Run asyncio loop forever.
        """
        self.loop.run_forever()

    def __del__(self):
        self.shutdown()
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    @staticmethod
    def serial_default_port():
        """Get the name of the default Thymio serial port for the current platform.
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
            ][0]
        elif sys.platform == "win32":
            devices = ["COM8"]
        else:
            raise Exception("Unsupported platform")
        if len(devices) < 1:
            raise Exception("No serial device for Thymio found")
        return devices[0]

    @staticmethod
    def serial(port=None, **kwargs):
        """Create Thymio object with a serial connection.
        """
        import serial  # pip3 install pyserial
        if port is None:
            port = Connection.serial_default_port()
        th = Connection(serial.Serial(port, timeout=1), **kwargs)
        return th

    @staticmethod
    def tcp(host="127.0.0.1", port=3000, **kwargs):
        """Create Thymio object with a TCP connection.
        """
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        th = Connection(s, **kwargs)
        return th

    @staticmethod
    def null(host_node_id=1, **kwargs):
        """Create Thymio object without connection.
        """
        import io
        class NullIO(io.RawIOBase):
            def read(self, n):
                return None
            def write(self, b):
                pass
        return Thymio(NullIO(), host_node_id)

    def handshake(self):
        self.auto_handshake = True
        self.list_nodes()

    def wait_for_handshake(self, n=1, timeout=5):
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

    def one_remote_node_id(self):
        """Get the node id of one of the connected nodes.
        """
        return next(iter(self.remote_node_set))

    def set_refreshing_rate(self, rate):
        """Change the auto-refresh rate to update variables.
        """
        self.refreshing_timeout = rate
        if rate is not None:
            # refresh now
            for event in self.refreshing_triggers:
                event.set()

    async def handle_message(self, msg):
        """Handle an input message.
        """
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
                    if (remote_node.rf_network_id != msg.network_id or
                        remote_node.rf_node_id != msg.node_id or
                        remote_node.rf_channel != msg.channel):
                        remote_node.rf_network_id = msg.network_id
                        remote_node.rf_node_id = msg.node_id
                        remote_node.rf_channel = msg.channel
                        change = True
            if change and self.on_connection_changed:
                await self.on_connection_changed(source_node, True)
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
                    async def do_refresh():
                        while not self.terminating:
                            if self.refreshing_timeout is None:
                                await asyncio.sleep(0.1)
                            else:
                                await asyncio.sleep(self.refreshing_timeout)
                                self.get_variables(source_node)
                            # assume disconnection upon timeout
                            current_time = time.time()
                            terminating_nodes = set()
                            for node_id in self.remote_node_set:
                                with self.input_lock:
                                    remote_node = self.remote_nodes[node_id]
                                    if current_time - remote_node.last_msg_time > self.timeout:
                                        terminating_nodes.add(node_id)
                            for node_id in terminating_nodes:
                                self.remote_node_set.remove(node_id)
                                if self.on_connection_changed:
                                    await self.on_connection_changed(node_id, False)
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
            pass  # ignore
        else:
            print(msg)
        self.remote_nodes[source_node].last_msg_time = time.time()

    def uuid_to_node_id(self, uuid):
        """Get node id from device uuid.
        """
        for node in self.remote_nodes.values():
            if node.device_uuid == uuid:
                return node.node_id

    def send(self, msg):
        """Send a message.
        """
        with self.output_lock:
            self.io.write(msg.serialize())

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

    def get_variables(self, target_node_id, chunk_offset=0, chunk_length=None):
        """Send a GET_VARIABLES message.
        """
        if target_node_id is not None:
            if chunk_length is None:
                chunk_length = (self.get_target_node_var_total_size(target_node_id) -
                    chunk_offset)
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
        """Get an array with the description of all variables, with fields "name", "offset" and "size".
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
            ] + bytecode[i : i + size_chunk])
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

if __name__ == "__main__":

    async def on_connection_changed(node_id, connected):
        print("Connection" if connected else "Disconnection", node_id)
        if connected:
            # display node information
            remote_node = th.remote_nodes[node_id]
            if remote_node.name:
                print(f"Node name: {remote_node.name}")
            if remote_node.device_name:
                print(f"Device name: {remote_node.device_name}")
            if remote_node.device_uuid:
                print(f"Device uuid: {remote_node.device_uuid}")

            # send bytecode for "call leds.top(32, 32, 0)" and run it
            th.set_bytecode(node_id, [
                3,          # vector table size
                0xffff, 3,  # address of event 0xffff (init)
                0x1000,     # push.s 0
                0x426b,     # store 0x26b
                0x126b,     # push.s 0x26b
                0x1020,     # push.s 32
                0x426a,     # store 0x26a
                0x126a,     # push.s 0x26a
                0x1020,     # push.s 32
                0x4269,     # store 0x269
                0x1269,     # push.s 0x269
                0xc028,     # callnat 0x28
                0x0000      # stop
            ])
            th.run(node_id)

    async def on_variables_received(node_id):
        try:
            print(f"Node {node_id}: prox.horizontal = {th[node_id]['prox.horizontal']}")
        except KeyError:
            print("on_variables_received", th.remote_nodes[node_id])

    with Connection.serial(discover_rate=2, refreshing_rate=0.5) as th:
        th.on_connection_changed = on_connection_changed
        th.on_variables_received = on_variables_received
        try:
            th.run_forever()
        except KeyboardInterrupt:
            th.shutdown()
            th.run_forever()
            th.close()
