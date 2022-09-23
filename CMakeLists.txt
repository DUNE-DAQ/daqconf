cmake_minimum_required(VERSION 3.12)
project(daqconf VERSION 5.5.0)

find_package(daq-cmake REQUIRED )

daq_setup_environment()

daq_codegen( *.jsonnet TEMPLATES Structs.hpp.j2 )

daq_install()
