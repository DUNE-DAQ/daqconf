# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes
moo.otypes.load_types('rcif/cmd.jsonnet')
moo.otypes.load_types('appfwk/cmd.jsonnet')
moo.otypes.load_types('appfwk/app.jsonnet')

moo.otypes.load_types('flxlibs/felixcardreader.jsonnet')
moo.otypes.load_types('dtpctrllibs/dtpcontroller.jsonnet')
moo.otypes.load_types('readoutlibs/sourceemulatorconfig.jsonnet')
moo.otypes.load_types('readoutlibs/readoutconfig.jsonnet')
moo.otypes.load_types('lbrulibs/pacmancardreader.jsonnet')
moo.otypes.load_types('dfmodules/fakedataprod.jsonnet')
moo.otypes.load_types("dpdklibs/nicreader.jsonnet")


# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd,
import dunedaq.rcif.cmd as rccmd # AddressedCmd,
import dunedaq.appfwk.cmd as cmd # AddressedCmd,
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.readoutlibs.sourceemulatorconfig as sec
import dunedaq.flxlibs.felixcardreader as flxcr
import dunedaq.dtpctrllibs.dtpcontroller as dtpctrl
import dunedaq.readoutlibs.readoutconfig as rconf
import dunedaq.lbrulibs.pacmancardreader as pcr
# import dunedaq.dfmodules.triggerrecordbuilder as trb
import dunedaq.dfmodules.fakedataprod as fdp
import dunedaq.dpdklibs.nicreader as nrc

# from appfwk.utils import acmd, mcmd, mrccmd, mspec
from os import path

import json
from daqconf.core.conf_utils import Direction, Queue
from daqconf.core.sourceid import TPInfo, SourceIDBroker, FWTPID, FWTPOUTID
from daqconf.core.daqmodule import DAQModule
from daqconf.core.app import App, ModuleGraph

# from detdataformats._daq_detdataformats_py import *
from detdataformats import *

## Compute the frament types from detector infos
def compute_data_types(
        det_id : int,
        clk_freq_hz: int,
        ro_protocol: str
    ):
    det_str = DetID.subdetector_to_string(DetID.Subdetector(det_id))

    fe_type = None
    fake_frag_type = None
    queue_frag_type = None

    # if ((det_str== "HD_TPC" or det_str== "VD_Bottom_TPC") and clk_freq_hz== 50000000):
    #     fe_type = "wib"
    #     queue_frag_type="WIBFrame"
    #     fake_frag_type = "ProtoWIB"
    if ((det_str== "HD_TPC" or det_str== "VD_Bottom_TPC") and clk_freq_hz== 62500000 and ro_protocol=='FELIX' ):
        fe_type = "wib2"
        queue_frag_type="WIB2Frame"
        fake_frag_type = "WIB"
    elif ((det_str== "HD_TPC" or det_str== "VD_Bottom_TPC") and clk_freq_hz== 62500000 and ro_protocol=='ETH' ):
        fe_type = "wibeth"
        queue_frag_type="WIBEthFrame"
        fake_frag_type = "WIBEth"
    elif det_str== "HD_PDS" or det_str== "VD_Cathode_PDS" or det_str=="VD_Membrane_PDS":
        fe_type = "pds_stream"
        fake_frag_type = "DAPHNE"
        queue_frag_type = "PDSStreamFrame"
    elif det_str== "VD_Top_TPC":
        fe_type = "tde"
        fake_frag_type = "TDE_AMC"
        queue_frag_type = "TDEFrame"
    else:
        raise ValueError(f"No match for {det_str}, {clk_freq_hz}, {ro_protocol}")


    return fe_type, queue_frag_type, fake_frag_type


###
# Fake Card Reader creator
###
def create_fake_cardreader(
    FRONTEND_TYPE: str,
    QUEUE_FRAGMENT_TYPE: str,
    DATA_RATE_SLOWDOWN_FACTOR: int,
    DATA_FILES: dict,
    DEFAULT_DATA_FILE: str,
    CLOCK_SPEED_HZ: int,
    EMULATED_DATA_TIMES_START_WITH_NOW: bool,
    det_ro_links: list  # This is a list of DROInfo

) -> tuple[list, list]:
    """
    Create a FAKE Card reader module
    """

    conf = sec.Conf(
            link_confs = [
                sec.LinkConfiguration(
                    source_id=link.dro_source_id,
                        slowdown=DATA_RATE_SLOWDOWN_FACTOR,
                        queue_name=f"output_{link.dro_source_id}",
                        data_filename = DATA_FILES[link.det_id] if link.det_id in DATA_FILES.keys() else DEFAULT_DATA_FILE,
                        emu_frame_error_rate=0
                    ) for link in det_ro_links],
            use_now_as_first_data_time=EMULATED_DATA_TIMES_START_WITH_NOW,
            clock_speed_hz=CLOCK_SPEED_HZ,
            queue_timeout_ms = QUEUE_POP_WAIT_MS
            )


    modules = [DAQModule(name = "fake_source",
                            plugin = "FakeCardReader",
                            conf = conf)]
    queues = [
        Queue(
            f"fake_source.output_{link.dro_source_id}",
            f"datahandler_{link.dro_source_id}.raw_input",
            QUEUE_FRAGMENT_TYPE,
            f'{FRONTEND_TYPE}_link_{link.dro_source_id}', 100000
        ) for link in det_ro_links
    ]
    
    return modules, queues


###
# FELIX Card Reader creator
###
def create_felix_cardreader(
        FRONTEND_TYPE: str,
        QUEUE_FRAGMENT_TYPE: str,
        CARD_ID_OVERRIDE: int,
        NUMA_ID: int,
        det_ro_links: list  # This is a list of DROInfo
    ) -> tuple[list, list]:
    """
    Create a FELIX Card Reader (and reader->DHL Queues?)

    [CR]->queues
    """
    link_slr0 = []
    links_slr1 = []
    sids_slr0 = []
    sids_slr1 = []
    for link in det_ro_links:
        if link.dro_slr == 0:
            link_slr0.append(link.dro_link)
            sids_slr0.append(link.dro_source_id)
        if link.dro_slr == 1:
            links_slr1.append(link.dro_link)
            sids_slr1.append(link.dro_source_id)

    link_slr0.sort()
    links_slr1.sort()

    card_id = det_ro_links[0].dro_card if CARD_ID_OVERRIDE == -1 else CARD_ID_OVERRIDE

    modules = []
    queues = []
    if len(link_slr0) > 0:
        modules += [DAQModule(name = 'flxcard_0',
                        plugin = 'FelixCardReader',
                        conf = flxcr.Conf(card_id = card_id,
                                            logical_unit = 0,
                                            dma_id = 0,
                                            chunk_trailer_size = 32,
                                            dma_block_size_kb = 4,
                                            dma_memory_size_gb = 4,
                                            numa_id = NUMA_ID,
                                            links_enabled = link_slr0
                                        )
                    )]
    
    if len(links_slr1) > 0:
        modules += [DAQModule(name = "flxcard_1",
                            plugin = "FelixCardReader",
                            conf = flxcr.Conf(card_id = card_id,
                                                logical_unit = 1,
                                                dma_id = 0,
                                                chunk_trailer_size = 32,
                                                dma_block_size_kb = 4,
                                                dma_memory_size_gb = 4,
                                                numa_id = NUMA_ID,
                                                links_enabled = links_slr1
                                            )
                    )]
    
    # Queues for card reader 1
    queues += [
        Queue(
            f'flxcard_0.output_{idx}',
            f"datahandler_{idx}.raw_input",
            QUEUE_FRAGMENT_TYPE,
            f'{FRONTEND_TYPE}_link_{idx}',
            100000 
        ) for idx in sids_slr0
    ]
    # Queues for card reader 2
    queues += [
        Queue(
            f'flxcard_1.output_{idx}',
            f"datahandler_{idx}.raw_input",
            QUEUE_FRAGMENT_TYPE,
            f'{FRONTEND_TYPE}_link_{idx}',
            100000 
        ) for idx in sids_slr1
    ]
   
    return modules, queues



