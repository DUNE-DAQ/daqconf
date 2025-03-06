cmake_minimum_required(VERSION 3.12)
project(daqconf VERSION 8.1.3)

find_package(daq-cmake REQUIRED )

daq_setup_environment()

find_package(logging REQUIRED)
find_package(appmodel REQUIRED)
find_package(conffwk REQUIRED)
find_package(confmodel REQUIRED)
find_package(Boost COMPONENTS unit_test_framework program_options REQUIRED)

daq_add_application(create_config_plot create_config_plot.cxx GraphBuilder.cpp LINK_LIBRARIES Boost::program_options appmodel::appmodel conffwk::conffwk confmodel::confmodel)

daq_add_unit_test(Graph_test)

daq_install()
