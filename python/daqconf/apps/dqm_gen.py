# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
moo.otypes.load_types('rcif/cmd.jsonnet')
moo.otypes.load_types('appfwk/cmd.jsonnet')
moo.otypes.load_types('appfwk/app.jsonnet')
moo.otypes.load_types('dfmodules/triggerrecordbuilder.jsonnet')
moo.otypes.load_types('dfmodules/fragmentreceiver.jsonnet')
moo.otypes.load_types('dqm/dqmprocessor.jsonnet')

# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd,
import dunedaq.rcif.cmd as rccmd # AddressedCmd,
import dunedaq.appfwk.cmd as cmd # AddressedCmd,
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.dfmodules.triggerrecordbuilder as trb
import dunedaq.dfmodules.fragmentreceiver as frcv
import dunedaq.dqm.dqmprocessor as dqmprocessor

from appfwk.utils import acmd, mcmd, mrccmd, mspec

from daqconf.core.conf_utils import Direction
from daqconf.core.daqmodule import DAQModule
from daqconf.core.app import App,ModuleGraph

# Time to wait on pop()
QUEUE_POP_WAIT_MS = 100
# local clock speed Hz
# CLOCK_SPEED_HZ = 50000000;

def get_dqm_app(RU_CONFIG=[],
                 RU_NAME='',
                 EMULATOR_MODE=False,
                 DATA_RATE_SLOWDOWN_FACTOR=1,
                 RUN_NUMBER=333,
                 DATA_FILE="./frames.bin",
                 CLOCK_SPEED_HZ=50000000,
                 DQMIDX=0,
                 SYSTEM_TYPE='TPC',
                 DQM_KAFKA_ADDRESS='',
                 DQM_CMAP='HD',
                 DQM_RAWDISPLAY_PARAMS=[60, 10, 50],
                 DQM_MEANRMS_PARAMS=[10, 1, 100],
                 DQM_FOURIER_PARAMS=[600, 60, 100],
                 DQM_FOURIERSUM_PARAMS=[10, 1, 8192],
                 HOST="localhost",
                 NUM_DF_APPS=1,
                 MODE="readout",
                 DF_RATE=10,
                 DF_ALGS='hist mean_rms fourier_sum',
                 DF_TIME_WINDOW=0,
                 DEBUG=False,
                 ):

    cmd_data = {}

    modules = []

    if MODE == 'readout':

        MIN_LINK = RU_CONFIG[DQMIDX]["start_channel"]
        MAX_LINK = MIN_LINK + RU_CONFIG[DQMIDX]["channel_count"]

        modules += [DAQModule(name='trb_dqm',
                            plugin='TriggerRecordBuilder',
                            conf=trb.ConfParams(# This needs to be done in connect_fragment_producers
                                general_queue_timeout=QUEUE_POP_WAIT_MS,
                                max_time_window=0,
                                map=trb.mapgeoidconnections([])
                            ))]

    # if this is a DQM-DF app
    else:
        MIN_LINK = RU_CONFIG[0]["start_channel"]
        MAX_LINK = RU_CONFIG[-1]["start_channel"] + RU_CONFIG[-1]["channel_count"]

    # Algorithms to run for TRs coming from DF
    algs = DF_ALGS.split(' ')

    algs_bitfield = 0
    for i, name in enumerate(['hist', 'mean_rms', 'fourier', 'fourier_sum']):
        if name in algs:
            algs_bitfield |= 1<<i

    modules += [DAQModule(name='dqmprocessor',
                          plugin='DQMProcessor',
                          conf=dqmprocessor.Conf(
                              region=RU_CONFIG[DQMIDX if MODE == 'readout' else 0]["region_id"],
                              channel_map=DQM_CMAP, # 'HD' for horizontal drift or 'VD' for vertical drift
                              mode=MODE,
                              sdqm_hist=dqmprocessor.StandardDQM(**{'how_often' : DQM_RAWDISPLAY_PARAMS[0], 'unavailable_time' : DQM_RAWDISPLAY_PARAMS[1], 'num_frames' : DQM_RAWDISPLAY_PARAMS[2]}),
                              sdqm_mean_rms=dqmprocessor.StandardDQM(**{'how_often' : DQM_MEANRMS_PARAMS[0], 'unavailable_time' : DQM_MEANRMS_PARAMS[1], 'num_frames' : DQM_MEANRMS_PARAMS[2]}),
                              sdqm_fourier=dqmprocessor.StandardDQM(**{'how_often' : DQM_FOURIER_PARAMS[0], 'unavailable_time' : DQM_FOURIER_PARAMS[1], 'num_frames' : DQM_FOURIER_PARAMS[2]}),
                              sdqm_fourier_sum=dqmprocessor.StandardDQM(**{'how_often' : DQM_FOURIERSUM_PARAMS[0], 'unavailable_time' : DQM_FOURIERSUM_PARAMS[1], 'num_frames' : DQM_FOURIERSUM_PARAMS[2]}),
                              kafka_address=DQM_KAFKA_ADDRESS,
                              link_idx=list(range(MIN_LINK, MAX_LINK)),
                              clock_frequency=CLOCK_SPEED_HZ,
                              timesync_connection_name = f"timesync_{DQMIDX}",
                              df2dqm_connection_name=f"tr_df2dqm_{DQMIDX}" if DQMIDX < NUM_DF_APPS else '',
                              dqm2df_connection_name=f"trmon_dqm2df_{DQMIDX}" if DQMIDX < NUM_DF_APPS else '',
                              readout_window_offset=10**7 / DATA_RATE_SLOWDOWN_FACTOR, # 10^7 works fine for WIBs with no slowdown
                              df_seconds=DF_RATE * NUM_DF_APPS if MODE == 'df' else 0,
                              df_offset=DF_RATE * DQMIDX,
                              df_algs=algs_bitfield,
                              df_num_frames=DF_TIME_WINDOW / 25,
                          )
                          )
                          ]

    mgraph = ModuleGraph(modules)

    mgraph.add_endpoint(None, None, Direction.IN, ["Timesync"])
    if MODE == 'readout':
        mgraph.connect_modules("dqmprocessor.trigger_decision_input_queue", "trb_dqm.trigger_decision_input", 'trigger_decision_q_dqm')
        mgraph.connect_modules('trb_dqm.trigger_record_output', 'dqmprocessor.trigger_record_dqm_processor', 'trigger_record_q_dqm', toposort=False)  
    elif DQMIDX < NUM_DF_APPS:
        mgraph.add_endpoint(f'trmon_dqm2df_{DQMIDX}', None, Direction.OUT)
        mgraph.add_endpoint(f"tr_df2dqm_{DQMIDX}", None, Direction.IN)
    
    dqm_app = App(mgraph, host=HOST)

    if DEBUG:
        dqm_app.export("dqm_app.dot")

    return dqm_app
