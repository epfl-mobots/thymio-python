# thymiodirect

Python package to connect to a [Thymio II robot](https://thymio.org)
with its native binary protocol via a serial port (virtual port over
a wired USB or wireless USB dongle) or a TCP port (asebaswitch or Thymio
simulator).

## Building the package

```
python3 setup.py sdist bdist_wheel
```

The result is a .tar.gz file (source archive, the result of sdist) and a .whl file (built distribution, the result of bdist_wheel) in directory dist.

## Installing the package

```
python3 -m pip install dist/ThymioDirect_EPFL_Mobots-0.1.0-py3-none-any.whl
```

## License

Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
Miniature Mobile Robots group, Switzerland

The module is provided under the BSD-3-Clause license.
Please see file LICENSE for details.
