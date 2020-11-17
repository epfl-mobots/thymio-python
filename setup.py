# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import setup

with open("help.md", "r") as fh:
    long_description = fh.read()

setup(
    name='thymiodirect',
    version='0.1.2',
    author='Yves Piguet',
    packages=['thymiodirect'],
    description='Communication with Thymio II robot via serial port or TCP',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/epfl-mobots/thymio-python',
    install_requires=[
        'pyserial'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Education",
        "Framework :: AsyncIO"
    ],
    python_requires='>=3.6',
)
