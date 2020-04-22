# Test of the communication with Thymio via serial port
# Author: Yves Piguet, EPFL

import thymio
import serial
import sys

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

    def run_demo(th):
        th.on_connection_changed = on_connection_changed
        th.on_variables_received = on_variables_received
        try:
            th.run_forever()
        except KeyboardInterrupt:
            th.shutdown()
            th.run_forever()
            th.close()


    use_tcp = len(sys.argv) > 1 and sys.argv[1] == "--tcp"

    try:
        if not use_tcp:
            # try to open serial connection
            with thymio.Connection.serial(discover_rate=2, refreshing_rate=0.5) as th:
                run_demo(th)
    except serial.serialutil.SerialException:
        use_tcp = True

    if use_tcp:
        # try TCP on default local port
        with thymio.Connection.tcp(discover_rate=2, refreshing_rate=0.5) as th:
            run_demo(th)
