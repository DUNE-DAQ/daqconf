# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes

moo.otypes.load_types('trigger/triggeractivitymaker.jsonnet')
moo.otypes.load_types('trigger/triggercandidatemaker.jsonnet')
moo.otypes.load_types('trigger/triggerzipper.jsonnet')
moo.otypes.load_types('trigger/moduleleveltrigger.jsonnet')
moo.otypes.load_types('trigger/timingtriggercandidatemaker.jsonnet')
moo.otypes.load_types('trigger/tpsetbuffercreator.jsonnet')
moo.otypes.load_types('trigger/faketpcreatorheartbeatmaker.jsonnet')
moo.otypes.load_types('trigger/txbuffer.jsonnet')
moo.otypes.load_types('readoutlibs/readoutconfig.jsonnet')
moo.otypes.load_types('trigger/tpchannelfilter.jsonnet')

# Import new types
import dunedaq.trigger.triggeractivitymaker as tam
import dunedaq.trigger.triggercandidatemaker as tcm
import dunedaq.trigger.triggerzipper as tzip
import dunedaq.trigger.moduleleveltrigger as mlt
import dunedaq.trigger.timingtriggercandidatemaker as ttcm
import dunedaq.trigger.tpsetbuffercreator as buf
import dunedaq.trigger.faketpcreatorheartbeatmaker as heartbeater
import dunedaq.trigger.txbufferconfig as bufferconf
import dunedaq.readoutlibs.readoutconfig as readoutconf
import dunedaq.trigger.tpchannelfilter as chfilter

from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Direction, Queue

TA_ELEMENT_ID = 10_000
TC_ELEMENT_ID = 100_000

#FIXME maybe one day, triggeralgs will define schemas... for now allow a dictionary of 4byte int, 4byte floats, and strings
moo.otypes.make_type(schema='number', dtype='i4', name='temp_integer', path='temptypes')
moo.otypes.make_type(schema='number', dtype='f4', name='temp_float', path='temptypes')
moo.otypes.make_type(schema='string', name='temp_string', path='temptypes')
moo.otypes.make_type(schema='boolean', name='temp_boolean', path='temptypes')
def make_moo_record(conf_dict,name,path='temptypes'):
    fields = []
    for pname,pvalue in conf_dict.items():
        typename = None
        if type(pvalue) == int:
            typename = 'temptypes.temp_integer'
        elif type(pvalue) == float:
            typename = 'temptypes.temp_float'
        elif type(pvalue) == str:
            typename = 'temptypes.temp_string'
        elif type(pvalue) == bool:
            typename = 'temptypes.temp_boolean'
        else:
            raise Exception(f'Invalid config argument type: {type(pvalue)}')
        fields.append(dict(name=pname,item=typename))
    moo.otypes.make_type(schema='record', fields=fields, name=name, path=path)

def get_tp_links(ru_config, FIRMWARE_TPG_ENABLED):
    if FIRMWARE_TPG_ENABLED:
        tp_links = []
        slr0_found = False
        slr1_found = False
        for ru_link in ru_config.links:
            if ru_link.dro_slr == 0 and not slr0_found:
                tp_links.append(ru_link)
                slr0_found = True
            if ru_link.dro_slr == 1 and not slr1_found:
                tp_links.append(ru_link)
                slr1_found = True
    else:
        tp_links = ru_config.links
    return tp_links

