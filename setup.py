from setuptools import setup

setup(
    name='Thymio',
	version='0.1.0',
	author='Yves Piguet',
	packages=['thymio'],
	description='Communication with Thymio II robot via serial port or TCP',
	install_requires=[
		'pyserial'
	],
)

