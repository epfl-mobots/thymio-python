# Test of the communication with Thymio via serial port
# Author: Yves Piguet, EPFL

from thymio import Thymio
import sys
import os

if __name__ == "__main__":

    # check arguments
    use_tcp = False
    serial_port = None
    host = None
    tcp_port = None
    if len(sys.argv) == 3:
        # tcp: argv[1] = host, argv[2] = port
        use_tcp = True
        host = sys.argv[1]
        tcp_port = int(sys.argv[2])
    elif len(sys.argv) == 2:
        if sys.argv[1] == "--help":
            print("Usage: {sys.argv[0]} [serial_port | host port]")
            sys.exit(0)
        # serial port: argv[1] = serial port
        serial_port = sys.argv[1]

    # connect
    th = Thymio(use_tcp=use_tcp,
                serial_port=serial_port,
                host=host, tcp_port=tcp_port)
    # constructor options: on_connect, on_disconnect, refreshing_rate, discover_rate, loop
    th.connect()

    # wait 2-3 sec until robots are known
    id = th.first_node()
    print(f"id: {id}")
    print(f"variables: {th.variables(id)}")
    print(f"events: {th.variables(id)}")
    print(f"native functions: {th.native_functions(id)[0]}")

    # get a variable
    th[id]["prox.horizontal"]

    # set a variable (scalar or array)
    th[id]["leds.top"] = [0, 0, 32]

    # set a function called after new variable values have been fetched
    prox_prev = 0
    def obs(node_id):
        global prox_prev
        prox = (th[node_id]["prox.horizontal"][5] - th[node_id]["prox.horizontal"][2]) // 10
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

    th.set_variable_observer(id, obs)
