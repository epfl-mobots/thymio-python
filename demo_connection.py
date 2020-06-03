# Test of the communication with Thymio via serial port
# Author: Yves Piguet, EPFL

import thymio
import thymio.assembler
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

            # assemble program corresponding to "call leds.top(32, 32, 0) onevent button.left emit myid counter counter++"
            src = """
                dc end_toc                  ; total size of event handler table
                dc _ev.init, init           ; id and address of init event
                dc _ev.button.left, btnleft ; id and address of button.left event
            end_toc:

            init:                           ; code executed on init event
                push.s 0                    ; initialize counter
                store counter
                push.s 0                    ; push address of 3rd arg, stored somewhere in free memory
                store _userdata
                push.s _userdata
                push.s 32                   ; push address of 2nd arg
                store _userdata+1
                push.s _userdata+1
                push.s 32                   ; push address of 1st arg
                store _userdata+2
                push.s _userdata+2
                callnat _nf.leds.top        ; call native function to set top rgb led
                stop                        ; stop program

            btnleft:
                emit myid, counter, 1       ; emit myid with current counter value
                load counter                ; increment counter
                push.s 1
                add
                store counter
                stop
            myid:
                equ 0
            counter:
                equ _userdata+3
            """
            a = thymio.assembler.Assembler(remote_node, src)
            bc = a.assemble()

            # send bytecode and run it
            th.set_bytecode(node_id, bc)
            th.run(node_id)

    async def on_variables_received(node_id):
        try:
            print(f"Node {node_id}: prox.horizontal = {th[node_id]['prox.horizontal']}")
        except KeyError:
            print("on_variables_received", th.remote_nodes[node_id])

    async def on_user_event(node_id, event_id, event_args):
        print(f"Node {node_id}: rcv event {event_id}, value={event_args}")

    def run_demo(th):
        th.on_connection_changed = on_connection_changed
        th.on_variables_received = on_variables_received
        th.on_user_event = on_user_event
        try:
            th.run_forever()
        except KeyboardInterrupt:
            th.shutdown()
            th.run_forever()
            th.close()


    use_tcp = False
    debug = False
    for arg in sys.argv[1:]:
        if arg == "--tcp":
            use_tcp = True
        elif arg == "--debug":
            debug = True
        else:
            sys.stderr.write(f"Unknown option {arg}\n")
            exit(1)

    try:
        if not use_tcp:
            # try to open serial connection
            with thymio.Connection.serial(discover_rate=2, refreshing_rate=0.5, debug=debug) as th:
                run_demo(th)
    except serial.serialutil.SerialException:
        use_tcp = True

    if use_tcp:
        # try TCP on default local port
        with thymio.Connection.tcp(discover_rate=2, refreshing_rate=0.5, debug=debug) as th:
            run_demo(th)
