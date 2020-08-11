# thymio-python

Python package to connect to a [Thymio II robot](https://thymio.org)
with its native binary protocol via a serial port (virtual port over
a wired USB or wireless USB dongle) or a TCP port (asebaswitch or Thymio
simulator).

## Building the package

```
python3 setup.py bdist_wheel
```

The result is a .whl file in directory dist, e.g.
dist/Thymio-0.1.0-py3-none-any.whl

## Installing the package

```
python3 -m pip install dist/Thymio-0.1.0-py3-none-any.whl
```
