# testapp_noreadout_two_process.py

# This python configuration produces *two* json configuration files
# that together form a MiniDAQApp with the same functionality as
# MiniDAQApp v1, but in two processes. One process contains the
# TriggerDecisionEmulator, while the other process contains everything
# else.
#
# As with testapp_noreadout_confgen.py
# in this directory, no modules from the readout package are used: the
# fragments are provided by the FakeDataProd module from dfmodules

import math
from rich.console import Console
console = Console()

# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
moo.otypes.load_types('rcif/cmd.jsonnet')
moo.otypes.load_types('timinglibs/hsireadout.jsonnet')
moo.otypes.load_types('timinglibs/hsicontroller.jsonnet')

import dunedaq.rcif.cmd as rccmd # AddressedCmd, 
import dunedaq.timinglibs.hsireadout as hsi
import dunedaq.timinglibs.hsicontroller as hsic

from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Direction

#===============================================================================
def get_hsi_app(RUN_NUMBER = 333,
                CLOCK_SPEED_HZ: int = 50000000,
                TRIGGER_RATE_HZ: int = 1,
                CONTROL_HSI_HARDWARE = False,
                READOUT_PERIOD_US: int = 1e3,
                HSI_ENDPOINT_ADDRESS = 1,
                HSI_ENDPOINT_PARTITION = 0,
                HSI_RE_MASK = 0x20000,
                HSI_FE_MASK = 0,
                HSI_INV_MASK = 0,
                HSI_SOURCE = 1,
                CONNECTIONS_FILE="${TIMING_SHARE}/config/etc/connections.xml",
                HSI_DEVICE_NAME="BOREAS_TLU",
                UHAL_LOG_LEVEL="notice",
                TIMING_PARTITION="UNKNOWN",
                TIMING_HOST="np04-srv-012.cern.ch",
                TIMING_PORT=12345,
                HOST="localhost",
                DEBUG=False):
    modules = {}

    ## TODO all the connections...
    modules = [DAQModule(name = "hsir",
                        plugin = "HSIReadout",
                        conf = hsi.ConfParams(connections_file=CONNECTIONS_FILE,
                                            readout_period=READOUT_PERIOD_US,
                                            hsi_device_name=HSI_DEVICE_NAME,
                                            uhal_log_level=UHAL_LOG_LEVEL,
                                            hsievent_connection_name = "hsievents"))]
    
    trigger_interval_ticks=0
    if TRIGGER_RATE_HZ > 0:
        trigger_interval_ticks=math.floor((1/TRIGGER_RATE_HZ) * CLOCK_SPEED_HZ)
    elif CONTROL_HSI_HARDWARE:
        console.log('WARNING! Emulated trigger rate of 0 will not disable signal emulation in real HSI hardware! To disable emulated HSI triggers, use  option: "--hsi-source 0" or mask all signal bits', style="bold red")
    
    startpars = rccmd.StartParams(run=RUN_NUMBER, trigger_rate = TRIGGER_RATE_HZ)
    # resumepars = rccmd.ResumeParams(trigger_interval_ticks = trigger_interval_ticks)

    if CONTROL_HSI_HARDWARE:
        modules.extend( [
                        DAQModule(name="hsic",
                                plugin = "HSIController",
                                conf = hsic.ConfParams( device=HSI_DEVICE_NAME,
                                                        clock_frequency=CLOCK_SPEED_HZ,
                                                        trigger_rate=TRIGGER_RATE_HZ,
                                                        address=HSI_ENDPOINT_ADDRESS,
                                                        partition=HSI_ENDPOINT_PARTITION,
                                                        rising_edge_mask=HSI_RE_MASK,
                                                        falling_edge_mask=HSI_FE_MASK,
                                                        invert_edge_mask=HSI_INV_MASK,
                                                        data_source=HSI_SOURCE),
                                extra_commands = {"start": startpars}),
                        ] )
    
    mgraph = ModuleGraph(modules)
    
    if CONTROL_HSI_HARDWARE:
        mgraph.add_external_connection("timing_cmds", "hsic.timing_cmds", Direction.OUT, TIMING_HOST, TIMING_PORT)
        mgraph.add_external_connection("timing_device_info", None, Direction.IN, TIMING_HOST, TIMING_PORT+1, [HSI_DEVICE_NAME])

    mgraph.add_endpoint("hsievents", None,     Direction.OUT)
    mgraph.add_endpoint(None, None, Direction.IN, ["Timesync"])
    
    hsi_app = App(modulegraph=mgraph, host=HOST, name="HSIApp")
    
    if DEBUG:
        hsi_app.export("hsi_app.dot")

    return hsi_app
