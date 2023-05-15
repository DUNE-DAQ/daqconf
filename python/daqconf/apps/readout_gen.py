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
# moo.otypes.load_types('dtpctrellibs/dtpcontroller.jsonnet')
moo.otypes.load_types('readoutlibs/sourceemulatorconfig.jsonnet')
moo.otypes.load_types('readoutlibs/readoutconfig.jsonnet')
# moo.otypes.load_types('lbrulibs/pacmancardreader.jsonnet')
# moo.otypes.load_types('dfmodules/fakedataprod.jsonnet')
moo.otypes.load_types("dpdklibs/nicreader.jsonnet")


# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd,
import dunedaq.rcif.cmd as rccmd # AddressedCmd,
import dunedaq.appfwk.cmd as cmd # AddressedCmd,
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.readoutlibs.sourceemulatorconfig as sec
import dunedaq.flxlibs.felixcardreader as flxcr
# import dunedaq.dtpctrllibs.dtpcontroller as dtpctrl
import dunedaq.readoutlibs.readoutconfig as rconf
# import dunedaq.lbrulibs.pacmancardreader as pcr
# import dunedaq.dfmodules.triggerrecordbuilder as trb
# import dunedaq.dfmodules.fakedataprod as fdp
import dunedaq.dpdklibs.nicreader as nrc

# from appfwk.utils import acmd, mcmd, mrccmd, mspec
from os import path
from itertools import groupby

from daqconf.core.conf_utils import Direction, Queue
from daqconf.core.sourceid import TPInfo, SourceIDBroker, FWTPID, FWTPOUTID
from daqconf.core.daqmodule import DAQModule
from daqconf.core.app import App, ModuleGraph
from daqconf.detreadoutmap import ReadoutUnitDescriptor

# from detdataformats._daq_detdataformats_py import *
from detdataformats import *


### Move to utility module
def group_by_key(coll, key):
    """
    """
    m = {}
    s = sorted(coll, key=key)
    for k, g in groupby(s, key):
        m[k] = list(g)
    return m



