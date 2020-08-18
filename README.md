# thymiodirect

Python package to connect to a [Thymio II robot](https://thymio.org)
with its native binary protocol via a serial port (virtual port over
a wired USB or wireless USB dongle) or a TCP port (asebaswitch or Thymio
simulator).

## Building the package

```
python3 setup.py bdist_wheel
```

The result is a .whl file in directory dist, e.g.
dist/ThymioDirect-0.1.0-py3-none-any.whl

## Installing the package

```
python3 -m pip install dist/ThymioDirect-0.1.0-py3-none-any.whl
```

## License

Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
Miniature Mobile Robots group, Switzerland

The module is provided under the BSD-3-Clause license.
Please see file LICENSE for details.