###
# DPDK Card Reader creator
###
def create_dpdk_cardreader(
        FRONTEND_TYPE: str,
        QUEUE_FRAGMENT_TYPE: str,
        BASE_SOURCE_IP: str,
        DESTINATION_IP: str,
        EAL_ARGS: str,
        det_ro_links: list  # This is a list of DROInfo
    ) -> tuple[list, list]:
    """
    Create a DPDK Card Reader (and reader->DHL Queues?)

    [CR]->queues
    """
    NUMBER_OF_GROUPS = 1
    NUMBER_OF_LINKS_PER_GROUP = 1

    # number_of_dlh = NUMBER_OF_GROUPS

    links = []
    rxcores = []
    lid = 0
    last_ip = 100
    for group in range(NUMBER_OF_GROUPS):
        offset= 0
        qlist = []
        for _ in range(NUMBER_OF_LINKS_PER_GROUP):
            links.append(
                nrc.Link(
                    id=lid,
                    ip=BASE_SOURCE_IP+str(last_ip),
                    rx_q=lid, 
                    lcore=group+1
                    )
                )
            qlist.append(lid)
            lid += 1
            last_ip += 1
        offset += NUMBER_OF_LINKS_PER_GROUP

    modules = [DAQModule(
                name="nic_reader",
                plugin="NICReceiver",
                conf=nrc.Conf(
                    eal_arg_list=EAL_ARGS,
                    dest_ip=DESTINATION_IP,
                    rx_cores=rxcores,
                    ip_sources=links
                ),
            )]

    # Queues
    queues = [
        Queue(
            f"nic_reader.output_{link.dro_source_id}",
            f"datahandler_{link.dro_source_id}.raw_input", QUEUE_FRAGMENT_TYPE,
            f'{FRONTEND_TYPE}_link_{link.dro_source_id}', 100000
        ) 
        for link in det_ro_links
    ]
    
    return modules, queues

###
# Create detector datalink handlers
###
def create_det_dhl(
        RUIDX: str,
        LATENCY_BUFFER_SIZE: int,
        LATENCY_BUFFER_NUMA_AWARE: int,
        LATENCY_BUFFER_ALLOCATION_MODE: int,
        NUMA_ID: int,
        SEND_PARTIAL_FRAGMENTS: bool,
        RAW_RECORDING_OUTPUT_DIR: str,
        DATA_REQUEST_TIMEOUT: int,
        FRAGMENT_SEND_TIMEOUT: int,
        RAW_RECORDING_ENABLED: bool,
        det_ro_links: list  # This is a list of DROInfo    
    ) -> tuple[list, list]:
    
    det_id = det_ro_links[0].det_id
    modules = []
    for link in det_ro_links:
        modules += [DAQModule(
                    name = f"datahandler_{link.dro_source_id}",
                    plugin = "DataLinkHandler", 
                    conf = rconf.Conf(
                        readoutmodelconf= rconf.ReadoutModelConf(
                            source_queue_timeout_ms= QUEUE_POP_WAIT_MS,
                            # fake_trigger_flag=0, # default
                            source_id =  link.dro_source_id,
                            send_partial_fragment_if_available = SEND_PARTIAL_FRAGMENTS
                        ),
                        latencybufferconf= rconf.LatencyBufferConf(
                            latency_buffer_alignment_size = 4096,
                            latency_buffer_size = LATENCY_BUFFER_SIZE,
                            source_id =  link.dro_source_id,
                            latency_buffer_numa_aware = LATENCY_BUFFER_NUMA_AWARE,
                            latency_buffer_numa_node = NUMA_ID,
                            latency_buffer_preallocation = LATENCY_BUFFER_ALLOCATION_MODE,
                            latency_buffer_intrinsic_allocator = LATENCY_BUFFER_ALLOCATION_MODE,
                        ),
                        rawdataprocessorconf= rconf.RawDataProcessorConf(),
                        requesthandlerconf= rconf.RequestHandlerConf(
                            latency_buffer_size = LATENCY_BUFFER_SIZE,
                            pop_limit_pct = 0.8,
                            pop_size_pct = 0.1,
                            source_id = link.dro_source_id,
                            det_id = det_id,
                            output_file = path.join(RAW_RECORDING_OUTPUT_DIR, f"output_{RUIDX}_{link.dro_source_id}.out"),
                            stream_buffer_size = 8388608,
                            request_timeout_ms = DATA_REQUEST_TIMEOUT,
                            fragment_send_timeout_ms = FRAGMENT_SEND_TIMEOUT,
                            enable_raw_recording = RAW_RECORDING_ENABLED,
                        ))
                )]
    queues = []
    return modules, queues


###
# Enable processing in DHLs
###
def add_tp_processing(
        dro_dlh_list: list,
        THRESHOLD_TPG: int,
        ALGORITHM_TPG: int,
        CHANNEL_MASK_TPG: list,
        TPG_CHANNEL_MAP: str,
        EMULATOR_MODE,
        CLOCK_SPEED_HZ: int,
        DATA_RATE_SLOWDOWN_FACTOR: int,
        SOURCEID_BROKER: SourceIDBroker,
    ) -> list:

    modules = []
    queues = []


    # Loop over datalink handlers to re-define the data processor configuration
    for dlh in dro_dlh_list:

        # Recover the raw data link source id
        # MOOOOOO
        dro_sid = dlh.conf.readoutmodelconf["source_id"]

        # Reserve a TP source id
        tp_sid = SOURCEID_BROKER.get_next_source_id("Trigger")
        SOURCEID_BROKER.register_source_id("Trigger", tp_sid, None)

        # Re-create the module with an extended configuration
        modules += [DAQModule(
            name = dlh.name,
            plugin = dlh.plugin,
            conf = rconf.Conf(
                readoutmodelconf = dlh.conf.readoutmodelconf,
                latencybufferconf = dlh.conf.latencybufferconf,
                requesthandlerconf = dlh.conf.requesthandlerconf,
                rawdataprocessorconf= rconf.RawDataProcessorConf(
                    source_id = dro_sid,
                    enable_software_tpg = True,
                    software_tpg_threshold = THRESHOLD_TPG,
                    software_tpg_algorithm = ALGORITHM_TPG,
                    software_tpg_channel_mask = CHANNEL_MASK_TPG,
                    channel_map_name = TPG_CHANNEL_MAP,
                    emulator_mode = EMULATOR_MODE,
                    clock_speed_hz = (CLOCK_SPEED_HZ / DATA_RATE_SLOWDOWN_FACTOR),
                    error_counter_threshold=100,
                    error_reset_freq=10000,
                    tpset_sourceid=tp_sid
                ),
            )
        )]
        
    return modules, queues

