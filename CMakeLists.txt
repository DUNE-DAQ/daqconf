cmake_minimum_required(VERSION 3.12)
project(daqconf VERSION 7.3.3)

find_package(daq-cmake REQUIRED )

daq_setup_environment()

daq_install()
