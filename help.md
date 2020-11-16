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
