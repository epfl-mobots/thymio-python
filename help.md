# thymiodirect

Python package to connect to a [Thymio II robot](https://thymio.org) with its native binary protocol via a serial port (virtual port over a wired USB or wireless USB dongle) or a TCP port (asebaswitch or Thymio simulator).

## Example

The steps below are borrowed from the help you obtain by typing
```
import thymiodirect
help(thymiodirect)
```

Import the required classes:
```
from thymiodirect import Connection
from thymiodirect import Thymio
```

Set the serial port the Thymio is connected to (depending on your configuration, the default port is not what you want):
```
port = Connection.serial_default_port()
```

Create a `Thymio` connection object with a callback to be notified when the robot is ready and start the connection (or just wait a few seconds):
```
th = Thymio(serial_port=port,
            on_connect=lambda node_id:print(f"{node_id} is connected"))
th.connect()
```

Get id of the first (or only) Thymio:
```
id = th.first_node()
```

Get a variable:
```
th[id]["prox.horizontal"]
```

Set a variable (scalar or array):
```
th[id]["leds.top"] = [0, 0, 32]
```

Define a function called after new variable values have been fetched.
The front and rear proximity sensors are used to make the robot move forward or backward. Decision to move or stop is based on the difference of these sensor readings.
```
prox_prev = 0
def obs(node_id):
    global prox_prev
    prox = (th[node_id]["prox.horizontal"][5]
            - th[node_id]["prox.horizontal"][2]) // 10
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
```

Install this function:
```
th.set_variable_observer(id, obs)
```

Make the robot move forward by putting your hand behind it, or backward by putting your hand in front of it.

Remove this function:
```
th.set_variable_observer(id, None)
```

By default, all the Thymio variables are fetched 10 times per second. This can be changed with options passed to the `Thymio` constructor. Here is how you would fetch 5 times per second (every 0.2 second) a chunk of variable data which covers `prox.horizontal` and `prox.ground`:
```
th = Thymio(serial_port=port,
            on_connect=lambda node_id:print(f"{node_id} is connected"),
            refreshing_rate=0.2,
            refreshing_coverage={"prox.horizontal", "prox.ground"})
```

## Implementation overview

Communication is implemented mainly in `connection.py` and the higher-level `thymio.py`. They both rely on asyncio event loops.

### connection.py

One `Connection` object lets you communicate via a serial or tcp connection to one or multiple robots (nodes). The `Connection` object opens the connection, has a single event loop which it can receive as constructor parameter or create and delete itself, sends messages, and cache the state of nodes in a dict of `RemoteNode` objects (key is the node id). Message reception is done asynchronously in a thread created by an `InputThread` object (one per `Connection` object). The `InputThread` object has a reference to its `Connection`'s event loop and handles the messages it receives via a callback in the context of the `Connection` object, thanks to `asyncio.ensure_future`.

The capability to connect to multiple robots depends on the communication channel. With a plain USB cable, you can connect only to a single Thymio II. With a USB wireless dongle, you can pair the dongle to multiple robots. Launch Thymio Suite and connect the dongle, select the tool _Pair a Wireless Thymio to a Wireless dongle_, click the button _Advanced Mode_, and for each robot, connect it with a USB cable and click the button _Pair!_ without changing the channel or network identifier. Please refer to the Thymio Suite documentation for more details. With a TCP connection, _asebaswitch_ can be launched with multiple robots and the `Connection` object establishes a single TCP stream to it where the messages for all the robots transit.

### thymio.py

A `Thymio` object provides a nicer interface to robots which hides async methods and event loops. It creates a `Connection` object and sets up all the hooks required to fetch information, get and set variables, and assemble and execute programs provided as Thymio bytecode assembler. To communicate with it, a `_ThymioProx` object is created, which has its own event loop and async functions in a separate thread. A callback can be registered to be executed once variables have been updated to allow for a feedback loop without superfluous delay.
