The intention of this page is to provide a few simple configurations that new or casual users can use in order to test the operation of a small demo system that uses emulators instead of real electronics.

After you have successfully followed the steps described in [Instructions for casual or first-time users](InstructionsForCasualUsers.md), we will focus now on a few variations to the default configuration used in those instructions.

First, a reminder to set up your working software environment and downloaded the fake input data file
1. `cd <work_dir>`
2. `source ./dbt-env.sh`
4. `dbt-workarea-env`
5. `curl -o frames.bin -O https://cernbox.cern.ch/index.php/s/0XzhExSIMQJUsp0/download`

Next we generate some sample system configurations and use _[nanorc](https://dune-daq-sw.readthedocs.io/en/latest/packages/nanorc/)_ to run a demo system with them.

The tools to generate these configurations consist of a single Python script that generates DAQ system configurations with different characteristics based on command-line parameters that are given to the script. This script is daqconf/scripts/daqconf_multiru_gen.py.
The config_gen files under `python/daqconf/` directory were developed to work with _nanorc_ package, which itself can be seen as a basic Finite State Machine that sends commands and drives the DAQ system.

The created configurations will be called `daq_fakeNN` and there will be a `daq_fakeNN` directory created containing the produced configuration to be used with  _nanorc_.
The configurations can be run interactively with `nanorc daq_fakeNN` from the `<work_dir>`.

1) In order to get the full set of configuration options and their `help` , run :
`daqconf_multiru_gen -h`

2) The data `Input` and `Output` system configuration options allow the user to change the input data file location and the output data directory path as needed. To specify an input `frames.bin` file from the current directory, a user would use `-d $PWD/frames.bin`. This file contains data frames that are replayed by fake cards in the current system, and as mentioned above, this file can be downloaded with "`curl -o frames.bin -O https://cernbox.cern.ch/index.php/s/7qNnuxD8igDOVJT/download`". The output data path option `-o` can be used to specify the directory where output data files are written.  To write the output data files to the current directory, one would use `-o .`
The `Input` and `Output` data system options can be used in the following way

`daqconf_multiru_gen -d $PWD/frames.bin -o .  daq_fake01`

3) The default trigger rate generated is 1 Hz per readout unit (RU). This can be changed with the option `--trigger-rate-hz FLOAT` (default 1.0 Hz), or alternatively `-t FLOAT`. For example to increase the trigger rate generated to 2.0 Hz, the user can run with either of these two options:

`daqconf_multiru_gen -d $PWD/frames.bin -o . --trigger-rate-hz 2.0  daq_fake02`

`daqconf_multiru_gen -d $PWD/frames.bin -o . -t 2.0 daq_fake03`


4) Use option `-s INTEGER` to slow down the generated data rate by a factor of INTEGER, this is achieved by slowing down the simulated clock speed for generating data. This option is particularly useful when the user is running the system on a slow computer that can't create data fast enough to match what the real electronics can do. For example to slowdown the data production rate by a factor of 10, run the following commmand:

`daqconf_multiru_gen -d $PWD/frames.bin -o . -s 10  daq_fake04`


5) Use option `-n INTEGER` to specify the number of data producers (links) per RU (<10) or total. Since the maximum number of data producers per readout unit is 10, values for this parameter that are larger than 10 are interpreted to indicate the _total_ number of data producers instead of the number per RU. When the total number of data producers are specified, they are spread equally among the RUs, as much as possible.
Here is an example command specifying 4 data producers (per RU) :

`daqconf_multiru_gen -d $PWD/frames.bin -o . -n 4 daq_fake05`


6) Use options `--host-df TEXT` , `--host-ru TEXT` , `--host-trigger TEXT` , `--host-hsi TEXT`  to specify different hosts for the different applications (processes):
`host Data-Flow (host-df)` this is a repeatable option adding an additional DF process each time
`host Readout Unit (host-ru)` this is a repeatable option adding an additional RU process each time, each `host-ru` option needs to be accompanied by a `--region-id <N>` option, and each of the <N> values must be unique
`host Trigger app  (host-trigger)`
`host HSI app (--host-hsi)`

for example using the following fake IP addresses for the different hosts :  127.0.0.1 , 127.0.0.2 , 127.0.0.3 , 127.0.0.4

`daqconf_multiru_gen -d $PWD/frames.bin -o . --host-df 127.0.0.1 --host-ru 127.0.0.2 --host-ru 127.0.0.2 --host-trigger 127.0.0.3 --host-hsi 127.0.0.4   --region-id 0 --region-id 1 daq_fake06`

the default for any unspecified host options will be `localhost`

7) Running _nanorc_ can be done in interactively or in batch mode, for the later you can specify a sequence of commands to drive MiniDAQ app, for example run :

 `nanorc daq_fake03 boot <partition_name> init conf start 103 wait 60 stop scrap terminate`

Where the `start <run_number>` command specifies the run_number value to be used.
Any meaningful combination of commands is allowed.  Note that the `start` command includes an automatically-generated `resume` command to start the flow of triggers, and the `stop` command includes an automatically-generated `pause` command to stop the flow of triggers.


8) examine the contents of the HDf5 file with commands like the following:
   * `h5dump-shared -H -A swtest_run000103_0000_*.hdf5`
   * and
   * `hdf5_dump.py -p both -f swtest_run000103_0000_*.hdf5`
