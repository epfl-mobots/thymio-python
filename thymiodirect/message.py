# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

# Messages defined for Aseba communication protocol

import uuid

class Message:
    """Aseba message data.
    """

    # v5
    ID_FIRST_ASEBA_ID = 0x8000
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
    ID_SET_VARIABLES = 0xa00c
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
        str = self.payload[offset + 1:offset + 1 + len]
        return str.decode('utf-8'), offset + 1 + len

    @staticmethod
    def uint16_to_bytes(word):
        """Convert an unsigned 16-bit integer to bytes.
        """
        return bytes([word & 0xff, (word & 0xff00) // 256])

    @staticmethod
    def uint16array_to_bytes(a):
        """Convert an array of unsigned 16-bit integer to bytes.
        """
        bytes = b""
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
        elif self.id == Message.ID_EXECUTION_STATE_CHANGED:
            self.pc, offset = self.get_uint16(0)
            self.flags, offset = self.get_uint16(offset)
            self.event_active = (self.flags & 1) != 0
            self.step_by_step = (self.flags & 2) != 0
            self.event_running = (self.flags & 4) != 0
        elif self.id == Message.ID_NODE_PRESENT:
            self.version, offset = self.get_uint16(0)
        elif self.id == Message.ID_DEVICE_INFO:
            self.device_info, offset = self.get_uint8(0)
            if self.device_info == Message.DEVICE_INFO_NAME:
                self.device_name, offset = self.get_string(offset)
            elif self.device_info == Message.DEVICE_INFO_UUID:
                data_len, offset = self.get_uint8(offset)
                data = self.payload[offset:offset + data_len]
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
                instr, offset = self.get_uint16(offset)
                val.append(instr)
            self.bc = val
        elif (self.id == Message.ID_BREAKPOINT_CLEAR_ALL
              or self.id == Message.ID_RESET
              or self.id == Message.ID_RUN
              or self.id == Message.ID_PAUSE
              or self.id == Message.ID_STEP
              or self.id == Message.ID_STOP
              or self.id == Message.ID_GET_EXECUTION_STATE):
            self.target_node_id, offset = self.get_uint16(0)
        elif (self.id == Message.ID_BREAKPOINT_SET
              or self.id == Message.ID_BREAKPOINT_CLEAR):
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
                v, offset = self.get_uint16(offset)
                val.append(v)
            self.var_val = val
        elif self.id == Message.ID_LIST_NODES:
            self.version, offset = self.get_uint16(0)
        elif self.id == Message.ID_GET_NODE_DESCRIPTION_FRAGMENT:
            self.version, offset = self.get_uint16(0)
            self.fragment, offset = self.get_uint16(offset)
        elif self.id < Message.ID_FIRST_ASEBA_ID:
            val = []
            offset = 0
            for i in range(0, len(self.payload), 2):
                v, offset = self.get_uint16(offset)
                val.append(v)
            self.user_event_arg = val

    def serialize(self):
        """Serialize message to bytes.
        """
        return (self.uint16_to_bytes(len(self.payload))
                + self.uint16_to_bytes(self.source_node)
                + self.uint16_to_bytes(self.id)
                + self.payload)

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
            str += f" max_var_size={self.max_var_size}"
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
        elif self.id == Message.ID_EXECUTION_STATE_CHANGED:
            str += f" pc={self.pc} event_active={self.event_active} step_by_step={self.step_by_step} event_running={self.event_running}"

        elif self.id == Message.ID_NODE_PRESENT:
            str += f" version={self.version}"
        return str
