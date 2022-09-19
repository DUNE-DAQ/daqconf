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

def get_dqm_app( DATA_RATE_SLOWDOWN_FACTOR=1,
                 CLOCK_SPEED_HZ=50000000,
                 DQMIDX=0,
                 KAFKA_ADDRESS='',
                 CMAP='HD',
                 RAW_PARAMS=[60, 50],
                 RMS_PARAMS=[10, 1000],
                 STD_PARAMS=[10, 1000],
                 FOURIER_CHANNEL_PARAMS=[600, 100],
                 FOURIER_PLANE_PARAMS=[60, 1000],
                 LINKS=[],
                 HOST="localhost",
                 MODE="readout",
                 DF_RATE=10,
                 DF_ALGS='hist mean_rms fourier_sum',
                 DF_TIME_WINDOW=0,
                 FRONTEND_TYPE='wib',
                 DEBUG=False,
                 ):

    modules = []

    if MODE == 'readout':

        modules += [DAQModule(name='trb_dqm',
                            plugin='TriggerRecordBuilder',
                            conf=trb.ConfParams(# This needs to be done in connect_fragment_producers
                                general_queue_timeout=QUEUE_POP_WAIT_MS,
                                source_id = DQMIDX,
                                max_time_window=0,
                                map=trb.mapsourceidconnections([])
                            ))]

    # Algorithms to run for TRs coming from DF
    algs = DF_ALGS.split(' ')

    algs_bitfield = 0
    for i, name in enumerate(['hist', 'mean_rms', 'fourier', 'fourier_sum']):
        if name in algs:
            algs_bitfield |= 1<<i

    modules += [DAQModule(name='dqmprocessor',
                          plugin='DQMProcessor',
                          conf=dqmprocessor.Conf(
                              channel_map=DQM_CMAP, # 'HD' for horizontal drift (PD1), PD2HD or 'VD' for vertical drift
                              mode=MODE,
                              hist=dqmprocessor.StandardDQM(**{'how_often' : DQM_RAWDISPLAY_PARAMS[0], 'num_frames' : DQM_RAWDISPLAY_PARAMS[1]}),
                              rms=dqmprocessor.StandardDQM(**{'how_often' : DQM_RMS_PARAMS[0], 'num_frames' : DQM_RMS_PARAMS[1]}),
                              std=dqmprocessor.StandardDQM(**{'how_often' : DQM_STD_PARAMS[0], 'num_frames' : DQM_STD_PARAMS[1]}),
                              fourier_channel=dqmprocessor.StandardDQM(**{'how_often' : DQM_FOURIER_CHANNEL_PARAMS[0], 'num_frames' : DQM_FOURIER_CHANNEL_PARAMS[1]}),
                              fourier_plane=dqmprocessor.StandardDQM(**{'how_often' : DQM_FOURIER_PLANE_PARAMS[0], 'num_frames' : DQM_FOURIER_PLANE_PARAMS[1]}),
                              kafka_address=DQM_KAFKA_ADDRESS,
                              link_idx=LINKS,
                              clock_frequency=CLOCK_SPEED_HZ,
                              timesync_topic_name = f"Timesync",
                              df2dqm_connection_name=f"tr_df2dqm_{DQMIDX}" if MODE == "df" else '',
                              dqm2df_connection_name=f"trmon_dqm2df_{DQMIDX}" if MODE == "df" else '',
                              readout_window_offset=10**7 / DATA_RATE_SLOWDOWN_FACTOR, # 10^7 works fine for WIBs with no slowdown
                              df_seconds=DF_RATE if MODE == 'df' else 0,
                              df_offset=DF_RATE * DQMIDX if MODE == 'df' else 0,
                              df_algs=algs_bitfield,
                              df_num_frames=DF_TIME_WINDOW / 25,
                              frontend_type=FRONTEND_TYPE,
                          )
                          )
                          ]

    mgraph = ModuleGraph(modules)

    mgraph.add_endpoint("timesync_{DQMIDX}", None, Direction.IN, ["Timesync"])
    if MODE == 'readout':
        mgraph.connect_modules("dqmprocessor.trigger_decision_input_queue", "trb_dqm.trigger_decision_input", 'trigger_decision_q_dqm')
        mgraph.connect_modules('trb_dqm.trigger_record_output', 'dqmprocessor.trigger_record_dqm_processor', 'trigger_record_q_dqm', toposort=False)  
    else:
        mgraph.add_endpoint(f'trmon_dqm2df_{DQMIDX}', None, Direction.OUT)
        mgraph.add_endpoint(f"tr_df2dqm_{DQMIDX}", None, Direction.IN, toposort=True)
    
    dqm_app = App(mgraph, host=HOST)

    if DEBUG:
        dqm_app.export("dqm_app.dot")

    return dqm_app
