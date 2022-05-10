# testapp_noreadout_two_process.py

# This python configuration produces *two* json configuration files
# that together form a MiniDAQApp with the same functionality as
# MiniDAQApp v1, but in two processes.  One process contains the
# TriggerDecisionEmulator, while the other process contains everything
# else.
#
# As with testapp_noreadout_confgen.py
# in this directory, no modules from the readout package are used: the
# fragments are provided by the FakeDataProd module from dfmodules


# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
moo.otypes.load_types('rcif/cmd.jsonnet')
moo.otypes.load_types('appfwk/cmd.jsonnet')
moo.otypes.load_types('appfwk/app.jsonnet')

moo.otypes.load_types('timinglibs/timinghardwaremanagerpdi.jsonnet')
moo.otypes.load_types('networkmanager/nwmgr.jsonnet')

# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd,
import dunedaq.rcif.cmd as rccmd # AddressedCmd,
import dunedaq.appfwk.cmd as cmd # AddressedCmd,
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.timinglibs.timinghardwaremanagerpdi as thi
import dunedaq.networkmanager.nwmgr as nwmgr

from appfwk.utils import acmd, mcmd, mrccmd, mspec
from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Direction

#===============================================================================
def get_thi_app(GATHER_INTERVAL=1e6,
                GATHER_INTERVAL_DEBUG=10e6,
                MASTER_DEVICE_NAME="",
                HSI_DEVICE_NAME="",
                CONNECTIONS_FILE="${TIMING_SHARE}/config/etc/connections.xml",
                UHAL_LOG_LEVEL="notice",
                TIMING_PARTITION="UNKNOWN",
                TIMING_PORT=12345,
                HOST="localhost",
                DEBUG=False):
    
    modules = {}
    modules = [ 
                DAQModule( name="thi",
                                plugin="TimingHardwareManagerPDI",
                                conf= thi.ConfParams(connections_file=CONNECTIONS_FILE,
                                                       gather_interval=GATHER_INTERVAL,
                                                       gather_interval_debug=GATHER_INTERVAL_DEBUG,
                                                       monitored_device_name_master=MASTER_DEVICE_NAME,
                                                       monitored_device_names_fanout=[],
                                                       monitored_device_name_endpoint="",
                                                       monitored_device_name_hsi=HSI_DEVICE_NAME,
                                                       uhal_log_level=UHAL_LOG_LEVEL)),
                ]                
        
    mgraph = ModuleGraph(modules)
    mgraph.add_partition_connection(TIMING_PARTITION, "timing_cmds", "thi.timing_cmds_in", Direction.IN, HOST, TIMING_PORT)

    thi_app = App(modulegraph=mgraph, host=HOST, name="THIApp")
    
    if DEBUG:
        thi_app.export("thi_app.dot")

    return thi_app
