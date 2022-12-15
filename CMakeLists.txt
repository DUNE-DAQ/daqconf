cmake_minimum_required(VERSION 3.12)
project(daqconf VERSION 5.5.4)

find_package(daq-cmake REQUIRED )

daq_setup_environment()

daq_codegen( *.jsonnet TEMPLATES Structs.hpp.j2 Nljs.hpp.j2)

daq_codegen( *.jsonnet OUTDIR lib64/python GRAFT "/lang:opython.jsonnet" TEMPLATES PyStructs.py.j2 PySerdes.py.j2)

daq_install()