#===============================================================================
def get_trigger_app(SOFTWARE_TPG_ENABLED: bool = False,
                    FIRMWARE_TPG_ENABLED: bool = False,
                    CLOCK_SPEED_HZ: int = 50_000_000,
                    DATA_RATE_SLOWDOWN_FACTOR: float = 1,
                    DRO_CONFIG: list = [],

                    ACTIVITY_PLUGIN: str = 'TriggerActivityMakerPrescalePlugin',
                    ACTIVITY_CONFIG: dict = dict(prescale=10000),

                    CANDIDATE_PLUGIN: str = 'TriggerCandidateMakerPrescalePlugin',
                    CANDIDATE_CONFIG: int = dict(prescale=10),

                    USE_HSI_INPUT = True,
                    TTCM_S1: int = 1,
                    TTCM_S2: int = 2,
                    TRIGGER_WINDOW_BEFORE_TICKS: int = 1000,
                    TRIGGER_WINDOW_AFTER_TICKS: int = 1000,
                    HSI_TRIGGER_TYPE_PASSTHROUGH: bool = False,

		    MLT_BUFFER_TIMEOUT: int = 100,
                    MLT_SEND_TIMED_OUT_TDS: bool = False,
                    MLT_MAX_TD_LENGTH_MS: int = 1000,

                    USE_CHANNEL_FILTER: bool = True,

                    CHANNEL_MAP_NAME = "ProtoDUNESP1ChannelMap",
                    DATA_REQUEST_TIMEOUT = 1000,
                    HOST="localhost",
                    DEBUG=False):
    
    # Generate schema for the maker plugins on the fly in the temptypes module
    make_moo_record(ACTIVITY_CONFIG , 'ActivityConf' , 'temptypes')
    make_moo_record(CANDIDATE_CONFIG, 'CandidateConf', 'temptypes')
    import temptypes

    # How many clock ticks are there in a _wall clock_ second?
    ticks_per_wall_clock_s = CLOCK_SPEED_HZ / DATA_RATE_SLOWDOWN_FACTOR
    
    max_td_length_ticks = MLT_MAX_TD_LENGTH_MS * CLOCK_SPEED_HZ / 1000
    
    modules = []

    tpset_dros = []
    region_ids = {}
    for dro_info in DRO_CONFIG:
        if DEBUG: print(f"Checking dro on host {dro_info.host} with {len(dro_info.links)} links, of type {dro_info.links[0].det_id} (kHD_TPC is 3)")
        if dro_info.links[0].det_id == 3:
            if DEBUG: print(f"DRO on host {dro_info.host} is a HD_TPC readout, creating TP readout for region_id {dro_info.links[0].det_crate}")
            tpset_dros.append(dro_info)
            # Assumption is that each DRO app has the same APA
            if dro_info.links[0].det_crate not in region_ids:
                region_ids[dro_info.links[0].det_crate] = 0
            region_ids[dro_info.links[0].det_crate] += len(dro_info.links)

    # We always have a TC buffer even when there are no TPs, because we want to put the timing TC in the output file
    modules += [DAQModule(name = 'tc_buf',
                         plugin = 'TCBuffer',
                         conf = bufferconf.Conf(latencybufferconf = readoutconf.LatencyBufferConf(latency_buffer_size = 100_000,
                                                                                                  source_id = TA_ELEMENT_ID),
                                                requesthandlerconf = readoutconf.RequestHandlerConf(latency_buffer_size = 100_000,
                                                                                                    pop_limit_pct = 0.8,
                                                                                                    pop_size_pct = 0.1,
                                                                                                    source_id = TC_ELEMENT_ID,
                                                                                                    # output_file = f"output_{idx + MIN_LINK}.out",
                                                                                                    stream_buffer_size = 8388608,
                                                                                                    request_timeout_ms = DATA_REQUEST_TIMEOUT,
                                                                                                    warn_on_timeout = False,
                                                                                                    enable_raw_recording = False)))]
    if USE_HSI_INPUT:
        modules += [DAQModule(name = 'tctee_ttcm',
                         plugin = 'TCTee')]

    
    if SOFTWARE_TPG_ENABLED or FIRMWARE_TPG_ENABLED:
        config_tcm =  tcm.Conf(candidate_maker=CANDIDATE_PLUGIN,
                               candidate_maker_config=temptypes.CandidateConf(**CANDIDATE_CONFIG))

        # (PAR 2022-06-09) The max_latency_ms here should be kept
        # larger than the corresponding value in the upstream
        # TPZippers. See comment below for more details
        modules += [DAQModule(name = 'tazipper',
                              plugin = 'TAZipper',
                              conf = tzip.ConfParams(cardinality=len(tpset_dros),
                                                     max_latency_ms=1000,
                                                     element_id=TC_ELEMENT_ID)),
                    DAQModule(name = 'tcm',
                              plugin = 'TriggerCandidateMaker',
                              conf = config_tcm),

                    DAQModule(name = 'tctee_chain',
                              plugin = 'TCTee'),
                    ]

        # Make one heartbeatmaker per link
        for ruidx, ru_config in enumerate(tpset_dros):
            tp_links = get_tp_links(ru_config, FIRMWARE_TPG_ENABLED)

            region_id = ru_config.links[0].det_crate

            for link_conf in tp_links:
                link_id = f'ru{ruidx}_link{link_conf.dro_source_id}'
                if USE_CHANNEL_FILTER:
                    modules += [DAQModule(name = f'channelfilter_{link_id}',
                                      plugin = 'TPChannelFilter',
                                      conf = chfilter.Conf(channel_map_name=CHANNEL_MAP_NAME,
                                                           keep_collection=True,
                                                           keep_induction=False))]
                modules += [DAQModule(name = f'tpsettee_{link_id}',
                                      plugin = 'TPSetTee'),
                            DAQModule(name = f'heartbeatmaker_{link_id}',
                                      plugin = 'FakeTPCreatorHeartbeatMaker',
                                      conf = heartbeater.Conf(heartbeat_interval=ticks_per_wall_clock_s//100))]
                    
                # 1 buffer per TPG channel
                modules += [DAQModule(name = f'buf_{link_id}',
                                      plugin = 'TPBuffer',
                                      conf = bufferconf.Conf(latencybufferconf = readoutconf.LatencyBufferConf(latency_buffer_size = 1_000_000,
                                                                                                                source_id = link_conf.dro_source_id),
                                                             requesthandlerconf = readoutconf.RequestHandlerConf(latency_buffer_size = 1_000_000,
                                                                                                                  pop_limit_pct = 0.8,
                                                                                                                  pop_size_pct = 0.1,
                                                                                                                  source_id = link_conf.dro_source_id,
                                                                                                                  # output_file = f"output_{idx + MIN_LINK}.out",
                                                                                                                  stream_buffer_size = 8388608,
                                                                                                                  request_timeout_ms = DATA_REQUEST_TIMEOUT,
                                                                                                                  enable_raw_recording = False)))]

        for region_id, cardinality in region_ids.items():
                # (PAR 2022-06-09) The max_latency_ms here should be
                # kept smaller than the corresponding value in the
                # downstream TAZipper. The reason is to avoid tardy
                # sets at run stop, which are caused as follows:
                #
                # 1. The TPZipper receives its last input TPSets from
                # multiple links. In general, the last time received
                # from each link will be different (because the
                # upstream readout senders don't all stop
                # simultaneously). So there will be sets on one link
                # that don't have time-matched sets on the other
                # links. TPZipper sends these unmatched sets out after
                # TPZipper's max_latency_ms milliseconds have passed,
                # so these sets are delayed by
                # "tpzipper.max_latency_ms"
                #
                # 2. Meanwhile, the TAZipper has also stopped
                # receiving data from all but one of the readout units
                # (which are stopped sequentially), and so is in a
                # similar situation. Once tazipper.max_latency_ms has
                # passed, it sends out the sets from the remaining
                # live input, and "catches up" with the current time
                #
                # So, if tpzipper.max_latency_ms >
                # tazipper.max_latency_ms, the TA inputs made from the
                # delayed TPSets will certainly arrive at the TAZipper
                # after it has caught up to the current time, and be
                # tardy. If the tpzipper.max_latency_ms ==
                # tazipper.max_latency_ms, then depending on scheduler
                # delays etc, the delayed TPSets's TAs _may_ arrive at
                # the TAZipper tardily. With tpzipper.max_latency_ms <
                # tazipper.max_latency_ms, everything should be fine.
                modules += [DAQModule(name = f'zip_{region_id}',
                                      plugin = 'TPZipper',
                                              conf = tzip.ConfParams(cardinality=cardinality,
                                                                     max_latency_ms=100,
                                                                     element_id=TA_ELEMENT_ID)),
                                    
                            DAQModule(name = f'tam_{region_id}',
                                      plugin = 'TriggerActivityMaker',
                                      conf = tam.Conf(activity_maker=ACTIVITY_PLUGIN,
                                                      geoid_element=region_id,  # 2022-02-02 PL: Same comment as above
                                                      window_time=10000,  # should match whatever makes TPSets, in principle
                                                      buffer_time=10*ticks_per_wall_clock_s//1000, # 10 wall-clock ms
                                                      activity_maker_config=temptypes.ActivityConf(**ACTIVITY_CONFIG))),

                            DAQModule(name = f'tasettee_region_{region_id}',
                                      plugin = "TASetTee"),
                            
                            DAQModule(name = f'ta_buf_region_{region_id}',
                                      plugin = 'TABuffer',
                                      # PAR 2022-04-20 Not sure what to set the element id to so it doesn't collide with the region/element used by TP buffers. Make it some big number that shouldn't already be used by the TP buffer
                                      conf = bufferconf.Conf(latencybufferconf = readoutconf.LatencyBufferConf(latency_buffer_size = 100_000,
                                                                                                               source_id = TA_ELEMENT_ID),
                                                             requesthandlerconf = readoutconf.RequestHandlerConf(latency_buffer_size = 100_000,
                                                                                                                 pop_limit_pct = 0.8,
                                                                                                                 pop_size_pct = 0.1,
                                                                                                                 source_id = TA_ELEMENT_ID,
                                                                                                                 # output_file = f"output_{idx + MIN_LINK}.out",
                                                                                                                 stream_buffer_size = 8388608,
                                                                                                                 request_timeout_ms = DATA_REQUEST_TIMEOUT,
                                                                                                                 enable_raw_recording = False)))]

        
    if USE_HSI_INPUT:
        modules += [DAQModule(name = 'ttcm',
                          plugin = 'TimingTriggerCandidateMaker',
                          conf=ttcm.Conf(s0=ttcm.map_t(signal_type=0,
                                                       time_before=TRIGGER_WINDOW_BEFORE_TICKS,
                                                       time_after=TRIGGER_WINDOW_AFTER_TICKS),
                                         s1=ttcm.map_t(signal_type=TTCM_S1,
                                                       time_before=TRIGGER_WINDOW_BEFORE_TICKS,
                                                       time_after=TRIGGER_WINDOW_AFTER_TICKS),
                                         s2=ttcm.map_t(signal_type=TTCM_S2,
                                                       time_before=TRIGGER_WINDOW_BEFORE_TICKS,
                                                       time_after=TRIGGER_WINDOW_AFTER_TICKS),
                                         hsievent_connection_name = "hsievents",
					 hsi_trigger_type_passthrough=HSI_TRIGGER_TYPE_PASSTHROUGH))]
    
    # We need to populate the list of links based on the fragment
    # producers available in the system. This is a bit of a
    # chicken-and-egg problem, because the trigger app itself creates
    # fragment producers (see below). Eventually when the MLT is its
    # own process, this problem will probably go away, but for now, we
    # leave the list of links here blank, and replace it in
    # util.connect_fragment_producers
    modules += [DAQModule(name = 'mlt',
                          plugin = 'ModuleLevelTrigger',
                          conf=mlt.ConfParams(links=[],  # To be updated later - see comment above
                                              dfo_connection=f"td_to_dfo",
                                              dfo_busy_connection=f"df_busy_signal",
                                              hsi_trigger_type_passthrough=HSI_TRIGGER_TYPE_PASSTHROUGH,
					      buffer_timeout=MLT_BUFFER_TIMEOUT,
                                              td_out_of_timeout=MLT_SEND_TIMED_OUT_TDS,
                                              td_readout_limit=max_td_length_ticks))]

    mgraph = ModuleGraph(modules)

    if USE_HSI_INPUT:
        mgraph.connect_modules("ttcm.output",         "tctee_ttcm.input",             "ttcm_input", size_hint=1000)
        mgraph.connect_modules("tctee_ttcm.output1",  "mlt.trigger_candidate_source", "tcs_to_mlt", size_hint=1000)
        mgraph.connect_modules("tctee_ttcm.output2",  "tc_buf.tc_source",             "tcs_to_buf", size_hint=1000)

    if SOFTWARE_TPG_ENABLED or FIRMWARE_TPG_ENABLED:
        mgraph.connect_modules("tazipper.output", "tcm.input", size_hint=1000)
        for ruidx, ru_config in enumerate(tpset_dros):
            
            tp_links = get_tp_links(ru_config, FIRMWARE_TPG_ENABLED)
            for link_conf in tp_links:
                    link_id = f'ru{ruidx}_link{link_conf.dro_source_id}'

                    if USE_CHANNEL_FILTER:
                        mgraph.connect_modules(f'channelfilter_{link_id}.tpset_sink', f'tpsettee_{link_id}.input', size_hint=1000)

                    mgraph.connect_modules(f'tpsettee_{link_id}.output1', f'heartbeatmaker_{link_id}.tpset_source', size_hint=1000)
                    mgraph.connect_modules(f'tpsettee_{link_id}.output2', f'buf_{link_id}.tpset_source', size_hint=1000)

                    mgraph.connect_modules(f'heartbeatmaker_{link_id}.tpset_sink', f"zip_{ru_config.links[0].det_crate}.input", f"{ru_config.links[0].det_crate}_tpset_q", size_hint=1000)

        for region_id in region_ids:
            mgraph.connect_modules(f'zip_{region_id}.output', f'tam_{region_id}.input', size_hint=1000)
        # Use connect_modules to connect up the Tees to the buffers/MLT,
        # as manually adding Queues doesn't give the desired behaviour
        mgraph.connect_modules("tcm.output",          "tctee_chain.input",            "chain_input", size_hint=1000)
        mgraph.connect_modules("tctee_chain.output1", "mlt.trigger_candidate_source", "tcs_to_mlt",  size_hint=1000)
        mgraph.connect_modules("tctee_chain.output2", "tc_buf.tc_source",             "tcs_to_buf",  size_hint=1000)


        for region_id in region_ids:
            mgraph.connect_modules(f'tam_{region_id}.output',              f'tasettee_region_{region_id}.input',      size_hint=1000)
            mgraph.connect_modules(f'tasettee_region_{region_id}.output1', f'tazipper.input', "tas_to_tazipper",      size_hint=1000)
            mgraph.connect_modules(f'tasettee_region_{region_id}.output2', f'ta_buf_region_{region_id}.taset_source', size_hint=1000)
    
    if USE_HSI_INPUT:
        mgraph.add_endpoint("hsievents", None, Direction.IN)
        
    mgraph.add_endpoint("td_to_dfo", None, Direction.OUT, toposort=True)
    mgraph.add_endpoint("df_busy_signal", None, Direction.IN)

    mgraph.add_fragment_producer(id=TC_ELEMENT_ID, subsystem="Trigger",
                                 requests_in="tc_buf.data_request_source",
                                 fragments_out="tc_buf.fragment_sink")

    if SOFTWARE_TPG_ENABLED or FIRMWARE_TPG_ENABLED:
        for ruidx, ru_config in enumerate(tpset_dros):
            
            tp_links = get_tp_links(ru_config, FIRMWARE_TPG_ENABLED)

            for link_conf in tp_links:
                # 1 buffer per link
                link_id1=f"ru{link_conf.dro_host}_{ruidx}_link{link_conf.dro_source_id}"
                link_id2=f"ru{ruidx}_link{link_conf.dro_source_id}"
                buf_name=f'buf_{link_id2}'

                if USE_CHANNEL_FILTER:
                    mgraph.add_endpoint(f"tpsets_{link_id1}_sub", f"channelfilter_{link_id2}.tpset_source", Direction.IN, topic=["TPSets"])
                else:
                    mgraph.add_endpoint(f"tpsets_{link_id1}_sub", f'tpsettee_{link_id2}.input',             Direction.IN, topic=["TPSets"])
                    

                mgraph.add_fragment_producer(id=link_conf.dro_source_id, subsystem="Trigger",
                                             requests_in=f"{buf_name}.data_request_source",
                                             fragments_out=f"{buf_name}.fragment_sink")
        for region_id in region_ids:
            buf_name = f'ta_buf_region_{region_id}'
            mgraph.add_fragment_producer(id=TA_ELEMENT_ID*region_id, subsystem="Trigger",
                                         requests_in=f"{buf_name}.data_request_source",
                                         fragments_out=f"{buf_name}.fragment_sink")


    trigger_app = App(modulegraph=mgraph, host=HOST, name='TriggerApp')
    
    if DEBUG:
        trigger_app.export("trigger_app.dot")

    return trigger_app