###
# Create TP data link handlers
###
def create_tp_dlhs(
    dro_dlh_list: list,
    LATENCY_BUFFER_SIZE: int, # To Check
    DATA_REQUEST_TIMEOUT: int, # To Check
    FRAGMENT_SEND_TIMEOUT: int, # To Check
    )-> tuple[list, list]:
    
    modules = []
    queues = []
    
    for dlh in dro_dlh_list:

        # extract source ids
        dro_sid = dlh.conf.readoutmodelconf["source_id"]
        tp_sid = dlh.conf.rawdataprocessorconf["tpset_sourceid"]

        modules += [
            DAQModule(name = f"tp_datahandler_{tp_sid}",
                plugin = "DataLinkHandler",
                conf = rconf.Conf(
                            readoutmodelconf = rconf.ReadoutModelConf(
                                source_queue_timeout_ms = QUEUE_POP_WAIT_MS,
                                source_id = tp_sid
                            ),
                            latencybufferconf = rconf.LatencyBufferConf(
                                latency_buffer_size = LATENCY_BUFFER_SIZE,
                                source_id =  tp_sid
                            ),
                            rawdataprocessorconf = rconf.RawDataProcessorConf(),
                            requesthandlerconf= rconf.RequestHandlerConf(
                                latency_buffer_size = LATENCY_BUFFER_SIZE,
                                pop_limit_pct = 0.8,
                                pop_size_pct = 0.1,
                                source_id = tp_sid,
                                det_id = 1,
                                # output_file = f"output_{idx + MIN_LINK}.out",
                                stream_buffer_size = 8388608,
                                request_timeout_ms = DATA_REQUEST_TIMEOUT,
                                fragment_send_timeout_ms = FRAGMENT_SEND_TIMEOUT,
                                enable_raw_recording = False
                            )
                        )
                )
            ]

        # Attach to the detector DLH's tp_out connector
        queues += [
            Queue(
                f"{dlh.name}.tp_out",
                f"tp_datahandler_{tp_sid}.raw_input",
                "TriggerPrimitive",
                f"sw_tp_link_{dro_sid}",100000 
                )
            ]

    return modules, queues

###
# Add detector endpoints and fragment producers
###
def add_dro_eps_and_fps(
    mgraph: ModuleGraph,
    dro_dlh_list: list,
    RUIDX: str,
        
) -> None: 
    """Adds detector readout endpoints and fragment producers"""
    for dlh in dro_dlh_list:

        # extract source ids
        dro_sid = dlh.conf.readoutmodelconf['source_id']
        # tp_sid = dlh.conf.rawdataprocessorconf.tpset_sourceid

        mgraph.add_fragment_producer(
            id = dro_sid, 
            subsystem = "Detector_Readout",
            requests_in   = f"datahandler_{dro_sid}.request_input",
            fragments_out = f"datahandler_{dro_sid}.fragment_queue"
        )
        mgraph.add_endpoint(
            f"timesync_ru{RUIDX}_{dro_sid}",
            f"datahandler_{dro_sid}.timesync_output",
            "TimeSync",   Direction.OUT,
            is_pubsub=True,
            toposort=False
        )

        # if processing is enabled, add a pubsub endooint for TPSets
        if dlh.conf.rawdataprocessorconf['enable_software_tpg']:
            mgraph.add_endpoint(
                f"tpsets_ru{RUIDX}_link{dro_sid}",
                f"datahandler_{dro_sid}.tpset_out",
                "TPSet",
                Direction.OUT,
                is_pubsub=True
            )


###
# Add tpg endpoints and fragment producers
###
def add_tpg_eps_and_fps(
    mgraph: ModuleGraph,
    # dro_dlh_list: list,
    tpg_dlh_list: list,
    RUIDX: str,
        
) -> None: 
    """Adds detector readout endpoints and fragment producers"""

    for dlh in tpg_dlh_list:

        # extract source ids
        tp_sid = dlh.conf.readoutmodelconf['source_id']

        # Add enpoint with this source id
        mgraph.add_endpoint(
            f"timesync_tp_dlh_ru{RUIDX}_{tp_sid}",
            f"tp_datahandler_{tp_sid}.timesync_output",
            "TimeSync",
            Direction.OUT,
            is_pubsub=True
        )

        # Add Fragment producer with this source id
        mgraph.add_fragment_producer(
            id = tp_sid, subsystem = "Trigger",
            requests_in   = f"tp_datahandler_{tp_sid}.request_input",
            fragments_out = f"tp_datahandler_{tp_sid}.fragment_queue"
        )

# Time to wait on pop()
QUEUE_POP_WAIT_MS = 10 # This affects stop time, as each link will wait this long before stop

def create_readout_app(
    DRO_CONFIG,
    EMULATOR_MODE=False,
    DATA_RATE_SLOWDOWN_FACTOR=1,
    DEFAULT_DATA_FILE="./frames.bin",
    DATA_FILES={},
    FLX_INPUT=False,
    ETH_MODE=False,
    CLOCK_SPEED_HZ=50000000,
    RAW_RECORDING_ENABLED=False,
    RAW_RECORDING_OUTPUT_DIR=".",
    CHANNEL_MASK_TPG: list = [],
    THRESHOLD_TPG=120,
    ALGORITHM_TPG="SWTPG",
    TPG_ENABLED=False,                                        
    TPG_CHANNEL_MAP= "ProtoDUNESP1ChannelMap",
    USE_FAKE_DATA_PRODUCERS=False,
    DATA_REQUEST_TIMEOUT=1000,
    FRAGMENT_SEND_TIMEOUT=10,
    HOST="localhost",
    SOURCEID_BROKER : SourceIDBroker = None,
    READOUT_SENDS_TP_FRAGMENTS=False,
    ENABLE_DPDK_READER=False,
    EAL_ARGS='-l 0-1 -n 3 -- -m [0:1].0 -j',
    BASE_SOURCE_IP="10.73.139.",
    DESTINATION_IP="10.73.139.17",
    NUMA_ID=0,
    LATENCY_BUFFER_SIZE=499968,
    LATENCY_BUFFER_NUMA_AWARE = False,
    LATENCY_BUFFER_ALLOCATION_MODE = False,

    CARD_ID_OVERRIDE = -1,
    EMULATED_DATA_TIMES_START_WITH_NOW = False,
    DEBUG=False
):

  
    host = DRO_CONFIG.host.replace("-","_")
    RUIDX = f"{host}_{DRO_CONFIG.card}"

    FRONTEND_TYPE, QUEUE_FRAGMENT_TYPE, _ = compute_data_types(DRO_CONFIG.links[0].det_id, CLOCK_SPEED_HZ,'FELIX'  if not ETH_MODE else 'ETH')

    modules = []
    queues = []

    cr_mods = []
    cr_queues = []

    # Create the card readers
    if FLX_INPUT:
        flx_mods, flx_queues = create_felix_cardreader(
            FRONTEND_TYPE,
            QUEUE_FRAGMENT_TYPE,
            CARD_ID_OVERRIDE,
            NUMA_ID,
            DRO_CONFIG.links
        )
        cr_mods += flx_mods
        cr_queues += flx_queues

    elif ETH_MODE:
        dpdk_mods, dpdk_queues = create_dpdk_cardreader(
            FRONTEND_TYPE=FRONTEND_TYPE,
            QUEUE_FRAGMENT_TYPE=QUEUE_FRAGMENT_TYPE,
            BASE_SOURCE_IP=BASE_SOURCE_IP,
            DESTINATION_IP=DESTINATION_IP,
            EAL_ARGS=EAL_ARGS,
            det_ro_links=DRO_CONFIG.links
        )
        cr_mods += dpdk_mods
        cr_queues += dpdk_queues

    else:
        fakecr_mods, fakecr_queues = create_fake_cardreader(
            FRONTEND_TYPE=FRONTEND_TYPE,
            QUEUE_FRAGMENT_TYPE=QUEUE_FRAGMENT_TYPE,
            DATA_RATE_SLOWDOWN_FACTOR=DATA_RATE_SLOWDOWN_FACTOR,
            DATA_FILES=DATA_FILES,
            DEFAULT_DATA_FILE=DEFAULT_DATA_FILE,
            CLOCK_SPEED_HZ=CLOCK_SPEED_HZ,
            EMULATED_DATA_TIMES_START_WITH_NOW=EMULATED_DATA_TIMES_START_WITH_NOW,
            det_ro_links=DRO_CONFIG.links
        )
        cr_mods += fakecr_mods
        cr_queues += fakecr_queues


    modules += cr_mods
    queues += cr_queues

    # Create the data-link handlers
    dlhs_mods, _ = create_det_dhl(
        RUIDX,
        LATENCY_BUFFER_SIZE=LATENCY_BUFFER_SIZE,
        LATENCY_BUFFER_NUMA_AWARE=LATENCY_BUFFER_NUMA_AWARE,
        LATENCY_BUFFER_ALLOCATION_MODE=LATENCY_BUFFER_ALLOCATION_MODE,
        NUMA_ID=NUMA_ID,
        SEND_PARTIAL_FRAGMENTS=False,
        RAW_RECORDING_OUTPUT_DIR=RAW_RECORDING_OUTPUT_DIR,
        DATA_REQUEST_TIMEOUT=DATA_REQUEST_TIMEOUT,
        FRAGMENT_SEND_TIMEOUT=FRAGMENT_SEND_TIMEOUT,
        RAW_RECORDING_ENABLED=RAW_RECORDING_ENABLED,
        det_ro_links=DRO_CONFIG.links

    )

    if TPG_ENABLED:
        dlhs_mods = add_tp_processing(
           dro_dlh_list=dlhs_mods,
           THRESHOLD_TPG=THRESHOLD_TPG,
           ALGORITHM_TPG=ALGORITHM_TPG,
           CHANNEL_MASK_TPG=CHANNEL_MASK_TPG,
           TPG_CHANNEL_MAP=TPG_CHANNEL_MAP,
           EMULATOR_MODE=EMULATOR_MODE,
           CLOCK_SPEED_HZ=CLOCK_SPEED_HZ,
           DATA_RATE_SLOWDOWN_FACTOR=DATA_RATE_SLOWDOWN_FACTOR,
           SOURCEID_BROKER=SOURCEID_BROKER
        )

    modules += dlhs_mods

    if READOUT_SENDS_TP_FRAGMENTS:
        tpg_mods, tpg_queues = create_tp_dlhs(
            dro_dlh_list=dlhs_mods,
            LATENCY_BUFFER_SIZE=LATENCY_BUFFER_SIZE,
            DATA_REQUEST_TIMEOUT=DATA_REQUEST_TIMEOUT,
            FRAGMENT_SEND_TIMEOUT=FRAGMENT_SEND_TIMEOUT
        )
        modules += tpg_mods
        queues += tpg_queues

    mgraph = ModuleGraph(modules, queues=queues)

    # Add endpoints and frame producers to DRO data handlers
    add_dro_eps_and_fps(
        mgraph=mgraph,
        dro_dlh_list=dlhs_mods,
        RUIDX=RUIDX
    )

    if READOUT_SENDS_TP_FRAGMENTS:
       # Add endpoints and frame producers to TP data handlers
        add_tpg_eps_and_fps(
            mgraph=mgraph,
            # dro_dlh_list=dlhs_mods,
            tpg_dlh_list=tpg_mods,
            RUIDX=RUIDX
        )

    readout_app = App(mgraph, host=HOST)
    return readout_app











