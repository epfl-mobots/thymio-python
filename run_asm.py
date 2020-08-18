# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

# Send assembly program to Thymio

import thymio
import thymio.assembler
import serial
import sys
import os

if __name__ == "__main__":

    asm = None
    use_tcp = False
    debug = False
    for arg in sys.argv[1:]:
        if arg == "--tcp":
            use_tcp = True
        elif arg == "--debug":
            debug = True
        elif arg[0:2] == "--" or asm:
            print(f"Usage: python3 {sys.argv[0]} [--tcp] [program.asm]")
            exit(1)
        else:
            with open(arg, 'r') as file:
                asm = file.read()
    if asm is None:
        asm = sys.stdin.read()

    code_sent = False

    async def on_connection_changed(node_id, connected):
        if connected:
            # assemble program
            remote_node = th.remote_nodes[node_id]
            a = thymio.assembler.Assembler(remote_node, asm)
            bc = a.assemble()

            # send bytecode and run it
            th.set_bytecode(node_id, bc)
            th.run(node_id)
            global code_sent
            code_sent = True

    async def on_execution_state_changed(node_id, pc, flags):
        if code_sent:
            os._exit(0) # forced exit despite coroutines

    def run_until_executed(th):
        th.on_connection_changed = on_connection_changed
        th.on_execution_state_changed = on_execution_state_changed
        try:
            th.run_forever()
        except KeyboardInterrupt:
            th.shutdown()
            th.run_forever()
            th.close()


    try:
        if not use_tcp:
            # try to open serial connection
            with thymio.Connection.serial(discover_rate=2, refreshing_rate=0.5, debug=debug) as th:
                run_until_executed(th)
    except serial.serialutil.SerialException:
        use_tcp = True

    if use_tcp:
        # try TCP on default local port
        with thymio.Connection.tcp(discover_rate=2, refreshing_rate=0.5, debug=debug) as th:
            run_until_executed(th)
