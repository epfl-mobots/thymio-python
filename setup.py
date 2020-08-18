# This file is part of thymiodirect.
# Copyright 2020 ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE,
# Miniature Mobile Robots group, Switzerland
# Author: Yves Piguet
#
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import setup

setup(
    name='ThymioDirect',
	version='0.1.0',
	author='Yves Piguet',
	packages=['thymiodirect'],
	description='Communication with Thymio II robot via serial port or TCP',
	install_requires=[
		'pyserial'
	],
)