######## Legacy code beyond this point


# def get_readout_app(DRO_CONFIG=None,
#                     EMULATOR_MODE=False,
#                     DATA_RATE_SLOWDOWN_FACTOR=1,
#                     # RUN_NUMBER=333, 
#                     DEFAULT_DATA_FILE="./frames.bin",
#                     DATA_FILES={},
#                     FLX_INPUT=False,
#                     ETH_MODE=False,
#                     CLOCK_SPEED_HZ=50000000,
#                     RAW_RECORDING_ENABLED=False,
#                     RAW_RECORDING_OUTPUT_DIR=".",
#                     CHANNEL_MASK_TPG: list = [],
#                     THRESHOLD_TPG=120,
#                     ALGORITHM_TPG="SWTPG",
#                     TPG_ENABLED=False,                                        
#                     # FIRMWARE_TPG_ENABLED=False,
#                     # DTP_CONNECTIONS_FILE="${DTPCONTROLS_SHARE}/config/dtp_connections.xml",
#                     # FIRMWARE_HIT_THRESHOLD=20,
#                     TPG_CHANNEL_MAP= "ProtoDUNESP1ChannelMap",
#                     USE_FAKE_DATA_PRODUCERS=False,
#                     DATA_REQUEST_TIMEOUT=1000,
#                     FRAGMENT_SEND_TIMEOUT=10,
#                     HOST="localhost",
#                     SOURCEID_BROKER : SourceIDBroker = None,
#                     READOUT_SENDS_TP_FRAGMENTS=False,
#                     # ENABLE_DPDK_SENDER=False,
#                     ENABLE_DPDK_READER=False,
#                     EAL_ARGS='-l 0-1 -n 3 -- -m [0:1].0 -j',
#                     BASE_SOURCE_IP="10.73.139.",
#                     DESTINATION_IP="10.73.139.17",
#                     NUMA_ID=0,

#                     LATENCY_BUFFER_SIZE=499968,
#                     LATENCY_BUFFER_NUMA_AWARE = False,
#                     LATENCY_BUFFER_ALLOCATION_MODE = False,

                    
#                     CARD_ID_OVERRIDE = -1,
#                     EMULATED_DATA_TIMES_START_WITH_NOW = False,
#                     DEBUG=False):
#     """Generate the json configuration for the readout process"""
    
#     if DRO_CONFIG is None:
#         raise RuntimeError(f"ERROR: DRO_CONFIG is None!")

#     # Hack on strings to be used for connection instances: will be solved when data_type is properly used.
#     # FAKEDATA_FRAGMENT_TYPE = "Unknown"
#     # QUEUE_FRAGMENT_TYPE="WIBFrame"
#     # FRONTEND_TYPE = DetID.subdetector_to_string(DetID.Subdetector(DRO_CONFIG.links[0].det_id))
#     # if ((FRONTEND_TYPE== "HD_TPC" or FRONTEND_TYPE== "VD_Bottom_TPC") and CLOCK_SPEED_HZ== 50000000):
#     #     FRONTEND_TYPE = "wib"
#     #     QUEUE_FRAGMENT_TYPE="WIBFrame"
#     #     FAKEDATA_FRAGMENT_TYPE = "ProtoWIB"
#     # elif ((FRONTEND_TYPE== "HD_TPC" or FRONTEND_TYPE== "VD_Bottom_TPC") and CLOCK_SPEED_HZ== 62500000 and ETH_MODE==False ):
#     #     FRONTEND_TYPE = "wib2"
#     #     QUEUE_FRAGMENT_TYPE="WIB2Frame"
#     #     FAKEDATA_FRAGMENT_TYPE = "WIB"
#     # elif ((FRONTEND_TYPE== "HD_TPC" or FRONTEND_TYPE== "VD_Bottom_TPC") and CLOCK_SPEED_HZ== 62500000 and ETH_MODE==True):
#     #     FRONTEND_TYPE = "wibeth"
#     #     QUEUE_FRAGMENT_TYPE="WIBEthFrame"
#     #     FAKEDATA_FRAGMENT_TYPE = "WIBEth"
#     # elif FRONTEND_TYPE== "HD_PDS" or FRONTEND_TYPE== "VD_Cathode_PDS" or FRONTEND_TYPE=="VD_Membrane_PDS":
#     #     FRONTEND_TYPE = "pds_stream"
#     #     FAKEDATA_FRAGMENT_TYPE = "DAPHNE"
#     #     QUEUE_FRAGMENT_TYPE = "PDSStreamFrame"
#     # elif FRONTEND_TYPE== "VD_Top_TPC":
#     #     FRONTEND_TYPE = "tde"
#     #     FAKEDATA_FRAGMENT_TYPE = "TDE_AMC"
#     #     QUEUE_FRAGMENT_TYPE = "TDEFrame"
#     # elif FRONTEND_TYPE== "NDLAr_TPC":
#     #     FRONTEND_TYPE = "pacman"
#     #     FAKEDATA_FRAGMENT_TYPE = "PACMAN"
#     #     QUEUE_FRAGMENT_TYPE = "PACMANFrame"
#     # elif FRONTEND_TYPE== "NDLAr_PDS":
#     #     FRONTEND_TYPE = "mpd"
#     #     FAKEDATA_FRAGMENT_TYPE = "MPD"
#     #     QUEUE_FRAGMENT_TYPE = "MPDFrame"

