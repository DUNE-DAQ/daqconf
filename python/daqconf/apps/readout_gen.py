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
moo.otypes.load_types('readoutlibs/sourceemulatorconfig.jsonnet')
moo.otypes.load_types('readoutlibs/readoutconfig.jsonnet')
moo.otypes.load_types('lbrulibs/pacmancardreader.jsonnet')
moo.otypes.load_types('dfmodules/fakedataprod.jsonnet')
moo.otypes.load_types('networkmanager/nwmgr.jsonnet')

# Import new types
import dunedaq.cmdlib.cmd as basecmd # AddressedCmd,
import dunedaq.rcif.cmd as rccmd # AddressedCmd,
import dunedaq.appfwk.cmd as cmd # AddressedCmd,
import dunedaq.appfwk.app as app # AddressedCmd,
import dunedaq.readoutlibs.sourceemulatorconfig as sec
import dunedaq.flxlibs.felixcardreader as flxcr
import dunedaq.readoutlibs.readoutconfig as rconf
import dunedaq.lbrulibs.pacmancardreader as pcr
# import dunedaq.dfmodules.triggerrecordbuilder as trb
import dunedaq.dfmodules.fakedataprod as fdp
import dunedaq.networkmanager.nwmgr as nwmgr

from appfwk.utils import acmd, mcmd, mrccmd, mspec
from os import path

import json
from daqconf.core.conf_utils import Direction, Queue
from daqconf.core.daqmodule import DAQModule
from daqconf.core.app import App,ModuleGraph

# Time to wait on pop()
QUEUE_POP_WAIT_MS = 100
# local clock speed Hz
# CLOCK_SPEED_HZ = 50000000;

