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

from distutils.command.check import check
import math
from rich.console import Console
console = Console()

# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
moo.otypes.load_types('timinglibs/timingpartitioncontroller.jsonnet')
import dunedaq.timinglibs.timingpartitioncontroller as tprtc

from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Direction

#===============================================================================
def get_tprtc_app(MASTER_DEVICE_NAME="",
                  TIMING_PARTITION_ID=0,
                  TRIGGER_MASK=0xff,
                  RATE_CONTROL_ENABLED=True,
                  SPILL_GATE_ENABLED=False,
                  TIMING_SESSION="",
                  HOST="localhost",
                  DEBUG=False):
    
    modules = {}

    modules = [DAQModule(name = "tprtc",
                         plugin = "TimingPartitionController",
                         conf = tprtc.PartitionConfParams(
                                             device=MASTER_DEVICE_NAME,
                                             timing_session_name=TIMING_SESSION,
                                             partition_id=TIMING_PARTITION_ID,
                                             trigger_mask=TRIGGER_MASK,
                                             spill_gate_enabled=SPILL_GATE_ENABLED,
                                             rate_control_enabled=RATE_CONTROL_ENABLED,
                                             ))]

    mgraph = ModuleGraph(modules)

    mgraph.add_endpoint("timing_cmds", "tprtc.timing_cmds", "TimingHwCmd", Direction.OUT, check_endpoints=False)
    mgraph.add_endpoint("timing_device_info", None,"JSON", Direction.IN, is_pubsub=True, check_endpoints=False)

    tprtc_app = App(modulegraph=mgraph, host=HOST, name="TPRTCApp")
     
    return tprtc_app