#     FRONTEND_TYPE, QUEUE_FRAGMENT_TYPE, FAKEDATA_FRAGMENT_TYPE = compute_data_types(DRO_CONFIG.links[0].det_id, CLOCK_SPEED_HZ,'FELIX'  if not ETH_MODE else 'ETH')
        
#     print(f' in readout gen FRONTENT_TYPE={FRONTEND_TYPE}')

#     if DEBUG: print(f'FRONTENT_TYPE={FRONTEND_TYPE}')

#     # For raw recording to work the size of the LB has to be a multiple of 4096 bytes so that gives
#     # us the following problem:
#     # number_of_elements * element_size = 4096 * M,  where M is an arbitrary integer,
#     # so only a value of number_elements that satisfies the equation above is valid.
#     if FRONTEND_TYPE == 'tde':
#         # number_of_elements = 4096 is always a solution by construction and
#         # the total size happens to be quite close to the one when using WIB
#         # as the frontend type
#         LATENCY_BUFFER_SIZE = 4096

#     # RS: Ignore FE type for DPDK receiver. Should NOT matter.
#     #if (ENABLE_DPDK_SENDER or ENABLE_DPDK_READER) and FRONTEND_TYPE != 'wibeth':
#     #    raise RuntimeError(f'DPDK is only supported when using the frontend type TDE, current frontend type is {FRONTEND_TYPE}')
#     # if ENABLE_DPDK_SENDER and not ENABLE_DPDK_READER:
#     #     raise RuntimeError('The DPDK sender can not be enabled and the DPDK reader disabled')

#     # cmd_data = {}

#     # RATE_KHZ = CLOCK_SPEED_HZ / (25 * 12 * DATA_RATE_SLOWDOWN_FACTOR * 1000)
    
#     if DEBUG: print(f"ReadoutApp.__init__ with host={DRO_CONFIG.host} and {len(DRO_CONFIG.links)} links enabled")

#     if DEBUG: print(f'FRONTENT_TYPE={FRONTEND_TYPE}')

#     modules = []
#     queues = []

#     host = DRO_CONFIG.host.replace("-","_")
#     RUIDX = f"{host}_{DRO_CONFIG.card}"

#     link_to_tp_sid_map = {}
#     # fw_tp_id_map = {}
#     # fw_tp_out_id_map = {}

#     if TPG_ENABLED:
#         # if FRONTEND_TYPE == 'pacman' or FRONTEND_TYPE == 'mpd':
#         #     print('ERROR: Cannot configure Software TPG for pacman or mpd data')
#         #     exit()

#     # if TPG_ENABLED:
#         for link in DRO_CONFIG.links:
#             link_to_tp_sid_map[link.dro_source_id] = SOURCEID_BROKER.get_next_source_id("Trigger")
#             SOURCEID_BROKER.register_source_id("Trigger", link_to_tp_sid_map[link.dro_source_id], None)
#     # if FIRMWARE_TPG_ENABLED:
#     #     for fwsid,fwconf in SOURCEID_BROKER.get_all_source_ids("Detector_Readout").items():
#     #         if isinstance(fwconf, FWTPID) and fwconf.host == DRO_CONFIG.host and fwconf.card == DRO_CONFIG.card:
#     #             if DEBUG: print(f"SSB fwsid: {fwsid}")
#     #             fw_tp_id_map[fwconf] = fwsid
#     #             link_to_tp_sid_map[fwconf] = SOURCEID_BROKER.get_next_source_id("Trigger")
#     #             SOURCEID_BROKER.register_source_id("Trigger", link_to_tp_sid_map[fwconf], None)
#     #         if isinstance(fwconf, FWTPOUTID) and fwconf.host == DRO_CONFIG.host and fwconf.card == DRO_CONFIG.card:
#     #             if DEBUG: print(f"SSB fw tp out id: {fwconf}")
#     #             fw_tp_out_id_map[fwconf] = fwsid

#         # if DEBUG: print(f"SSB fw_tp source ID map: {fw_tp_id_map}")
#         # if DEBUG: print(f"SSB fw_tp_out source ID map: {fw_tp_out_id_map}")