def get_readout_app(RU_CONFIG=[],
                    EMULATOR_MODE=False,
                    DATA_RATE_SLOWDOWN_FACTOR=1,
                    RUN_NUMBER=333, 
                    DATA_FILE="./frames.bin",
                    FLX_INPUT=False,
                    SSP_INPUT=True,
                    CLOCK_SPEED_HZ=50000000,
                    RUIDX=0,
                    RAW_RECORDING_ENABLED=False,
                    RAW_RECORDING_OUTPUT_DIR=".",
                    FRONTEND_TYPE='wib',
                    SYSTEM_TYPE='TPC',
                    SOFTWARE_TPG_ENABLED=False,
                    FIRMWARE_TPG_ENABLED=False,
                    TPG_CHANNEL_MAP= "ProtoDUNESP1ChannelMap",
                    USE_FAKE_DATA_PRODUCERS=False,
                    LATENCY_BUFFER_SIZE=499968,
                    HOST="localhost",
                    DEBUG=False):
    """Generate the json configuration for the readout and DF process"""
    NUMBER_OF_DATA_PRODUCERS = len(RU_CONFIG)
    cmd_data = {}
    
    required_eps = {f'timesync_{RUIDX}'}
    # if not required_eps.issubset([nw.name for nw in NW_SPECS]):
    #     raise RuntimeError(f"ERROR: not all the required endpoints ({', '.join(required_eps)}) found in list of endpoints {' '.join([nw.name for nw in NW_SPECS])}")
    
    RATE_KHZ = CLOCK_SPEED_HZ / (25 * 12 * DATA_RATE_SLOWDOWN_FACTOR * 1000)
    
    MIN_LINK = RU_CONFIG[RUIDX]["start_channel"]
    MAX_LINK = MIN_LINK + RU_CONFIG[RUIDX]["channel_count"]
    
    if DEBUG: print(f"ReadoutApp.__init__ with RUIDX={RUIDX}, MIN_LINK={MIN_LINK}, MAX_LINK={MAX_LINK}")

    modules = []
    queues = []

    total_link_count = 0
    for ru in range(len(RU_CONFIG)):
        if RU_CONFIG[ru]['region_id'] == RU_CONFIG[RUIDX]['region_id']:
            total_link_count += RU_CONFIG[ru]["channel_count"]

    if SOFTWARE_TPG_ENABLED:
        for idx in range(MIN_LINK, MAX_LINK):
            if idx > 4:
                link_num = idx + 1
            else:
                link_num = idx
            modules += [DAQModule(name = f"tp_datahandler_{link_num}",
                               plugin = "DataLinkHandler",
                               conf = rconf.Conf(readoutmodelconf = rconf.ReadoutModelConf(source_queue_timeout_ms = QUEUE_POP_WAIT_MS,
                                                                                         region_id = RU_CONFIG[RUIDX]["region_id"],
                                                                                         element_id = total_link_count+idx),
                                                 latencybufferconf = rconf.LatencyBufferConf(latency_buffer_size = LATENCY_BUFFER_SIZE,
                                                                                            region_id = RU_CONFIG[RUIDX]["region_id"],
                                                                                            element_id = total_link_count + link_num),
                                                 rawdataprocessorconf = rconf.RawDataProcessorConf(region_id = RU_CONFIG[RUIDX]["region_id"],
                                                                                                   element_id = total_link_count + link_num,
                                                                                                   enable_software_tpg = False,
                                                                                                   channel_map_name=TPG_CHANNEL_MAP),
                                                 requesthandlerconf= rconf.RequestHandlerConf(latency_buffer_size = LATENCY_BUFFER_SIZE,
                                                                                              pop_limit_pct = 0.8,
                                                                                              pop_size_pct = 0.1,
                                                                                              region_id = RU_CONFIG[RUIDX]["region_id"],
                                                                                              element_id =total_link_count + link_num,
                                                                                              # output_file = f"output_{idx + MIN_LINK}.out",
                                                                                              stream_buffer_size = 100 if FRONTEND_TYPE=='pacman' else 8388608,
                                                                                              enable_raw_recording = False)))]
    if FIRMWARE_TPG_ENABLED:
        if RU_CONFIG[RUIDX]["channel_count"] > 5:
            tp_links = 2
        else:
            tp_links = 1
        for idx in range(tp_links):
            if FIRMWARE_TPG_ENABLED:
                queues += [Queue(f"tp_datahandler_{idx}.errored_frames", 'errored_frame_consumer.input_queue', "errored_frames_q")]
                queues += [Queue(f"tp_datahandler_{idx}.tp_out",f"tp_datahandler_{idx}.raw_input",f"raw_tp_link_{((idx+1)*5)+idx}",100000 )]
            modules += [DAQModule(name = f"tp_datahandler_{idx}",
                                  plugin = "DataLinkHandler", 
                                  conf = rconf.Conf(
                                      readoutmodelconf= rconf.ReadoutModelConf(
                                          source_queue_timeout_ms= QUEUE_POP_WAIT_MS,
                                          # fake_trigger_flag=0, # default
                                          region_id = RU_CONFIG[RUIDX]["region_id"],
                                          element_id = idx,
                                          timesync_connection_name = f"timesync_{RUIDX}",
                                          timesync_topic_name = "Timesync",
                                      ),
                                      latencybufferconf= rconf.LatencyBufferConf(
                                          latency_buffer_alignment_size = 4096,
                                          latency_buffer_size = LATENCY_BUFFER_SIZE,
                                          region_id = RU_CONFIG[RUIDX]["region_id"],
                                          element_id = idx,
                                      ),
                                      rawdataprocessorconf= rconf.RawDataProcessorConf(
                                          region_id = RU_CONFIG[RUIDX]["region_id"],
                                          element_id = idx,
                                          enable_software_tpg = False,
                                          enable_firmware_tpg = True,
                                          channel_map_name = TPG_CHANNEL_MAP,
                                          emulator_mode = EMULATOR_MODE,
                                          error_counter_threshold=100,
                                          error_reset_freq=10000,
                                          tpset_topic=RU_CONFIG[RUIDX]["tpset_topics"][idx]
                                      ),
                                      requesthandlerconf= rconf.RequestHandlerConf(
                                          latency_buffer_size = LATENCY_BUFFER_SIZE,
                                          pop_limit_pct = 0.8,
                                          pop_size_pct = 0.1,
                                          region_id = RU_CONFIG[RUIDX]["region_id"],
                                          element_id = idx,
                                          output_file = path.join(RAW_RECORDING_OUTPUT_DIR, f"output_tp_{RUIDX}_{idx}.out"),
                                          stream_buffer_size = 8388608,
                                          enable_raw_recording = RAW_RECORDING_ENABLED,
                                      )))]


    if FRONTEND_TYPE == 'wib' and not USE_FAKE_DATA_PRODUCERS:
        modules += [DAQModule(name = "errored_frame_consumer",
                           plugin = "ErroredFrameConsumer")]

    # There are two flags to be checked so I think a for loop
    # is the closest way to the blocks that are being used here
    
    for idx in range(MIN_LINK,MAX_LINK):
        if idx > 4:
            link_num = idx + 1
        else:
            link_num = idx
        if USE_FAKE_DATA_PRODUCERS:
            modules += [DAQModule(name = f"fakedataprod_{link_num}",
                                  plugin='FakeDataProd',
                                  conf = fdp.ConfParams(
                                  system_type = SYSTEM_TYPE,
                                  apa_number = RU_CONFIG[RUIDX]["region_id"],
                                  link_number = link_num,
                                  time_tick_diff = 25,
                                  frame_size = 464,
                                  response_delay = 0,
                                  fragment_type = "FakeData",
                                  timesync_topic_name = "Timesync",
                                  ))]
        else:
            if SOFTWARE_TPG_ENABLED:
                queues += [Queue(f"datahandler_{link_num}.tp_out",f"tp_datahandler_{link_num}.raw_input",f"sw_tp_link_{link_num}",100000 )]                
                
            if FRONTEND_TYPE == 'wib':
                queues += [Queue(f"datahandler_{link_num}.errored_frames", 'errored_frame_consumer.input_queue', "errored_frames_q")]

            if SOFTWARE_TPG_ENABLED: 
                tpset_topic = RU_CONFIG[RUIDX]["tpset_topics"][idx]
            else:
                tpset_topic = "None"
            modules += [DAQModule(name = f"datahandler_{link_num}",
                                  plugin = "DataLinkHandler", 
                                  conf = rconf.Conf(
                                      readoutmodelconf= rconf.ReadoutModelConf(
                                          source_queue_timeout_ms= QUEUE_POP_WAIT_MS,
                                          # fake_trigger_flag=0, # default
                                          region_id = RU_CONFIG[RUIDX]["region_id"],
                                          element_id = link_num,
                                          timesync_connection_name = f"timesync_{RUIDX}",
                                          timesync_topic_name = "Timesync",
                                      ),
                                      latencybufferconf= rconf.LatencyBufferConf(
                                          latency_buffer_alignment_size = 4096,
                                          latency_buffer_size = LATENCY_BUFFER_SIZE,
                                          region_id = RU_CONFIG[RUIDX]["region_id"],
                                          element_id = link_num,
                                      ),
                                      rawdataprocessorconf= rconf.RawDataProcessorConf(
                                          region_id = RU_CONFIG[RUIDX]["region_id"],
                                          element_id = link_num,
                                          enable_software_tpg = SOFTWARE_TPG_ENABLED,
                                          channel_map_name = TPG_CHANNEL_MAP,
                                          emulator_mode = EMULATOR_MODE,
                                          error_counter_threshold=100,
                                          error_reset_freq=10000,
                                          tpset_topic=tpset_topic
                                      ),
                                      requesthandlerconf= rconf.RequestHandlerConf(
                                          latency_buffer_size = LATENCY_BUFFER_SIZE,
                                          pop_limit_pct = 0.8,
                                          pop_size_pct = 0.1,
                                          region_id = RU_CONFIG[RUIDX]["region_id"],
                                          element_id = link_num,
                                          output_file = path.join(RAW_RECORDING_OUTPUT_DIR, f"output_{RUIDX}_{link_num}.out"),
                                          stream_buffer_size = 8388608,
                                          enable_raw_recording = RAW_RECORDING_ENABLED,
                                      )))]

                    
    if not USE_FAKE_DATA_PRODUCERS:
        if FLX_INPUT:
            link_0 = [i for i in range(min(5, RU_CONFIG[RUIDX]["channel_count"]))]
            link_1 = [i-5 for i in range(5, max(5, RU_CONFIG[RUIDX]["channel_count"]))]
            if FIRMWARE_TPG_ENABLED:
                link_0.append(5)
                if RU_CONFIG[RUIDX]["channel_count"] > 5:
                    link_1.append(5)
            for idx in range(MIN_LINK, MIN_LINK + min(5, RU_CONFIG[RUIDX]["channel_count"])):
                queues += [Queue(f'flxcard_0.output_{idx}',f"datahandler_{idx}.raw_input",f'{FRONTEND_TYPE}_link_{idx}', 100000 )]
            if FIRMWARE_TPG_ENABLED:
                queues += [Queue(f'flxcard_0.output_5',f"tp_datahandler_0.raw_input",f'raw_tp_link_5', 100000 )]

            modules += [DAQModule(name = 'flxcard_0',
                               plugin = 'FelixCardReader',
                               conf = flxcr.Conf(card_id = RU_CONFIG[RUIDX]["card_id"],
                                                 logical_unit = 0,
                                                 dma_id = 0,
                                                 chunk_trailer_size = 32,
                                                 dma_block_size_kb = 4,
                                                 dma_memory_size_gb = 4,
                                                 numa_id = 0,
                                                 links_enabled = link_0))]
            
            if RU_CONFIG[RUIDX]["channel_count"] > 5 :
                for idx in range(MIN_LINK+6, MAX_LINK+1):
                    queues += [Queue(f'flxcard_1.output_{idx}',f"datahandler_{idx}.raw_input",f'{FRONTEND_TYPE}_link_{idx}', 100000 )]
                if FIRMWARE_TPG_ENABLED:
                    queues += [Queue(f'flxcard_1.output_11',f"tp_datahandler_1.raw_input",f'raw_tp_link_11', 100000 )]

                modules += [DAQModule(name = "flxcard_1",
                                   plugin = "FelixCardReader",
                                   conf = flxcr.Conf(card_id = RU_CONFIG[RUIDX]["card_id"],
                                                     logical_unit = 1,
                                                     dma_id = 0,
                                                     chunk_trailer_size = 32,
                                                     dma_block_size_kb = 4,
                                                     dma_memory_size_gb = 4,
                                                     numa_id = 0,
                                                     links_enabled = link_1))]
                
        elif SSP_INPUT:
            modules += [DAQModule(name = "ssp_0",
                               plugin = "SSPCardReader",
                               connections = {f'output_{idx}': Connection(f"datahandler_{idx}.raw_input",
                                                                          queue_name = f'{FRONTEND_TYPE}_link_{idx}',
                                                                          queue_kind = "FollySPSCQueue",
                                                                          queue_capacity = 100000)},
                               conf = flxcr.Conf(card_id = RU_CONFIG[RUIDX]["card_id"],
                                                 logical_unit = 0,
                                                 dma_id = 0,
                                                 chunk_trailer_size = 32,
                                                 dma_block_size_kb = 4,
                                                 dma_memory_size_gb = 4,
                                                 numa_id = 0,
                                                 links_enabled = [i for i in range(RU_CONFIG[RUIDX]["channel_count"])]))]
    
        else:
            fake_source = "fake_source"
            card_reader = "FakeCardReader"
            conf = sec.Conf(link_confs = [sec.LinkConfiguration(geoid=sec.GeoID(system=SYSTEM_TYPE,
                                                                                region=RU_CONFIG[RUIDX]["region_id"],
                                                                                element=idx),
                                                                slowdown=DATA_RATE_SLOWDOWN_FACTOR,
                                                                queue_name=f"output_{idx}",
                                                                data_filename = DATA_FILE,
                                                                emu_frame_error_rate=0) for idx in range(MIN_LINK,MAX_LINK)],
                            # input_limit=10485100, # default
                            queue_timeout_ms = QUEUE_POP_WAIT_MS)
            
            if FRONTEND_TYPE=='pacman':
                fake_source = "pacman_source"
                card_reader = "PacmanCardReader"
                conf = pcr.Conf(link_confs = [pcr.LinkConfiguration(geoid = pcr.GeoID(system = SYSTEM_TYPE,
                                                                                      region = RU_CONFIG[RUIDX]["region_id"],
                                                                                      element = idx))
                                              for idx in range(MIN_LINK,MAX_LINK)],
                                zmq_receiver_timeout = 10000)
            modules += [DAQModule(name = fake_source,
                               plugin = card_reader,
                               conf = conf)]
            queues += [Queue(f"{fake_source}.output_{idx}",f"datahandler_{idx}.raw_input",f'{FRONTEND_TYPE}_link_{idx}', 100000) for idx in range(MIN_LINK, MAX_LINK)]

    # modules += [
    #     DAQModule(name = "fragment_sender",
    #                    plugin = "FragmentSender",
    #                    conf = None)]
                        
    mgraph = ModuleGraph(modules, queues=queues)

    if FIRMWARE_TPG_ENABLED:
        if RU_CONFIG[RUIDX]["channel_count"] > 5:
            tp_links = 2
        else:
            tp_links = 1
        for idx in range(tp_links):
            assert total_link_count < 1000
            mgraph.add_endpoint(f"tpsets_ru{RUIDX}_link{idx}", f"tp_datahandler_{idx}.tpset_out",    Direction.OUT, topic=[RU_CONFIG[RUIDX]["tpset_topics"][idx]])
            mgraph.add_fragment_producer(region = RU_CONFIG[RUIDX]["region_id"], element = idx + 1000, system = SYSTEM_TYPE,
                                    requests_in   = f"tp_datahandler_{idx}.request_input",
                                    fragments_out = f"tp_datahandler_{idx}.fragment_queue")
            mgraph.add_endpoint(f"timesync_{idx}", f"tp_datahandler_{idx}.timesync_output",    Direction.OUT, ["Timesync"])

    for idx in range(MIN_LINK, MAX_LINK):
        if idx > 4:
            link_num = idx + 1
        else:
            link_num = idx
        if SOFTWARE_TPG_ENABLED:
            mgraph.add_endpoint(f"tpsets_ru{RUIDX}_link{idx}", f"datahandler_{link_num}.tpset_out",    Direction.OUT, topic=[RU_CONFIG[RUIDX]["tpset_topics"][idx]])
            mgraph.add_endpoint(f"timesync_tp_dlh_ru{RUIDX}_{idx}", f"tp_datahandler_{link_num}.timesync_output",    Direction.OUT, ["Timesync"])
        
        if USE_FAKE_DATA_PRODUCERS:
            # Add fragment producers for fake data. This call is necessary to create the RequestReceiver instance, but we don't need the generated FragmentSender or its queues...
            mgraph.add_fragment_producer(region = RU_CONFIG[RUIDX]["region_id"], element = idx, system = SYSTEM_TYPE,
                                         requests_in   = f"fakedataprod_{idx}.data_request_input_queue",
                                         fragments_out = f"fakedataprod_{idx}.fragment_queue")
            mgraph.add_endpoint(f"timesync_ru{RUIDX}_{idx}", f"fakedataprod_{idx}.timesync_output",    Direction.OUT, ["Timesync"], toposort=False)
        else:
            # Add fragment producers for raw data
            mgraph.add_fragment_producer(region = RU_CONFIG[RUIDX]["region_id"], element = link_num, system = SYSTEM_TYPE,
                                         requests_in   = f"datahandler_{link_num}.request_input",
                                         fragments_out = f"datahandler_{link_num}.fragment_queue")
            mgraph.add_endpoint(f"timesync_ru{RUIDX}_{idx}", f"datahandler_{link_num}.timesync_output",    Direction.OUT, ["Timesync"], toposort=False)

            # Add fragment producers for TPC TPs. Make sure the element index doesn't overlap with the ones for raw data
            #
            # NB We decided not to request TPs from readout for the
            # 2.10 release. It would be nice to achieve this by just
            # not adding fragment producers for the relevant links
            # here, but then the necessary input and output queues for
            # the DataLinkHandler modules are not created, so we can't
            # init. So instead we do it this roundabout way: the
            # fragment producers are all created, and then they are
            # eventually removed from the MLT's list of links to
            # request data from. That removal is done in
            # daqconf_multiru_gen, which relies on a convention that
            # TP links have element value > 1000.
            #
            # This situation should change after release 2.10, when
            # real firmware TPs become available
            if SOFTWARE_TPG_ENABLED:
                assert total_link_count < 1000
                mgraph.add_fragment_producer(region = RU_CONFIG[RUIDX]["region_id"], element = link_num + 1000, system = SYSTEM_TYPE,
                                             requests_in   = f"tp_datahandler_{link_num}.request_input",
                                             fragments_out = f"tp_datahandler_{link_num}.fragment_queue")

    readout_app = App(mgraph, host=HOST)
    if DEBUG:
        readout_app.export("readout_app.dot")

    return readout_app
