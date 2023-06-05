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

moo.otypes.load_types('hsilibs/fakehsieventgenerator.jsonnet')
moo.otypes.load_types('readoutlibs/readoutconfig.jsonnet')

# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd,
import dunedaq.rcif.cmd as rccmd # AddressedCmd,
import dunedaq.appfwk.cmd as cmd # AddressedCmd,
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.hsilibs.fakehsieventgenerator as fhsig
import dunedaq.readoutlibs.readoutconfig as rconf

from appfwk.utils import acmd, mcmd, mrccmd, mspec
    
from daqconf.core.daqmodule import DAQModule
from daqconf.core.app import ModuleGraph, App
from daqconf.core.conf_utils import Direction, Queue
        
import math

#===============================================================================
def get_fake_hsi_app(RUN_NUMBER=333,
                     CLOCK_SPEED_HZ: int=62500000,
                     DATA_RATE_SLOWDOWN_FACTOR: int=1,
                     TRIGGER_RATE_HZ: int=1,
                     HSI_SOURCE_ID: int=0,
                     MEAN_SIGNAL_MULTIPLICITY: int=0,
                     SIGNAL_EMULATION_MODE: int=0,
                     ENABLED_SIGNALS: int=0b00000001,
                     QUEUE_POP_WAIT_MS=10,
                     LATENCY_BUFFER_SIZE=100000,
                     DATA_REQUEST_TIMEOUT=1000,
                     HOST="localhost",
                     DEBUG=False):
    
    region_id=0
    element_id=0
    
    trigger_interval_ticks = 0
    if TRIGGER_RATE_HZ > 0:
        trigger_interval_ticks = math.floor((1 / TRIGGER_RATE_HZ) * CLOCK_SPEED_HZ / DATA_RATE_SLOWDOWN_FACTOR)

    startpars = rccmd.StartParams(run=RUN_NUMBER, trigger_rate = TRIGGER_RATE_HZ)

    modules = [DAQModule(name   = 'fhsig',
                         plugin = "FakeHSIEventGenerator",
                         conf   =  fhsig.Conf(clock_frequency=CLOCK_SPEED_HZ/DATA_RATE_SLOWDOWN_FACTOR,
                                              trigger_rate=TRIGGER_RATE_HZ,
                                              mean_signal_multiplicity=MEAN_SIGNAL_MULTIPLICITY,
                                              signal_emulation_mode=SIGNAL_EMULATION_MODE,
                                              enabled_signals=ENABLED_SIGNALS),
                         extra_commands = {"start": startpars})]
    
    
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
    
    queues = [Queue(f"fhsig.output",f"hsi_datahandler.raw_input","HSIFrame", f'hsi_link_0', 100000)]

    mgraph = ModuleGraph(modules, queues=queues)
    
    mgraph.add_fragment_producer(id = HSI_SOURCE_ID, subsystem = "HW_Signals_Interface",
                                         requests_in   = f"hsi_datahandler.request_input",
                                         fragments_out = f"hsi_datahandler.fragment_queue")
    mgraph.add_endpoint(f"timesync_fake_hsi", f"hsi_datahandler.timesync_output","TimeSync", Direction.OUT, is_pubsub=True, toposort=False)

    mgraph.add_endpoint("hsievents", "fhsig.hsievents", "HSIEvent", Direction.OUT)
    mgraph.add_endpoint(None, None, data_type="TimeSync", inout=Direction.IN, is_pubsub=True)
    fake_hsi_app = App(modulegraph=mgraph, host=HOST, name="FakeHSIApp")
    
    return fake_hsi_app

