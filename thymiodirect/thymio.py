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
from typing import List

from thymiodirect.connection import Connection
from thymiodirect.assembler import Assembler


class Thymio:
    """
    Thymio is a helper object for communicating with one or several Thymios
    connected to a single port.
    """

    class _ThymioProxy:
        """
        _ThymioProxy is a proxy to a Thymio object to call user-defined
        functions from asyncio coroutines.
        """

        def __init__(self, thymio: "thymio.Thymio"):
            """
            Construct a new __ThymioProxy object.

            :param thymio: Thymio object
            """

            self.thymio = thymio
            self.connection = None
            self.loop = asyncio.get_event_loop()
            self.nodes = set()

        def run(self):
            """
            Run the asyncio loop forever, taking care of executing callbacks
            registered for the Thymio connection.
            """

            async def on_connection_changed(node_id, connected: bool):
                """
                Do what's required when the Thymio connection changes.
                """
                if connected:
                    self.nodes.add(node_id)
                    if self.thymio.on_connect_cb:
                        self.thymio.on_connect_cb(node_id)
                else:
                    self.nodes.remove(node_id)
                    if self.thymio.on_disconnect_cb:
                        self.thymio.on_disconnect_cb(node_id)

            async def on_variables_received(node_id: int):
                """
                Do what's required when new variables have been received.
                """
                if node_id in self.thymio.variable_observers:
                    variable_observer = self.thymio.variable_observers[node_id]
                    variable_observer(node_id)

            async def on_user_event(node_id: int, event_id: int, event_args: List[int]):
                """
                Do what's required when an event has been received from the Thymio.
                """
                if node_id in self.thymio.user_event_listeners:
                    user_event_listener = self.thymio.user_event_listeners[node_id]
                    user_event_listener(node_id, event_id, event_args)

            def on_comm_error(error: Exception) -> None:
                """
                Forward error raised when communicating with the Thymio.
                """
                if self.thymio.on_comm_error is not None:
                    self.thymio.on_comm_error(error)

            try:
                if self.thymio.use_tcp:
                    self.connection = Connection.tcp(host=self.thymio.host,
                                                     port=self.thymio.tcp_port,
                                                     discover_rate=self.thymio.discover_rate,
                                                     refreshing_rate=self.thymio.refreshing_rate,
                                                     refreshing_coverage=self.thymio.refreshing_coverage,
                                                     loop=self.loop)
                else:
                    self.connection = Connection.serial(port=self.thymio.serial_port,
                                                        discover_rate=self.thymio.discover_rate,
                                                        refreshing_rate=self.thymio.refreshing_rate,
                                                        refreshing_coverage=self.thymio.refreshing_coverage,
                                                        loop=self.loop)
            except Exception as error:
                on_comm_error(error)

            self.connection.on_connection_changed = on_connection_changed
            self.connection.on_variables_received = on_variables_received
            self.connection.on_user_event = on_user_event
            self.connection.on_comm_error = on_comm_error

            self.loop.run_forever()

    def __init__(self,
                 use_tcp=False,
                 serial_port=None,
                 host=None,
                 tcp_port=None,
                 on_connect=None,
                 on_disconnect=None,
                 on_comm_error=None,
                 refreshing_rate=0.1,
                 refreshing_coverage=None,
                 discover_rate=2,
                 loop=None):
        self.use_tcp = use_tcp
        self.serial_port = serial_port
        self.host = host
        self.tcp_port = tcp_port
        self.on_connect_cb = on_connect
        self.on_disconnect_cb = on_disconnect
        self.on_comm_error = on_comm_error
        self.refreshing_rate = refreshing_rate
        self.refreshing_coverage = refreshing_coverage
        self.discover_rate = discover_rate
        self.loop = loop or asyncio.get_event_loop()
        self.thymio_proxy = None
        self.variable_observers = {}
        self.user_event_listeners = {}

    def connect(self):
        """Connect to Thymio or dongle.
        """
        def thymio_thread():
            asyncio.set_event_loop(asyncio.new_event_loop())
            self.thymio_proxy = self._ThymioProxy(self)
            self.thymio_proxy.run()
        self.thread = threading.Thread(target=thymio_thread)
        self.thread.start()
        while self.thymio_proxy is None or len(self.thymio_proxy.nodes) == 0:
            time.sleep(0.1)

    def nodes(self):
        """Get set of ids of node currentlty connected.
        """
        return self.thymio_proxy.nodes if self.thymio_proxy else set()

    def first_node(self):
        """Get id of first node connected.
        """
        return next(iter(self.nodes()))

    def variables(self, node_id):
        """Get list of variable names.
        """
        node = self.thymio_proxy.connection.remote_nodes[node_id]
        return node.named_variables

    def variable_size(self, node_id, var_name):
        """Get the size of a variable.
        """
        node = self.thymio_proxy.connection.remote_nodes[node_id]
        return node.var_size[var_name]

    def variable_offset(self, node_id, var_name):
        """Get the offset (address) of a variable.
        """
        node = self.thymio_proxy.connection.remote_nodes[node_id]
        return node.var_offset[var_name]

    def __getitem__(self, key):
        class Node:
            def __init__(self_node, node_id):
                self_node.node_id = node_id
            def __getitem__(self_node, name):
                try:
                    val = self.thymio_proxy.connection.get_var_array(self_node.node_id, name)
                    return val if len(val) != 1 else val[0]
                except KeyError:
                    raise KeyError(name)
            def __setitem__(self_node, name, val):
                try:
                    if isinstance(val, list):
                        self.thymio_proxy.connection.set_var_array(self_node.node_id, name, val)
                    else:
                        self.thymio_proxy.connection.set_var(self_node.node_id, name, val)
                except KeyError:
                    raise KeyError(name)

        return Node(key)

    def set_variable_observer(self, node_id, observer):
        self.variable_observers[node_id] = observer

    def set_user_event_listener(self, node_id, listener):
        self.user_event_listeners[node_id] = listener

    def events(self, node_id):
        """Get list of event names.
        """
        node = self.thymio_proxy.connection.remote_nodes[node_id]
        return node.local_events

    def native_functions(self, node_id):
        """Get list of native function names and list of corresponding arg sizes.
        """
        node = self.thymio_proxy.connection.remote_nodes[node_id]
        return (
            node.native_functions,
            [node.native_functions_arg_sizes[f] for f in node.native_functions]
        )

    def run_asm(self, node_id: int, asm: str) -> None:
        """Assemble assembly code to bytecode, load it and run it.
        """
        # assemble program
        remote_node = self.thymio_proxy.connection.remote_nodes[node_id]
        a = Assembler(remote_node, asm)
        bc = a.assemble()
        # run it
        self.thymio_proxy.connection.set_bytecode(node_id, bc)
        self.thymio_proxy.connection.run(node_id)
