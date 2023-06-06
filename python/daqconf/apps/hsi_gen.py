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
moo.otypes.load_types('hsilibs/hsireadout.jsonnet')
moo.otypes.load_types('hsilibs/hsicontroller.jsonnet')
moo.otypes.load_types('readoutlibs/readoutconfig.jsonnet')

import dunedaq.rcif.cmd as rccmd # AddressedCmd, 
import dunedaq.hsilibs.hsireadout as hsir
import dunedaq.hsilibs.hsicontroller as hsic
import dunedaq.readoutlibs.readoutconfig as rconf

from ..core.app import App, ModuleGraph
from ..core.daqmodule import DAQModule
from ..core.conf_utils import Direction, Queue

#===============================================================================
def get_timing_hsi_app(RUN_NUMBER = 333,
                CLOCK_SPEED_HZ: int = 62500000,
                TRIGGER_RATE_HZ: int = 1,
                DATA_RATE_SLOWDOWN_FACTOR: int=1,
                CONTROL_HSI_HARDWARE = False,
                READOUT_PERIOD_US: int = 1e3,
                HSI_ENDPOINT_ADDRESS = 1,
                HSI_ENDPOINT_PARTITION = 0,
                HSI_RE_MASK = 0x20000,
                HSI_FE_MASK = 0,
                HSI_INV_MASK = 0,
                HSI_SOURCE = 1,
                HSI_SOURCE_ID = 0,
                CONNECTIONS_FILE="${TIMING_SHARE}/config/etc/connections.xml",
                HSI_DEVICE_NAME="BOREAS_TLU",
                UHAL_LOG_LEVEL="notice",
                QUEUE_POP_WAIT_MS=10,
                LATENCY_BUFFER_SIZE=100000,
                DATA_REQUEST_TIMEOUT=1000,
                TIMING_SESSION="",
                HARDWARE_STATE_RECOVERY_ENABLED=True,
                HOST="localhost",
                DEBUG=False):
    modules = {}

    ## TODO all the connections...
    modules = [DAQModule(name = "hsir",
                        plugin = "HSIReadout",
                        conf = hsir.ConfParams(connections_file=CONNECTIONS_FILE,
                                            readout_period=READOUT_PERIOD_US,
                                            hsi_device_name=HSI_DEVICE_NAME,
                                            uhal_log_level=UHAL_LOG_LEVEL))]
    
    region_id=0
    element_id=0

    modules += [DAQModule(name = f"hsi_datahandler",
                        plugin = "HSIDataLinkHandler",
                        conf = rconf.Conf(readoutmodelconf = rconf.ReadoutModelConf(source_queue_timeout_ms = QUEUE_POP_WAIT_MS,
                                                                                    source_id=HSI_SOURCE_ID,
                                                                                    send_partial_fragment_if_available = True),
                                             latencybufferconf = rconf.LatencyBufferConf(latency_buffer_size = LATENCY_BUFFER_SIZE,
                                                                                         source_id=HSI_SOURCE_ID),
                                             rawdataprocessorconf = rconf.RawDataProcessorConf(source_id=HSI_SOURCE_ID,
                                                                                               clock_speed_hz=(CLOCK_SPEED_HZ/DATA_RATE_SLOWDOWN_FACTOR)),
                                             requesthandlerconf= rconf.RequestHandlerConf(latency_buffer_size = LATENCY_BUFFER_SIZE,
                                                                                          pop_limit_pct = 0.8,
                                                                                          pop_size_pct = 0.1,
                                                                                          source_id=HSI_SOURCE_ID,
                                                                                          # output_file = f"output_{idx + MIN_LINK}.out",
                                                                                          request_timeout_ms = DATA_REQUEST_TIMEOUT,
                                                                                          warn_about_empty_buffer = False,
                                                                                          enable_raw_recording = False)
                                             ))]

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
                                                        hardware_state_recovery_enabled=HARDWARE_STATE_RECOVERY_ENABLED,
                                                        timing_session_name=TIMING_SESSION,
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
    
    queues = [Queue(f"hsir.output",f"hsi_datahandler.raw_input", "HSIFrame", f'hsi_link_0', 100000)]

    mgraph = ModuleGraph(modules, queues=queues)
    
    mgraph.add_fragment_producer(id = HSI_SOURCE_ID, subsystem = "HW_Signals_Interface",
                                         requests_in   = f"hsi_datahandler.request_input",
                                         fragments_out = f"hsi_datahandler.fragment_queue")
    mgraph.add_endpoint(f"timesync_timing_hsi", f"hsi_datahandler.timesync_output",  "TimeSync",  Direction.OUT, is_pubsub=True, toposort=False)

    
    if CONTROL_HSI_HARDWARE:
        mgraph.add_endpoint("timing_cmds", "hsic.timing_cmds", "TimingHwCmd", Direction.OUT, check_endpoints=False)
        mgraph.add_endpoint(HSI_DEVICE_NAME+"_info", "hsic."+HSI_DEVICE_NAME+"_info", "JSON", Direction.IN, is_pubsub=True, check_endpoints=False)

    mgraph.add_endpoint("hsievents", "hsir.hsievents", "HSIEvent",    Direction.OUT)
    
    # dummy subscriber
    mgraph.add_endpoint(None, None, data_type="TimeSync", inout=Direction.IN, is_pubsub=True)

    hsi_app = App(modulegraph=mgraph, host=HOST, name="HSIApp")
    
    return hsi_app