## Compute the frament types from detector infos
def compute_data_types(
        det_id : int,
        clk_freq_hz: int,
        tech: str
    ):
    det_str = DetID.subdetector_to_string(DetID.Subdetector(det_id))

    fe_type = None
    fake_frag_type = None
    queue_frag_type = None

    # if ((det_str == "HD_TPC" or det_str== "VD_Bottom_TPC") and clk_freq_hz== 50000000):
    #     fe_type = "wib"
    #     queue_frag_type="WIBFrame"
    #     fake_frag_type = "ProtoWIB"
    # Far detector types
    if ((det_str == "HD_TPC" or det_str == "VD_Bottom_TPC") and clk_freq_hz== 62500000 and tech=='flx' ):
        fe_type = "wib2"
        queue_frag_type="WIB2Frame"
        fake_frag_type = "WIB"
    elif ((det_str == "HD_TPC" or det_str == "VD_Bottom_TPC") and clk_freq_hz== 62500000 and tech=='eth' ):
        fe_type = "wibeth"
        queue_frag_type="WIBEthFrame"
        fake_frag_type = "WIBEth"
    elif det_str == "HD_PDS" or det_str == "VD_Cathode_PDS" or det_str =="VD_Membrane_PDS":
        fe_type = "pds_stream"
        fake_frag_type = "DAPHNE"
        queue_frag_type = "PDSStreamFrame"
    elif det_str == "VD_Top_TPC":
        fe_type = "tde"
        fake_frag_type = "TDE_AMC"
        queue_frag_type = "TDEFrame"

    # Far detector types
    # elif det_str == "NDLAr_TPC":
    #     fe_type = "pacman"
    #     fake_frag_type = "PACMAN"
    #     queue_frag_type = "PACMANFrame"
    # elif det_str == "NDLAr_PDS":
    #     fe_type = "mpd"
    #     fake_frag_type = "MPD"
    #     queue_frag_type = "MPDFrame"
    else:
        raise ValueError(f"No match for {det_str}, {clk_freq_hz}, {tech}")


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
    RU_DESCRIPTOR # ReadoutUnitDescriptor

) -> tuple[list, list]:
    """
    Create a FAKE Card reader module
    """

    conf = sec.Conf(
            link_confs = [
                sec.LinkConfiguration(
                    source_id=s.src_id,
                        slowdown=DATA_RATE_SLOWDOWN_FACTOR,
                        queue_name=f"output_{s.src_id}",
                        data_filename = DATA_FILES[s.geo_id.det_id] if s.geo_id.det_id in DATA_FILES.keys() else DEFAULT_DATA_FILE,
                        emu_frame_error_rate=0
                    ) for s in RU_DESCRIPTOR.streams],
            use_now_as_first_data_time=EMULATED_DATA_TIMES_START_WITH_NOW,
            clock_speed_hz=CLOCK_SPEED_HZ,
            queue_timeout_ms = QUEUE_POP_WAIT_MS
            )


    modules = [DAQModule(name = "fake_source",
                            plugin = "FakeCardReader",
                            conf = conf)]
    queues = [
        Queue(
            f"fake_source.output_{s.src_id}",
            f"datahandler_{s.src_id}.raw_input",
            QUEUE_FRAGMENT_TYPE,
            f'{FRONTEND_TYPE}_link_{s.src_id}', 100000
        ) for s in RU_DESCRIPTOR.streams
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
        RU_DESCRIPTOR # ReadoutUnitDescriptor
    ) -> tuple[list, list]:
    """
    Create a FELIX Card Reader (and reader->DHL Queues?)

    [CR]->queues
    """
    links_slr0 = []
    links_slr1 = []
    sids_slr0 = []
    sids_slr1 = []
    for stream in RU_DESCRIPTOR.streams:
        if stream.config.slr == 0:
            links_slr0.append(stream.config.link)
            sids_slr0.append(stream.src_id)
        if stream.config.slr == 1:
            links_slr1.append(stream.config.link)
            sids_slr1.append(stream.src_id)

    links_slr0.sort()
    links_slr1.sort()

    card_id = RU_DESCRIPTOR.iface if CARD_ID_OVERRIDE == -1 else CARD_ID_OVERRIDE

    modules = []
    queues = []
    if len(links_slr0) > 0:
        modules += [DAQModule(name = 'flxcard_0',
                        plugin = 'FelixCardReader',
                        conf = flxcr.Conf(card_id = card_id,
                                            logical_unit = 0,
                                            dma_id = 0,
                                            chunk_trailer_size = 32,
                                            dma_block_size_kb = 4,
                                            dma_memory_size_gb = 4,
                                            numa_id = NUMA_ID,
                                            links_enabled = links_slr0
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
class NICReceiverBuilder:

    # FIXME: workaround to avoid lcore to be set to 0
    # To be reviewd
    lcore_offset = 1

    def __init__(self, rudesc : ReadoutUnitDescriptor):
        self.desc = rudesc


    def streams_by_host(self):

        iface_map = group_by_key(self.desc.streams, lambda s: s.config.rx_host)

        return iface_map    

    def streams_by_iface(self):

        iface_map = group_by_key(self.desc.streams, lambda s: (s.config.rx_ip, s.config.rx_mac, s.config.rx_host))

        return iface_map

    def streams_by_iface_and_tx_endpoint(self):

        s_by_if = self.streams_by_iface()
        m = {}
        for k,v in s_by_if.items():
            m[k] = group_by_key(v, lambda s: (s.config.tx_ip, s.config.tx_mac, s.config.tx_host))
            
        return m
    
    # def streams_by_ru(self):
    #     m = group_by_key(self.desc.streams, lambda s: (getattr(s.config, self.desc._host_label_map[s.tech]), getattr(s.config, self.desc._iflabel_map[s.tech]), s.tech, s.geo_id.det_id))
    #     return m

    def build_conf(self, eal_arg_list):

        streams_by_if_and_tx = self.streams_by_iface_and_tx_endpoint()

        ifcfgs = []
        for (rx_ip, rx_mac, _),txs in streams_by_if_and_tx.items():
            srcs = []
            # Sid is used for the "Source.id". What is it?

            for sid,((tx_ip,_,_),streams) in enumerate(txs.items()):
                ssm = nrc.SrcStreamsMapping([
                        nrc.StreamMap(source_id=s.src_id, stream_id=s.geo_id.stream_id)
                        for s in streams
                    ])
                geo_id = streams[0].geo_id
                si = nrc.SrcGeoInfo(
                    det_id=geo_id.det_id,
                    crate_id=geo_id.crate_id,
                    slot_id=geo_id.slot_id
                )

                srcs.append(
                    nrc.Source(
                        id=sid, # FIXME what is this ID?
                        ip_addr=tx_ip,
                        lcore=sid+self.lcore_offset,
                        rx_q=sid,
                        src_info=si,
                        src_streams_mapping=ssm
                    )
                )
            ifcfgs.append(
                nrc.Interface(
                    ip_addr=rx_ip,
                    mac_addr=rx_mac,
                    expected_sources=srcs
                )
            )         


        conf = nrc.Conf(
            ifaces = ifcfgs,
            eal_arg_list=eal_arg_list
        )

        return conf

    def build_conf_by_host(self, eal_arg_list):

        streams_by_if_and_tx = self.streams_by_host()

        ifcfgs = []
        for (rx_ip, rx_mac, _),txs in streams_by_if_and_tx.items():
            srcs = []
            # Sid is used for the "Source.id". What is it?

            for sid,((tx_ip,_,_),streams) in enumerate(txs.items()):
                ssm = nrc.SrcStreamsMapping([
                        nrc.StreamMap(source_id=s.src_id, stream_id=s.geo_id.stream_id)
                        for s in streams
                    ])
                geo_id = streams[0].geo_id
                si = nrc.SrcGeoInfo(
                    det_id=geo_id.det_id,
                    crate_id=geo_id.crate_id,
                    slot_id=geo_id.slot_id
                )

                srcs.append(
                    nrc.Source(
                        id=sid, # FIXME what is this ID?
                        ip_addr=tx_ip,
                        lcore=sid+self.lcore_offset,
                        rx_q=sid,
                        src_info=si,
                        src_streams_mapping=ssm
                    )
                )
            ifcfgs.append(
                nrc.Interface(
                    ip_addr=rx_ip,
                    mac_addr=rx_mac,
                    expected_sources=srcs
                )
            )         


        conf = nrc.Conf(
            ifaces = ifcfgs,
            eal_arg_list=eal_arg_list
        )

        return conf

def create_dpdk_cardreader(
        FRONTEND_TYPE: str,
        QUEUE_FRAGMENT_TYPE: str,
        # BASE_SOURCE_IP: str,
        # DESTINATION_IP: str,
        EAL_ARGS: str,
        # RU_STREAMS: list  # This is a list of DROInfo
        RU_DESCRIPTOR # ReadoutUnitDescriptor

    ) -> tuple[list, list]:
    """
    Create a DPDK Card Reader (and reader->DHL Queues?)

    [CR]->queues
    """
    # NUMBER_OF_GROUPS = 1
    # NUMBER_OF_LINKS_PER_GROUP = 1

    # number_of_dlh = NUMBER_OF_GROUPS

    # links = []
    # rxcores = []
    # lid = 0
    # last_ip = 100
    # for group in range(NUMBER_OF_GROUPS):
    #     offset= 0
    #     qlist = []
    #     for _ in range(NUMBER_OF_LINKS_PER_GROUP):
    #         links.append(
    #             nrc.Link(
    #                 id=lid,
    #                 ip=BASE_SOURCE_IP+str(last_ip),
    #                 rx_q=lid, 
    #                 lcore=group+1
    #                 )
    #             )
    #         qlist.append(lid)
    #         lid += 1
    #         last_ip += 1
    #     offset += NUMBER_OF_LINKS_PER_GROUP

    eth_ru_bldr = NICReceiverBuilder(RU_DESCRIPTOR)

    nic_reader_name = f"nic_reader_{RU_DESCRIPTOR.iface}"

    modules = [DAQModule(
                name=nic_reader_name,
                plugin="NICReceiver",
                conf=eth_ru_bldr.build_conf(eal_arg_list=EAL_ARGS),
            )]

    # Queues
    queues = [
        Queue(
            f"{nic_reader_name}.output_{stream.src_id}",
            f"datahandler_{stream.src_id}.raw_input", QUEUE_FRAGMENT_TYPE,
            f'{FRONTEND_TYPE}_stream_{stream.src_id}', 100000
        ) 
        for stream in RU_DESCRIPTOR.streams
    ]
    
    return modules, queues

###
# Create detector datalink handlers
###
def create_det_dhl(
        LATENCY_BUFFER_SIZE: int,
        LATENCY_BUFFER_NUMA_AWARE: int,
        LATENCY_BUFFER_ALLOCATION_MODE: int,
        NUMA_ID: int,
        SEND_PARTIAL_FRAGMENTS: bool,
        RAW_RECORDING_OUTPUT_DIR: str,
        DATA_REQUEST_TIMEOUT: int,
        FRAGMENT_SEND_TIMEOUT: int,
        RAW_RECORDING_ENABLED: bool,
        RU_DESCRIPTOR # ReadoutUnitDescriptor
 
    ) -> tuple[list, list]:
    
    modules = []
    for stream in RU_DESCRIPTOR.streams:
        modules += [DAQModule(
                    name = f"datahandler_{stream.src_id}",
                    plugin = "DataLinkHandler", 
                    conf = rconf.Conf(
                        readoutmodelconf= rconf.ReadoutModelConf(
                            source_queue_timeout_ms= QUEUE_POP_WAIT_MS,
                            # fake_trigger_flag=0, # default
                            source_id =  stream.src_id,
                            send_partial_fragment_if_available = SEND_PARTIAL_FRAGMENTS
                        ),
                        latencybufferconf= rconf.LatencyBufferConf(
                            latency_buffer_alignment_size = 4096,
                            latency_buffer_size = LATENCY_BUFFER_SIZE,
                            source_id =  stream.src_id,
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
                            source_id = stream.src_id,
                            det_id = RU_DESCRIPTOR.det_id,
                            output_file = path.join(RAW_RECORDING_OUTPUT_DIR, f"output_{RU_DESCRIPTOR.label}_{stream.src_id}.out"),
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
        
    return modules

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
        print(dlh)

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
    # DRO_CONFIG,
    # RU_ID,
    # RU_STREAMS,
    RU_DESCRIPTOR,
    EMULATOR_MODE=False,
    DATA_RATE_SLOWDOWN_FACTOR=1,
    DEFAULT_DATA_FILE="./frames.bin",
    DATA_FILES={},
    # FLX_INPUT=False,
    # ETH_MODE=False,
    USE_FAKE_CARDS=True,
    CLOCK_SPEED_HZ=50000000,
    RAW_RECORDING_ENABLED=False,
    RAW_RECORDING_OUTPUT_DIR=".",
    CHANNEL_MASK_TPG: list = [],
    THRESHOLD_TPG=120,
    ALGORITHM_TPG="SWTPG",
    TPG_ENABLED=False,                                        
    TPG_CHANNEL_MAP= "ProtoDUNESP1ChannelMap",
    # USE_FAKE_DATA_PRODUCERS=False,
    DATA_REQUEST_TIMEOUT=1000,
    FRAGMENT_SEND_TIMEOUT=10,
    # HOST="localhost",
    SOURCEID_BROKER : SourceIDBroker = None,
    READOUT_SENDS_TP_FRAGMENTS=False,
    # ENABLE_DPDK_READER=False,
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
    
    FRONTEND_TYPE, QUEUE_FRAGMENT_TYPE, _ = compute_data_types(RU_DESCRIPTOR.det_id, CLOCK_SPEED_HZ, RU_DESCRIPTOR.tech)
    
    # TPG is automatically disabled for non wib2 frontends
    TPG_ENABLED = TPG_ENABLED and (FRONTEND_TYPE=='wib2')
    
    modules = []
    queues = []


    # Create the card readers
    cr_mods = []
    cr_queues = []


    if USE_FAKE_CARDS:
        fakecr_mods, fakecr_queues = create_fake_cardreader(
            FRONTEND_TYPE=FRONTEND_TYPE,
            QUEUE_FRAGMENT_TYPE=QUEUE_FRAGMENT_TYPE,
            DATA_RATE_SLOWDOWN_FACTOR=DATA_RATE_SLOWDOWN_FACTOR,
            DATA_FILES=DATA_FILES,
            DEFAULT_DATA_FILE=DEFAULT_DATA_FILE,
            CLOCK_SPEED_HZ=CLOCK_SPEED_HZ,
            EMULATED_DATA_TIMES_START_WITH_NOW=EMULATED_DATA_TIMES_START_WITH_NOW,
            RU_DESCRIPTOR=RU_DESCRIPTOR
        )
        cr_mods += fakecr_mods
        cr_queues += fakecr_queues
    # Create the card readers
    else:
        if RU_DESCRIPTOR.tech == 'flx':
            flx_mods, flx_queues = create_felix_cardreader(
                FRONTEND_TYPE=FRONTEND_TYPE,
                QUEUE_FRAGMENT_TYPE=QUEUE_FRAGMENT_TYPE,
                CARD_ID_OVERRIDE=CARD_ID_OVERRIDE,
                NUMA_ID=NUMA_ID,
                RU_DESCRIPTOR=RU_DESCRIPTOR
            )
            cr_mods += flx_mods
            cr_queues += flx_queues

        elif RU_DESCRIPTOR.tech == 'eth':
            dpdk_mods, dpdk_queues = create_dpdk_cardreader(
                FRONTEND_TYPE=FRONTEND_TYPE,
                QUEUE_FRAGMENT_TYPE=QUEUE_FRAGMENT_TYPE,
                # BASE_SOURCE_IP=BASE_SOURCE_IP,
                # DESTINATION_IP=DESTINATION_IP,
                EAL_ARGS=EAL_ARGS,
                RU_DESCRIPTOR=RU_DESCRIPTOR
            )
            cr_mods += dpdk_mods
            cr_queues += dpdk_queues

    modules += cr_mods
    queues += cr_queues

    # Create the data-link handlers
    dlhs_mods, _ = create_det_dhl(
        LATENCY_BUFFER_SIZE=LATENCY_BUFFER_SIZE,
        LATENCY_BUFFER_NUMA_AWARE=LATENCY_BUFFER_NUMA_AWARE,
        LATENCY_BUFFER_ALLOCATION_MODE=LATENCY_BUFFER_ALLOCATION_MODE,
        NUMA_ID=NUMA_ID,
        SEND_PARTIAL_FRAGMENTS=False,
        RAW_RECORDING_OUTPUT_DIR=RAW_RECORDING_OUTPUT_DIR,
        DATA_REQUEST_TIMEOUT=DATA_REQUEST_TIMEOUT,
        FRAGMENT_SEND_TIMEOUT=FRAGMENT_SEND_TIMEOUT,
        RAW_RECORDING_ENABLED=RAW_RECORDING_ENABLED,
        RU_DESCRIPTOR=RU_DESCRIPTOR

    )

    # Configure the TP processing if requrested
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

    # Add the TP datalink handlers
    if TPG_ENABLED and READOUT_SENDS_TP_FRAGMENTS:
        tpg_mods, tpg_queues = create_tp_dlhs(
            dro_dlh_list=dlhs_mods,
            LATENCY_BUFFER_SIZE=LATENCY_BUFFER_SIZE,
            DATA_REQUEST_TIMEOUT=DATA_REQUEST_TIMEOUT,
            FRAGMENT_SEND_TIMEOUT=FRAGMENT_SEND_TIMEOUT
        )
        modules += tpg_mods
        queues += tpg_queues

    # Create the Module graphs
    mgraph = ModuleGraph(modules, queues=queues)

    # Add endpoints and frame producers to DRO data handlers
    add_dro_eps_and_fps(
        mgraph=mgraph,
        dro_dlh_list=dlhs_mods,
        RUIDX=RU_DESCRIPTOR.label
    )

    if TPG_ENABLED and READOUT_SENDS_TP_FRAGMENTS:
       # Add endpoints and frame producers to TP data handlers
        add_tpg_eps_and_fps(
            mgraph=mgraph,
            # dro_dlh_list=dlhs_mods,
            tpg_dlh_list=tpg_mods,
            RUIDX=RU_DESCRIPTOR.label
        )

    # Create the application
    readout_app = App(mgraph, host=RU_DESCRIPTOR.host_name)

    # All done
    return readout_app

