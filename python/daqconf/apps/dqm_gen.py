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
moo.otypes.load_types('dqm/dqmprocessor.jsonnet')

# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd,
import dunedaq.rcif.cmd as rccmd # AddressedCmd,
import dunedaq.appfwk.cmd as cmd # AddressedCmd,
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.dfmodules.triggerrecordbuilder as trb
import dunedaq.dqm.dqmprocessor as dqmprocessor

from appfwk.utils import acmd, mcmd, mrccmd, mspec

from daqconf.core.conf_utils import Direction
from daqconf.core.daqmodule import DAQModule
from daqconf.core.app import App,ModuleGraph

from detdataformats._daq_detdataformats_py import *

# Time to wait on pop()
QUEUE_POP_WAIT_MS = 100
# local clock speed Hz
# CLOCK_SPEED_HZ = 50000000;

def get_dqm_app(sourceid, common_conf, dqm_conf, dro_config, idx, ru_name_with_underscore='', debug=False):

    '''
    DQM_IMPL='',
    DATA_RATE_SLOWDOWN_FACTOR=1,
    CLOCK_SPEED_HZ=50000000,
    DQMIDX=0,
    MAX_NUM_FRAMES=32768,
    KAFKA_ADDRESS='',
    KAFKA_TOPIC='',
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
    DF_ALGS='raw std fourier_plane',
    DF_TIME_WINDOW=0,
    DRO_CONFIG=None,
    RU_APPNAME_WITH_UNDERSCORE="ru_0",
    TRB_DQM_SOURCEID_OFFSET=0,
    DEBUG=False,
    '''
    DATA_RATE_SLOWDOWN_FACTOR = common_conf.data_rate_slowdown_factor
    CLOCK_SPEED_HZ            = common_conf.clock_speed_hz

    TRB_DQM_SOURCEID_OFFSET = sourceid.get_next_source_id("TRBuilder")

    DQMIDX = idx
    LINKS  = dqm_links
    DRO_CONFIG = dro_config
    RU_APPNAME_WITH_UNDERSCORE = ru_name_with_underscore

    dqm_links = [link.dro_source_id for dro_config in dro_infos for link in dro_config.links]

    DQM_IMPL                   = dqm_conf.impl
    MAX_NUM_FRAMES             = dqm_conf.max_num_frames
    KAFKA_ADDRESS              = dqm_conf.kafka_address
    KAFKA_TOPIC                = dqm_conf.kafka_topic
    CMAP                       = dqm_conf.cmap
    RAW_PARAMS                 = dqm_conf.raw_params
    RMS_PARAMS                 = dqm_conf.rms_params
    STD_PARAMS                 = dqm_conf.std_params
    FOURIER_CHANNEL_PARAMS     = dqm_conf.fourier_channel_params
    FOURIER_PLANE_PARAMS       = dqm_conf.fourier_plane_params
    HOST                       = dqm_conf.host_dqm[DQMIDX % len(dqm_conf.host_dqm)]

    FRONTEND_TYPE = DetID.subdetector_to_string(DetID.Subdetector(DRO_CONFIG.links[0].det_id))
    if ((FRONTEND_TYPE== "HD_TPC" or FRONTEND_TYPE== "VD_Bottom_TPC") and CLOCK_SPEED_HZ== 50000000):
        FRONTEND_TYPE = "wib"
    elif ((FRONTEND_TYPE== "HD_TPC" or FRONTEND_TYPE== "VD_Bottom_TPC") and CLOCK_SPEED_HZ== 62500000):
        FRONTEND_TYPE = "wib2"
    elif FRONTEND_TYPE== "HD_PDS" or FRONTEND_TYPE== "VD_Cathode_PDS" or FRONTEND_TYPE=="VD_Membrane_PDS":
        FRONTEND_TYPE = "pds_list"
    elif FRONTEND_TYPE== "VD_Top_TPC":
        FRONTEND_TYPE = "tde"
    elif FRONTEND_TYPE== "ND_LAr":
        FRONTEND_TYPE = "pacman"

    if DQM_IMPL == 'cern':
        KAFKA_ADDRESS = "monkafka.cern.ch:30092"

    TICKS = {'wib': 25, 'wib2': 32}

    modules = []

    if MODE == 'readout':

        modules += [DAQModule(name='trb_dqm',
                            plugin='TriggerRecordBuilder',
                            conf=trb.ConfParams(
                                general_queue_timeout=QUEUE_POP_WAIT_MS,
                                source_id = DQMIDX+TRB_DQM_SOURCEID_OFFSET,
                                max_time_window=0
                            ))]

    modules += [DAQModule(name='dqmprocessor',
                          plugin='DQMProcessor',
                          conf=dqmprocessor.Conf(
                              channel_map=CMAP, # 'HD' for horizontal drift (PD1), PD2HD or 'VD' for vertical drift
                              mode=MODE,
                              raw=dqmprocessor.StandardDQM(**{'how_often' : RAW_PARAMS[0], 'num_frames' : RAW_PARAMS[1]}),
                              rms=dqmprocessor.StandardDQM(**{'how_often' : RMS_PARAMS[0], 'num_frames' : RMS_PARAMS[1]}),
                              std=dqmprocessor.StandardDQM(**{'how_often' : STD_PARAMS[0], 'num_frames' : STD_PARAMS[1]}),
                              fourier_channel=dqmprocessor.StandardDQM(**{'how_often' : FOURIER_CHANNEL_PARAMS[0], 'num_frames' : FOURIER_CHANNEL_PARAMS[1]}),
                              fourier_plane=dqmprocessor.StandardDQM(**{'how_often' : FOURIER_PLANE_PARAMS[0], 'num_frames' : FOURIER_PLANE_PARAMS[1]}),
                              kafka_address=KAFKA_ADDRESS,
                              kafka_topic=KAFKA_TOPIC,
                              link_idx=LINKS,
                              clock_frequency=CLOCK_SPEED_HZ,
                              df2dqm_connection_name=f"tr_df2dqm_{DQMIDX}" if MODE == "df" else '',
                              dqm2df_connection_name=f"trmon_dqm2df_{DQMIDX}" if MODE == "df" else '',
                              readout_window_offset=10**7 / DATA_RATE_SLOWDOWN_FACTOR, # 10^7 works fine for WIBs with no slowdown
                              df_seconds=DF_RATE if MODE == 'df' else 0,
                              df_offset=DF_RATE * DQMIDX if MODE == 'df' else 0,
                              df_algs=DF_ALGS,
                              df_num_frames=DF_TIME_WINDOW / (TICKS[FRONTEND_TYPE] if FRONTEND_TYPE in TICKS else 25),
                              max_num_frames=MAX_NUM_FRAMES,
                              frontend_type=FRONTEND_TYPE,
                          )
                          )
                          ]

    mgraph = ModuleGraph(modules)

    if MODE == 'readout':
        mgraph.add_endpoint(f"timesync_{RU_APPNAME_WITH_UNDERSCORE}_.*", "dqmprocessor.timesync_input", "TimeSync", Direction.IN, is_pubsub=True)
        mgraph.connect_modules("dqmprocessor.trigger_decision_output", "trb_dqm.trigger_decision_input", "TriggerDecision", 'trigger_decision_q_dqm')
        mgraph.connect_modules('trb_dqm.trigger_record_output', 'dqmprocessor.trigger_record_input', "TriggerRecord", 'trigger_record_q_dqm', toposort=False)
    else:
        mgraph.add_endpoint(f'trmon_dqm2df_{DQMIDX}', None, "TRMonRequest", Direction.OUT)
        mgraph.add_endpoint(f"tr_df2dqm_{DQMIDX}", None, "TriggerRecord", Direction.IN, toposort=True)

    dqm_app = App(mgraph, host=HOST)

    return dqm_app