#     # if TPG_ENABLED:
#         for link in DRO_CONFIG.links:
#             modules += [DAQModule(name = f"tp_datahandler_{link_to_tp_sid_map[link.dro_source_id]}",
#                                plugin = "DataLinkHandler",
#                                conf = rconf.Conf(readoutmodelconf = rconf.ReadoutModelConf(source_queue_timeout_ms = QUEUE_POP_WAIT_MS,
#                                                                                          source_id = link_to_tp_sid_map[link.dro_source_id]),
#                                                  latencybufferconf = rconf.LatencyBufferConf(latency_buffer_size = LATENCY_BUFFER_SIZE,
#                                                                                             source_id =  link_to_tp_sid_map[link.dro_source_id]),
#                                                  rawdataprocessorconf = rconf.RawDataProcessorConf(
#                                                                                                 #     source_id = link_to_tp_sid_map[link.dro_source_id],
#                                                                                                 #    enable_software_tpg = False,
#                                                                                                 #    software_tpg_threshold = THRESHOLD_TPG,
#                                                                                                 #    software_tpg_algorithm = ALGORITHM_TPG,               
#                                                                                                 #    software_tpg_channel_mask = CHANNEL_MASK_TPG,
#                                                                                                 #    channel_map_name=TPG_CHANNEL_MAP
#                                                                                                    ),
#                                                  requesthandlerconf= rconf.RequestHandlerConf(latency_buffer_size = LATENCY_BUFFER_SIZE,
#                                                                                               pop_limit_pct = 0.8,
#                                                                                               pop_size_pct = 0.1,
#                                                                                               source_id = link_to_tp_sid_map[link.dro_source_id],
#                                                                                               det_id = 1,
#                                                                                               # output_file = f"output_{idx + MIN_LINK}.out",
#                                                                                               stream_buffer_size = 100 if FRONTEND_TYPE=='pacman' else 8388608,
#                                                                                               request_timeout_ms = DATA_REQUEST_TIMEOUT,
#                                                                                               fragment_send_timeout_ms = FRAGMENT_SEND_TIMEOUT,
#                                                                                               enable_raw_recording = False)))]
#     # if FIRMWARE_TPG_ENABLED:
#     #     assert(len(fw_tp_out_id_map) <= 2)
#     #     assert(len(fw_tp_id_map) <= 2)
#     #     for tp, tp_out in zip(fw_tp_id_map.values(), fw_tp_out_id_map.values()):
#     #         # for sid in fw_tp_out_id_map.values():
#     #         queues += [Queue(f"tp_datahandler_{tp}.tp_out",f"tp_out_datahandler_{tp_out}.raw_input", "TriggerPrimitive",f"sw_tp_link_{tp_out}",100000 )]                
#     #         modules += [DAQModule(name = f"tp_out_datahandler_{tp_out}",
#     #                            plugin = "DataLinkHandler",
#     #                            conf = rconf.Conf(readoutmodelconf = rconf.ReadoutModelConf(source_queue_timeout_ms = QUEUE_POP_WAIT_MS,
#     #                                                                                      source_id = tp_out),
#     #                                              latencybufferconf = rconf.LatencyBufferConf(latency_buffer_size = LATENCY_BUFFER_SIZE,
#     #                                                                                          latency_buffer_numa_aware = LATENCY_BUFFER_NUMA_AWARE,
#     #                                                                                          latency_buffer_numa_node = NUMA_ID,
#     #                                                                                          latency_buffer_preallocation = LATENCY_BUFFER_ALLOCATION_MODE,
#     #                                                                                          latency_buffer_intrinsic_allocator = LATENCY_BUFFER_ALLOCATION_MODE,
#     #                                                                                          source_id = tp_out),
#     #                                              rawdataprocessorconf = rconf.RawDataProcessorConf(source_id =  tp_out,
#     #                                                                                                enable_software_tpg = False,
#     #                                                                                                fwtp_fake_timestamp = False,
#     #                                                                                                channel_map_name=TPG_CHANNEL_MAP),
#     #                                              requesthandlerconf= rconf.RequestHandlerConf(latency_buffer_size = LATENCY_BUFFER_SIZE,
#     #                                                                                           pop_limit_pct = 0.8,
#     #                                                                                           pop_size_pct = 0.1,
#     #                                                                                           source_id = tp_out,
#     #                                                                                           det_id = 1,
#     #                                                                                           stream_buffer_size = 100 if FRONTEND_TYPE=='pacman' else 8388608,
#     #                                                                                           request_timeout_ms = DATA_REQUEST_TIMEOUT,
#     #                                                                                           fragment_send_timeout_ms = FRAGMENT_SEND_TIMEOUT,
#     #                                                                                           enable_raw_recording = False)))]
#     #         # for sid in fw_tp_id_map.values():
#     #         queues += [Queue(f"tp_datahandler_{tp}.errored_frames", 'errored_frame_consumer.input_queue',"WIBFrame", "errored_frames_q")]
#     #         modules += [DAQModule(name = f"tp_datahandler_{tp}",
#     #                               plugin = "DataLinkHandler", 
#     #                               conf = rconf.Conf(
#     #                                   readoutmodelconf= rconf.ReadoutModelConf(
#     #                                       source_queue_timeout_ms= QUEUE_POP_WAIT_MS,
#     #                                       # fake_trigger_flag=0, # default
#     #                                       source_id = tp,
#     #                                   ),
#     #                                   latencybufferconf= rconf.LatencyBufferConf(
#     #                                       latency_buffer_alignment_size = 4096,
#     #                                       latency_buffer_size = LATENCY_BUFFER_SIZE,
#     #                                       latency_buffer_numa_aware = LATENCY_BUFFER_NUMA_AWARE,
#     #                                       latency_buffer_numa_node = NUMA_ID,
#     #                                       latency_buffer_preallocation = LATENCY_BUFFER_ALLOCATION_MODE,
#     #                                       latency_buffer_intrinsic_allocator = LATENCY_BUFFER_ALLOCATION_MODE,
#     #                                       source_id = tp,
#     #                                   ),
#     #                                   rawdataprocessorconf= rconf.RawDataProcessorConf(
#     #                                       source_id = tp,
#     #                                       enable_software_tpg = False,
#     #                                       software_tpg_threshold = THRESHOLD_TPG,
#     #                                       software_tpg_algorithm = ALGORITHM_TPG,                                          
#     #                                       software_tpg_channel_mask = CHANNEL_MASK_TPG,
#     #                                       enable_firmware_tpg = True,
#     #                                       fwtp_fake_timestamp = False,
#     #                                       channel_map_name = TPG_CHANNEL_MAP,
#     #                                       emulator_mode = EMULATOR_MODE,
#     #                                       error_counter_threshold=100,
#     #                                       error_reset_freq=10000,
#     #                                       tpset_sourceid=tp,
#     #                                   ),
#     #                                   requesthandlerconf= rconf.RequestHandlerConf(
#     #                                       latency_buffer_size = LATENCY_BUFFER_SIZE,
#     #                                       pop_limit_pct = 0.8,
#     #                                       pop_size_pct = 0.1,
#     #                                       source_id = tp,
#     #                                       det_id = DRO_CONFIG.links[0].det_id,
#     #                                       output_file = path.join(RAW_RECORDING_OUTPUT_DIR, f"output_tp_{RUIDX}_{tp}.out"),
#     #                                       stream_buffer_size = 8388608,
#     #                                       request_timeout_ms = DATA_REQUEST_TIMEOUT,
#     #                                       fragment_send_timeout_ms = FRAGMENT_SEND_TIMEOUT,
#     #                                       enable_raw_recording = RAW_RECORDING_ENABLED,
#     #                                   )))]

#     # if FRONTEND_TYPE == 'wib' and not USE_FAKE_DATA_PRODUCERS:
#     #     modules += [DAQModule(name = "errored_frame_consumer",
#     #                        plugin = "ErroredFrameConsumer")]

#     # There are two flags to be checked so I think a for loop
#     # is the closest way to the blocks that are being used here
    
#     for link in DRO_CONFIG.links:
#         # if USE_FAKE_DATA_PRODUCERS:
#         #     modules += [DAQModule(name = f"fakedataprod_{link.dro_source_id}",
#         #                           plugin='FakeDataProd',
#         #                           conf = fdp.ConfParams(
#         #                           system_type = "Detector_Readout",
#         #                           source_id = link.dro_source_id,
#         #                           time_tick_diff = 25 if CLOCK_SPEED_HZ == 50000000 else 32, # WIB1 only if clock is WIB1 clock, otherwise WIB2
#         #                           frame_size = 464 if CLOCK_SPEED_HZ == 50000000 else 472, # WIB1 only if clock is WIB1 clock, otherwise WIB2
#         #                           response_delay = 0,
#         #                           fragment_type = FAKEDATA_FRAGMENT_TYPE,
#         #                           ))]
#         # else:
#             if TPG_ENABLED:
#                 queues += [Queue(f"datahandler_{link.dro_source_id}.tp_out",f"tp_datahandler_{link_to_tp_sid_map[link.dro_source_id]}.raw_input","TriggerPrimitive",f"sw_tp_link_{link.dro_source_id}",100000 )]                

#             #? why only create errored frames for wib, should this also be created for wib2 or other FE's?
#             # if FRONTEND_TYPE == 'wib':
#             #     queues += [Queue(f"datahandler_{link.dro_source_id}.errored_frames", 'errored_frame_consumer.input_queue',"WIBFrame", "errored_frames_q")]

