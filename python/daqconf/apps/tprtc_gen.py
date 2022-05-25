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
moo.otypes.load_types('appfwk/cmd.jsonnet')
moo.otypes.load_types('appfwk/app.jsonnet')

moo.otypes.load_types('timinglibs/timingpartitioncontroller.jsonnet')
moo.otypes.load_types('networkmanager/nwmgr.jsonnet')

# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd, 
import dunedaq.rcif.cmd as rccmd # AddressedCmd, 
import dunedaq.appfwk.cmd as cmd # AddressedCmd, 
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.timinglibs.timingpartitioncontroller as tprtc
import dunedaq.networkmanager.nwmgr as nwmgr

from appfwk.utils import acmd, mcmd, mrccmd, mspec
from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Direction

#===============================================================================
def get_tprtc_app(MASTER_DEVICE_NAME="",
                  TIMING_PARTITION_ID=0,
                  TRIGGER_MASK=0xff,
                  RATE_CONTROL_ENABLED=True,
                  SPILL_GATE_ENABLED=False,
                  TIMING_PARTITION="UNKNOWN",
                  TIMING_HOST="np04-srv-012.cern.ch",
                  TIMING_PORT=12345,
                  HOST="localhost",
                  DEBUG=False):
    
    modules = {}

    modules = [DAQModule(name = "tprtc",
                         plugin = "TimingPartitionController",
                         conf = tprtc.PartitionConfParams(
                                             device=MASTER_DEVICE_NAME,
                                             partition_id=TIMING_PARTITION_ID,
                                             trigger_mask=TRIGGER_MASK,
                                             spill_gate_enabled=SPILL_GATE_ENABLED,
                                             rate_control_enabled=RATE_CONTROL_ENABLED,
                                             ))]

    mgraph = ModuleGraph(modules)
     
    mgraph.add_external_connection("timing_cmds", "tprtc.hardware_commands_out", Direction.OUT, TIMING_HOST, TIMING_PORT)
    mgraph.add_external_connection("timing_cmds", "tprtc.timing_cmds", Direction.OUT, TIMING_HOST, TIMING_PORT)
    mgraph.add_external_connection("timing_device_info", None, Direction.IN, TIMING_HOST, TIMING_PORT+1, [MASTER_DEVICE_NAME])

    tprtc_app = App(modulegraph=mgraph, host=HOST, name="TPRTCApp")
     
    if DEBUG:
        tprtc_app.export("tprtc_app.dot")

    return tprtc_app