#             modules += [DAQModule(name = f"datahandler_{link.dro_source_id}",
#                                   plugin = "DataLinkHandler", 
#                                   conf = rconf.Conf(
#                                       readoutmodelconf= rconf.ReadoutModelConf(
#                                           source_queue_timeout_ms= QUEUE_POP_WAIT_MS,
#                                           # fake_trigger_flag=0, # default
#                                           source_id =  link.dro_source_id,
#                                           send_partial_fragment_if_available = (FRONTEND_TYPE == 'mpd')
#                                       ),
#                                       latencybufferconf= rconf.LatencyBufferConf(
#                                           latency_buffer_alignment_size = 4096,
#                                           latency_buffer_size = LATENCY_BUFFER_SIZE,
#                                           source_id =  link.dro_source_id,
#                                           latency_buffer_numa_aware = LATENCY_BUFFER_NUMA_AWARE,
#                                           latency_buffer_numa_node = NUMA_ID,
#                                           latency_buffer_preallocation = LATENCY_BUFFER_ALLOCATION_MODE,
#                                           latency_buffer_intrinsic_allocator = LATENCY_BUFFER_ALLOCATION_MODE,
#                                       ),
#                                       rawdataprocessorconf= rconf.RawDataProcessorConf(
#                                           source_id =  link.dro_source_id,
#                                           enable_software_tpg = TPG_ENABLED,
#                                           software_tpg_threshold = THRESHOLD_TPG,
#                                           software_tpg_algorithm = ALGORITHM_TPG,
#                                           software_tpg_channel_mask = CHANNEL_MASK_TPG,
#                                           channel_map_name = TPG_CHANNEL_MAP,
#                                           emulator_mode = EMULATOR_MODE,
#                                           clock_speed_hz = (CLOCK_SPEED_HZ / DATA_RATE_SLOWDOWN_FACTOR),
#                                           error_counter_threshold=100,
#                                           error_reset_freq=10000,
#                                           tpset_sourceid=link_to_tp_sid_map[link.dro_source_id] if TPG_ENABLED else 0
#                                       ),
#                                       requesthandlerconf= rconf.RequestHandlerConf(
#                                           latency_buffer_size = LATENCY_BUFFER_SIZE,
#                                           pop_limit_pct = 0.8,
#                                           pop_size_pct = 0.1,
#                                           source_id = link.dro_source_id,
#                                           det_id = DRO_CONFIG.links[0].det_id,
#                                           output_file = path.join(RAW_RECORDING_OUTPUT_DIR, f"output_{RUIDX}_{link.dro_source_id}.out"),
#                                           stream_buffer_size = 8388608,
#                                           request_timeout_ms = DATA_REQUEST_TIMEOUT,
#                                           fragment_send_timeout_ms = FRAGMENT_SEND_TIMEOUT,
#                                           enable_raw_recording = RAW_RECORDING_ENABLED,
#                                       )))]

                    
#     if not USE_FAKE_DATA_PRODUCERS:
#         if FLX_INPUT:
#             link_0 = []
#             link_1 = []
#             sid_0 = []
#             sid_1 = []
#             for link in DRO_CONFIG.links:
#                 if link.dro_slr == 0:
#                     link_0.append(link.dro_link)
#                     sid_0.append(link.dro_source_id)
#                 if link.dro_slr == 1:
#                     link_1.append(link.dro_link)
#                     sid_1.append(link.dro_source_id)
#             for idx in sid_0:
#                 queues += [Queue(f'flxcard_0.output_{idx}',f"datahandler_{idx}.raw_input",QUEUE_FRAGMENT_TYPE, f'{FRONTEND_TYPE}_link_{idx}', 100000 )]
#             for idx in sid_1:
#                 queues += [Queue(f'flxcard_1.output_{idx}',f"datahandler_{idx}.raw_input",QUEUE_FRAGMENT_TYPE, f'{FRONTEND_TYPE}_link_{idx}', 100000 )]
#             # if FIRMWARE_TPG_ENABLED:
#             #     link_0.append(5)
#             #     fw_tp_sid = fw_tp_id_map[FWTPID(DRO_CONFIG.host, DRO_CONFIG.card, 0)]
#             #     queues += [Queue(f'flxcard_0.output_{fw_tp_sid}',f"tp_datahandler_{fw_tp_sid}.raw_input", "TPSet",f'raw_tp_link_{fw_tp_sid}', 100000 )]
#             #     if len(link_1) > 0:
#             #         link_1.append(5)
#             #         fw_tp_sid = fw_tp_id_map[FWTPID(DRO_CONFIG.host, DRO_CONFIG.card, 1)]
#             #         queues += [Queue(f'flxcard_1.output_{fw_tp_sid}',f"tp_datahandler_{fw_tp_sid}.raw_input","TPSet", f'raw_tp_link_{fw_tp_sid}', 100000 )]
            
#             link_0.sort()
#             link_1.sort()

#             modules += [DAQModule(name = 'flxcard_0',
#                                plugin = 'FelixCardReader',
#                                conf = flxcr.Conf(card_id = DRO_CONFIG.links[0].dro_card if CARD_ID_OVERRIDE == -1 else CARD_ID_OVERRIDE,
#                                                  logical_unit = 0,
#                                                  dma_id = 0,
#                                                  chunk_trailer_size = 32,
#                                                  dma_block_size_kb = 4,
#                                                  dma_memory_size_gb = 4,
#                                                  numa_id = NUMA_ID,
#                                                  links_enabled = link_0))]
            
#             if len(link_1) > 0:
#                 modules += [DAQModule(name = "flxcard_1",
#                                    plugin = "FelixCardReader",
#                                    conf = flxcr.Conf(card_id = DRO_CONFIG.links[0].dro_card if CARD_ID_OVERRIDE == -1 else CARD_ID_OVERRIDE,
#                                                      logical_unit = 1,
#                                                      dma_id = 0,
#                                                      chunk_trailer_size = 32,
#                                                      dma_block_size_kb = 4,
#                                                      dma_memory_size_gb = 4,
#                                                      numa_id = NUMA_ID,
#                                                      links_enabled = link_1))]
#         if not ENABLE_DPDK_READER:
#             # DTPController - only required if FW TPs enabled
#             # if FIRMWARE_TPG_ENABLED:
#             #     if len(link_0) > 0:
#             #         modules += [DAQModule(
#             #                     name = 'dtpctrl_0',
#             #                     plugin = 'DTPController',
#             #                     conf = dtpctrl.Conf(connections_file=path.expandvars(DTP_CONNECTIONS_FILE),
#             #                                         device=f"flx-{2*DRO_CONFIG.links[0].dro_card}-p2-hf",
#             #                                         uhal_log_level="notice",
#             #                                         source="ext",
#             #                                         pattern="",
#             #                                         threshold=FIRMWARE_HIT_THRESHOLD,
#             #                                         masks=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]) )]
#             #     if len(link_1) > 0:
#             #         modules += [DAQModule(
#             #                     name = 'dtpctrl_1',
#             #                     plugin = 'DTPController',
#             #                     conf = dtpctrl.Conf(connections_file=path.expandvars(DTP_CONNECTIONS_FILE),
#             #                                         device=f"flx-{(2*DRO_CONFIG.links[0].dro_card) + 1}-p2-hf",
#             #                                         uhal_log_level="notice",
#             #                                         source="ext",
#             #                                         pattern="",
#             #                                         threshold=FIRMWARE_HIT_THRESHOLD,
#             #                                         masks=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]) )]

#             if not FLX_INPUT:
#                 fake_source = "fake_source"
#                 card_reader = "FakeCardReader"
#                 conf = sec.Conf(link_confs = [sec.LinkConfiguration(source_id=link.dro_source_id,
#                                                                     slowdown=DATA_RATE_SLOWDOWN_FACTOR,
#                                                                     queue_name=f"output_{link.dro_source_id}",
#                                                                     data_filename = DATA_FILES[link.det_id] if link.det_id in DATA_FILES.keys() else DEFAULT_DATA_FILE,
#                                                                     emu_frame_error_rate=0) for link in DRO_CONFIG.links],
#                                 use_now_as_first_data_time=EMULATED_DATA_TIMES_START_WITH_NOW,
#                                 clock_speed_hz=CLOCK_SPEED_HZ,
#                                 queue_timeout_ms = QUEUE_POP_WAIT_MS)
#                 if FRONTEND_TYPE=='pacman':
#                     fake_source = "pacman_source"
#                     card_reader = "PacmanCardReader"
#                     conf = pcr.Conf(link_confs = [pcr.LinkConfiguration(Source_ID=link.dro_source_id)
#                                                  for link in DRO_CONFIG.links],
#                                   zmq_receiver_timeout = 10000)
#                 if FRONTEND_TYPE=='mpd':
#                     fake_source = "mpd_source"
#                     card_reader = "PacmanCardReader" # Should be generic for all NDLAR 
#                     conf = pcr.Conf(link_confs = [pcr.LinkConfiguration(Source_ID=link.dro_source_id)
#                                                   for link in DRO_CONFIG.links],
#                                     zmq_receiver_timeout = 10000)

#                 modules += [DAQModule(name = fake_source,
#                                       plugin = card_reader,
#                                       conf = conf)]
#                 queues += [Queue(f"{fake_source}.output_{link.dro_source_id}",f"datahandler_{link.dro_source_id}.raw_input",QUEUE_FRAGMENT_TYPE, f'{FRONTEND_TYPE}_link_{link.dro_source_id}', 100000) for link in DRO_CONFIG.links]

#         else:

#             NUMBER_OF_GROUPS = 1
#             NUMBER_OF_LINKS_PER_GROUP = 1

#             # number_of_dlh = NUMBER_OF_GROUPS

#             links = []
#             rxcores = []
#             lid = 0
#             last_ip = 100
#             for group in range(NUMBER_OF_GROUPS):
#                 offset= 0
#                 qlist = []
#                 for src in range(NUMBER_OF_LINKS_PER_GROUP):
#                     links.append(nrc.Link(id=lid, ip=BASE_SOURCE_IP+str(last_ip), rx_q=lid, lcore=group+1))
#                     qlist.append(lid)
#                     lid += 1
#                     last_ip += 1
#                 offset += NUMBER_OF_LINKS_PER_GROUP

#             modules += [DAQModule(name="nic_reader", plugin="NICReceiver",
#                                 conf=nrc.Conf(eal_arg_list=EAL_ARGS,
#                                                 dest_ip=DESTINATION_IP,
#                                                 rx_cores=rxcores,
#                                                 ip_sources=links),
#                 )]

#             queues += [Queue(f"nic_reader.output_{link.dro_source_id}",
#                              f"datahandler_{link.dro_source_id}.raw_input", QUEUE_FRAGMENT_TYPE,
#                              f'{FRONTEND_TYPE}_link_{link.dro_source_id}', 100000) for link in DRO_CONFIG.links]
                  
#     # modules += [
#     #     DAQModule(name = "fragment_sender",
#     #                    plugin = "FragmentSender",
#     #                    conf = None)]
                        
#     mgraph = ModuleGraph(modules, queues=queues)

#     # if FIRMWARE_TPG_ENABLED:
#     #     tp_key_0 = FWTPID(DRO_CONFIG.host, DRO_CONFIG.card, 0)
#     #     tp_key_1 = FWTPID(DRO_CONFIG.host, DRO_CONFIG.card, 1)
#     #     if tp_key_0 in fw_tp_id_map.keys():
#     #         tp_sid_0 = fw_tp_id_map[tp_key_0]
#     #         mgraph.add_endpoint(f"tpsets_ru{RUIDX}_link{tp_sid_0}", f"tp_datahandler_{tp_sid_0}.tpset_out", "TPSet",   Direction.OUT, is_pubsub=True)
#     #     if tp_key_1 in fw_tp_id_map.keys():
#     #         tp_sid_1 = fw_tp_id_map[tp_key_1]
#     #         mgraph.add_endpoint(f"tpsets_ru{RUIDX}_link{tp_sid_1}", f"tp_datahandler_{tp_sid_1}.tpset_out", "TPSet",   Direction.OUT, is_pubsub=True)

#     #     for sid in fw_tp_id_map.values():
#     #         mgraph.add_fragment_producer(id = sid, subsystem = "Trigger",
#     #                                 requests_in   = f"tp_datahandler_{sid}.request_input",
#     #                                 fragments_out = f"tp_datahandler_{sid}.fragment_queue", is_mlt_producer = READOUT_SENDS_TP_FRAGMENTS)
#     #         mgraph.add_endpoint(f"timesync_{sid}", f"tp_datahandler_{sid}.timesync_output", "TimeSync",   Direction.OUT, is_pubsub=True)
#     #     for sid in fw_tp_out_id_map.values():
#     #         mgraph.add_fragment_producer(id = sid, subsystem = "Trigger",
#     #                                 requests_in   = f"tp_out_datahandler_{sid}.request_input",
#     #                                 fragments_out = f"tp_out_datahandler_{sid}.fragment_queue", is_mlt_producer = READOUT_SENDS_TP_FRAGMENTS)
#     #         mgraph.add_endpoint(f"timesync_tp_out_{sid}", f"tp_out_datahandler_{sid}.timesync_output", "TimeSync",   Direction.OUT, is_pubsub=True)



#     for link in DRO_CONFIG.links:
#         if TPG_ENABLED:
#             mgraph.add_endpoint(f"tpsets_ru{RUIDX}_link{link.dro_source_id}", f"datahandler_{link.dro_source_id}.tpset_out", "TPSet",   Direction.OUT, is_pubsub=True)
#             mgraph.add_endpoint(f"timesync_tp_dlh_ru{RUIDX}_{link_to_tp_sid_map[link.dro_source_id]}", f"tp_datahandler_{link_to_tp_sid_map[link.dro_source_id]}.timesync_output","TimeSync",    Direction.OUT, is_pubsub=True)
        
#         if USE_FAKE_DATA_PRODUCERS:
#             pass
#             # # Add fragment producers for fake data. This call is necessary to create the RequestReceiver instance, but we don't need the generated FragmentSender or its queues...
#             # mgraph.add_fragment_producer(id = link.dro_source_id, subsystem = "Detector_Readout",
#             #                              requests_in   = f"fakedataprod_{link.dro_source_id}.data_request_input_queue",
#             #                              fragments_out = f"fakedataprod_{link.dro_source_id}.fragment_queue")
#             # mgraph.add_endpoint(f"timesync_ru{RUIDX}_{link.dro_source_id}", f"fakedataprod_{link.dro_source_id}.timesync_output",    "TimeSync",   Direction.OUT, is_pubsub=True, toposort=False)
#         else:
#             # Add fragment producers for raw data
#             mgraph.add_fragment_producer(id = link.dro_source_id, subsystem = "Detector_Readout",
#                                          requests_in   = f"datahandler_{link.dro_source_id}.request_input",
#                                          fragments_out = f"datahandler_{link.dro_source_id}.fragment_queue")
#             mgraph.add_endpoint(f"timesync_ru{RUIDX}_{link.dro_source_id}", f"datahandler_{link.dro_source_id}.timesync_output",    "TimeSync",   Direction.OUT, is_pubsub=True, toposort=False)

#             # Add fragment producers for TPC TPs. Make sure the element index doesn't overlap with the ones for raw data
#             #
#             # NB We decided not to request TPs from readout for the
#             # 2.10 release. It would be nice to achieve this by just
#             # not adding fragment producers for the relevant links
#             # here, but then the necessary input and output queues for
#             # the DataLinkHandler modules are not created, so we can't
#             # init. So instead we do it this roundabout way: the
#             # fragment producers are all created, and then they are
#             # eventually removed from the MLT's list of links to
#             # request data from. That removal is done in
#             # daqconf_multiru_gen, which relies on a convention that
#             # TP links have element value > 1000.
#             #
#             # This situation should change after release 2.10, when
#             # real firmware TPs become available
#             if TPG_ENABLED:
#                 mgraph.add_fragment_producer(id = link_to_tp_sid_map[link.dro_source_id], subsystem = "Trigger",
#                                              requests_in   = f"tp_datahandler_{link_to_tp_sid_map[link.dro_source_id]}.request_input",
#                                              fragments_out = f"tp_datahandler_{link_to_tp_sid_map[link.dro_source_id]}.fragment_queue",
#                                                 is_mlt_producer = READOUT_SENDS_TP_FRAGMENTS)
#     # if ENABLE_DPDK_READER:
#     #     for link in DRO_CONFIG.links:
#     #         mgraph.connect_modules(f"datahandler_{link.dro_source_id}.timesync_output", "timesync_consumer.input_queue", "timesync_q")
#     #         mgraph.connect_modules(f"datahandler_{idx}.fragment_queue", "fragment_consumer.input_queue", "data_fragments_q", 100)


#     readout_app = App(mgraph, host=HOST)
#     return readout_app

