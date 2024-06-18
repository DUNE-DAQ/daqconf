# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

# Load configuration types
import moo.otypes

moo.otypes.load_types('trigger/triggeractivitymaker.jsonnet')
moo.otypes.load_types('trigger/triggercandidatemaker.jsonnet')
moo.otypes.load_types('trigger/customtriggercandidatemaker.jsonnet')
moo.otypes.load_types('trigger/randomtriggercandidatemaker.jsonnet')
moo.otypes.load_types('trigger/triggerzipper.jsonnet')
moo.otypes.load_types('trigger/moduleleveltrigger.jsonnet')
moo.otypes.load_types('trigger/timingtriggercandidatemaker.jsonnet')
moo.otypes.load_types('trigger/ctbtriggercandidatemaker.jsonnet')
moo.otypes.load_types('trigger/cibtriggercandidatemaker.jsonnet')
moo.otypes.load_types('trigger/faketpcreatorheartbeatmaker.jsonnet')
moo.otypes.load_types('trigger/txbuffer.jsonnet')
moo.otypes.load_types('readoutlibs/readoutconfig.jsonnet')
moo.otypes.load_types('trigger/tpchannelfilter.jsonnet')

# Import new types
import dunedaq.trigger.triggeractivitymaker as tam
import dunedaq.trigger.triggercandidatemaker as tcm
import dunedaq.trigger.customtriggercandidatemaker as ctcm
import dunedaq.trigger.randomtriggercandidatemaker as rtcm
import dunedaq.trigger.triggerzipper as tzip
import dunedaq.trigger.moduleleveltrigger as mlt
import dunedaq.trigger.timingtriggercandidatemaker as ttcm
import dunedaq.trigger.ctbtriggercandidatemaker as ctbtcm
import dunedaq.trigger.cibtriggercandidatemaker as cibtcm
import dunedaq.trigger.faketpcreatorheartbeatmaker as heartbeater
import dunedaq.trigger.txbufferconfig as bufferconf
import dunedaq.readoutlibs.readoutconfig as readoutconf
import dunedaq.trigger.tpchannelfilter as chfilter

from daqconf.core.app import App, ModuleGraph
from daqconf.core.daqmodule import DAQModule
from daqconf.core.conf_utils import Direction, Queue
from daqconf.core.sourceid import TAInfo, TPInfo, TCInfo

import trgdataformats

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

#===============================================================================
def get_buffer_conf(source_id, data_request_timeout):
    return bufferconf.Conf(latencybufferconf = readoutconf.LatencyBufferConf(latency_buffer_size = 10_000_000),
                           requesthandlerconf = readoutconf.RequestHandlerConf(latency_buffer_size = 10_000_000,
                                                                               pop_limit_pct = 0.8,
                                                                               pop_size_pct = 0.1,
                                                                               source_id = source_id,
                                                                               det_id = 1,
                                                                               # output_file = f"output_{idx + MIN_LINK}.out",
                                                                               stream_buffer_size = 8388608,
                                                                               request_timeout_ms = data_request_timeout,
                                                                               warn_on_timeout = False,
                                                                               enable_raw_recording = False))

#===============================================================================
### Function that converts trigger word strings to trigger word integers given TC type. Uses functions from trgdataformats.
def get_trigger_bitwords(bitwords):
    # create bitwords flags
    final_bit_flags = []
    for bitword in bitwords:
        tmp_bits = []
        for bit_name in bitword:
            bit_value = trgdataformats.string_to_fragment_type_value(bit_name)
            if bit_value == 0:
                raise RuntimeError(f'One (or more) of provided MLT trigger bitwords is unknown! Please recheck the names...')
            else:
                tmp_bits.append(bit_value)
        final_bit_flags.append(tmp_bits)
 
    return final_bit_flags

def check_mlt_roi_config(mlt_roi_conf, n_groups):
    prob = 0
    for group in mlt_roi_conf:
        prob += group["probability"]
        if group["number_of_link_groups"] > n_groups:
            raise RuntimeError(f'The MLT ROI configuration map is invalid, the number of requested link groups ({group["number_of_link_groups"]}) must be <= all link groups ({n_groups})')
    if prob > 1.0:
        raise RuntimeError(f'The MLT ROI configuration map is invalid, the sum of probabilites must be <= 1.0, your configured sum of probabilities: {prob}')
    return

#===============================================================================
### Function to check for the presence of TC sources.
def tc_source_present(use_hsi, use_fake_hsi, use_ctb, use_cib, use_ctcm, use_rtcm, n_tp_sources):
	return (use_hsi or use_fake_hsi or use_ctb or use_ctcm or use_cib or use_rtcm or n_tp_sources)


#===============================================================================
def update_ttcm_map(ttcm_map,
                    trigger_window_before_ticks,
                    trigger_window_after_ticks
    ):
    """
    Populates the readout window for TTCM hsi-TC map with the global values the
    supplied values are -1 (default if readout window not supplied in TTCM map)

    Args:
        ttcm_map (dict): The TTCM hsi-TC map as defined in the schema.
        trigger_window_before_ticks (int): N ticks to expand readout window before event
        trigger_window_after_ticks (int): N ticks to expand readout window after event

    Returns:
        dict: Updated TTCM hsi-TC map
    """
    for entry in ttcm_map:
        if entry['time_before'] == -1:
            entry['time_before'] = trigger_window_before_ticks
        if entry['time_after'] == -1:
            entry['time_after'] = trigger_window_after_ticks
    return ttcm_map

#===============================================================================
### Function to check whether hsi config is sensible
def check_hsi_config(USE_FAKE_HSI_INPUT, FAKE_HSI_CTB):
    if FAKE_HSI_CTB and not USE_FAKE_HSI_INPUT:
        raise RuntimeError(f'Fake CTB requires fake HSI. Configuration given: fake_hsi: {USE_FAKE_HSI_INPUT}, fake_ctb: {FAKE_HSI_CTB}')
    return

#===============================================================================
def get_trigger_app(
        trigger,
        detector,
        daq_common,
        tp_infos,
        trigger_data_request_timeout,
        use_hsi_input,
        use_fake_hsi_input,
        use_ctb_input,
        use_cib_input,
        fake_hsi_to_ctb,
        USE_CHANNEL_FILTER: bool = True,
        DEBUG=False
    ):

    # Temp variables, To cleanup
    DATA_RATE_SLOWDOWN_FACTOR = daq_common.data_rate_slowdown_factor
    CLOCK_SPEED_HZ = detector.clock_speed_hz
    TRG_CONFIG = tp_infos
    ACTIVITY_PLUGIN = trigger.trigger_activity_plugin
    ACTIVITY_CONFIG = trigger.trigger_activity_config
    CANDIDATE_PLUGIN = trigger.trigger_candidate_plugin
    CANDIDATE_CONFIG = trigger.trigger_candidate_config
    TTCM_INPUT_MAP = update_ttcm_map(trigger.ttcm_input_map,
                                     trigger.trigger_window_before_ticks,
                                     trigger.trigger_window_after_ticks)
    TTCM_PRESCALE=trigger.ttcm_prescale
    USE_SOFTWARE_TRIGGER = trigger.use_software_trigger
    USE_HSI_INPUT = use_hsi_input
    USE_FAKE_HSI_INPUT = use_fake_hsi_input
    USE_CTB_INPUT = use_ctb_input
    FAKE_HSI_CTB = fake_hsi_to_ctb
    CTB_PRESCALE=trigger.ctb_prescale
    CTB_TIME_BEFORE=trigger.ctb_time_before
    CTB_TIME_AFTER=trigger.ctb_time_after
    USE_CIB_INPUT=use_cib_input
    CIB_PRESCALE=trigger.cib_prescale
    CIB_TIME_BEFORE=trigger.cib_time_before
    CIB_TIME_AFTER=trigger.cib_time_after
    MLT_MERGE_OVERLAPPING_TCS = trigger.mlt_merge_overlapping_tcs
    MLT_BUFFER_TIMEOUT = trigger.mlt_buffer_timeout
    MLT_MAX_TD_LENGTH_MS = trigger.mlt_max_td_length_ms
    MLT_SEND_TIMED_OUT_TDS = trigger.mlt_send_timed_out_tds
    MLT_IGNORE_TC = trigger.mlt_ignore_tc
    MLT_USE_READOUT_MAP = trigger.mlt_use_readout_map
    MLT_READOUT_MAP = trigger.mlt_td_readout_map
    MLT_USE_BITWORDS = trigger.mlt_use_bitwords
    MLT_TRIGGER_BITWORDS = trigger.mlt_trigger_bitwords
    MLT_USE_ROI_READOUT = trigger.mlt_use_roi_readout
    MLT_ROI_CONF = trigger.mlt_roi_conf
    USE_CUSTOM_MAKER = trigger.use_custom_maker
    CTCM_TYPES = trigger.ctcm_trigger_types
    CTCM_INTERVAL = trigger.ctcm_trigger_intervals
    CTCM_TIMESTAMP_METHOD = trigger.ctcm_timestamp_method
    USE_RANDOM_MAKER = trigger.use_random_maker
    RTCM_INTERVAL = trigger.rtcm_trigger_interval_ticks
    RTCM_TIMESTAMP_METHOD = trigger.rtcm_timestamp_method
    RTCM_DISTRIBUTION = trigger.rtcm_time_distribution
    CHANNEL_MAP_NAME = detector.tpc_channel_map
    DATA_REQUEST_TIMEOUT=trigger_data_request_timeout
    HOST=trigger.host_trigger

    # Check HSI config
    check_hsi_config(USE_FAKE_HSI_INPUT, FAKE_HSI_CTB)

    # Generate schema for each of the maker plugins on the fly in the temptypes module
    num_algs = len(ACTIVITY_PLUGIN)
    for j in range(num_algs):
        make_moo_record(ACTIVITY_CONFIG[j] , 'ActivityConf' , 'temptypes')
        make_moo_record(CANDIDATE_CONFIG[j], 'CandidateConf', 'temptypes')

    import temptypes

    # How many clock ticks are there in a _wall clock_ second?
    ticks_per_wall_clock_s = CLOCK_SPEED_HZ / DATA_RATE_SLOWDOWN_FACTOR
    
    # Converting certain parameters to ticks instead of ms
    max_td_length_ticks = MLT_MAX_TD_LENGTH_MS * CLOCK_SPEED_HZ / 1000
    
    modules = []
    
    TP_SOURCE_IDS = {}
    TA_SOURCE_IDS = {}
    TC_SOURCE_ID = {}

    for trigger_sid,conf in TRG_CONFIG.items():
        # Don't fill all the source IDs if we're not using software trigger
        if USE_SOFTWARE_TRIGGER:
            if isinstance(conf, TPInfo):
                TP_SOURCE_IDS[trigger_sid] = conf
            elif isinstance(conf, TAInfo):
                TA_SOURCE_IDS[(conf.region_id, conf.plane)] = {"source_id": trigger_sid, "conf": conf}
        if isinstance(conf, TCInfo):
            TC_SOURCE_ID = {"source_id": trigger_sid, "conf": conf}
       
    # Check for present of TC sources. At least 1 is required
    if not tc_source_present(USE_HSI_INPUT, USE_FAKE_HSI_INPUT, USE_CTB_INPUT, USE_CIB_INPUT, USE_CUSTOM_MAKER, USE_RANDOM_MAKER, len(TP_SOURCE_IDS)):
        raise RuntimeError('There are no TC sources!')
 
    # We always have a TC buffer even when there are no TPs, because we want to put the timing TC in the output file
    modules += [DAQModule(name = 'tc_buf',
                          plugin = 'TCBuffer',
                          conf = get_buffer_conf(TC_SOURCE_ID["source_id"], DATA_REQUEST_TIMEOUT))]
    if USE_HSI_INPUT:
        modules += [DAQModule(name = 'tctee_t',
                         plugin = 'TCTee')]
    if USE_CTB_INPUT:
        modules += [DAQModule(name = 'tctee_ctb',
                         plugin = 'TCTee')]
    if USE_FAKE_HSI_INPUT and not FAKE_HSI_CTB :
        modules += [DAQModule(name = 'tctee_tcmfake',
                         plugin = 'TCTee')]
    if USE_FAKE_HSI_INPUT and FAKE_HSI_CTB:
        modules += [DAQModule(name = 'tctee_ctbfake',
                         plugin = 'TCTee')]

    if USE_CIB_INPUT:
        modules += [DAQModule(name = 'tctee_cibtcm',
                         plugin = 'TCTee')]

    if len(TP_SOURCE_IDS) > 0:        
        cm_configs = []
        # Get a list of TCMaker configs if more than one exists:
        for j, cm_conf in enumerate(CANDIDATE_CONFIG):
            cm_configs.append(tcm.Conf(candidate_maker=CANDIDATE_PLUGIN[j],
                                       candidate_maker_config=temptypes.CandidateConf(CANDIDATE_CONFIG[j])))
    
         # (PAR 2022-06-09) The max_latency_ms here should be kept
         # larger than the corresponding value in the upstream
         # TPZippers. See comment below for more details
        for j, cm_config in enumerate(cm_configs):
            modules += [DAQModule(name = f'tazipper_{j}',
                              plugin = 'TAZipper',
                              conf = tzip.ConfParams(cardinality=len(TA_SOURCE_IDS),
                                                     max_latency_ms=1000,
                                                     element_id=TC_SOURCE_ID["source_id"])),
                        DAQModule(name = f'tcm_{j}',
                              plugin = 'TriggerCandidateMaker',
                              conf = tcm.Conf(candidate_maker=CANDIDATE_PLUGIN[j],
                                     candidate_maker_config=temptypes.CandidateConf(CANDIDATE_CONFIG[j]))),

                        DAQModule(name = f'tctee_swt_{j}',
                              plugin = 'TCTee'),]

        for tp_sid,tp_conf in TP_SOURCE_IDS.items():
            ru_sid = f'{tp_conf.tp_ru_sid}'
            region = f'{tp_conf.region_id}'
            plane = f'{tp_conf.plane}'

            if USE_CHANNEL_FILTER:
                modules += [DAQModule(name = f'tpcf_{region}_{plane}',
                                      plugin = 'TPChannelFilter',
                                      conf = chfilter.Conf(channel_map_name=CHANNEL_MAP_NAME,
                                                           keep_collection=True,
                                                           keep_induction=True,
                                                           max_time_over_threshold=10_000))]
        
        for (region_id, plane), ta_conf in TA_SOURCE_IDS.items():
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

                # Add a TAMaker for each one and it's config supplied, additionally add a TASetTee:
                for j, tamaker in enumerate(ACTIVITY_PLUGIN):
                    modules += [DAQModule(name = f'tam_{region_id}_{plane}_{j}',
                                          plugin = 'TriggerActivityMaker',
                                          conf = tam.Conf(activity_maker=tamaker,
                                                          geoid_element=region_id,  # 2022-02-02 PL: Same comment as above
                                                          window_time=10000,  # should match whatever makes TPSets, in principle
                                                          buffer_time=10*ticks_per_wall_clock_s//1000, # 10 wall-clock ms
                                                          activity_maker_config=temptypes.ActivityConf(ACTIVITY_CONFIG[j]))),
                                DAQModule(name = f'tasettee_{region_id}_{plane}_{j}', plugin = "TASetTee")]

                # Add the zippers and TABuffers, independant of the number of algorithms we want to run concurrently.
                modules += [
                            DAQModule(name = f'ta_buf_{region_id}_{plane}',
                                      plugin = 'TABuffer',
                                      # PAR 2022-04-20 Not sure what to set the element id to so it doesn't collide with the region/element used by TP buffers. Make it some big number that shouldn't already be used by the TP buffer
                                      conf = bufferconf.Conf(latencybufferconf = readoutconf.LatencyBufferConf(latency_buffer_size = 100_000),
                                                             requesthandlerconf = readoutconf.RequestHandlerConf(latency_buffer_size = 100_000,
                                                                                                                 pop_limit_pct = 0.8,
                                                                                                                 pop_size_pct = 0.1,
                                                                                                                 source_id = ta_conf["source_id"],
                                                                                                                 det_id = 1,
                                                                                                                 # output_file = f"output_{idx + MIN_LINK}.out",
                                                                                                                 stream_buffer_size = 8388608,
                                                                                                                 request_timeout_ms = DATA_REQUEST_TIMEOUT,
                                                                                                                 enable_raw_recording = False)))]

                if(num_algs > 1):
                    modules += [DAQModule(name = f'tpsettee_ma_{region_id}_{plane}',
                                          plugin = 'TPSetTee'),]

    if USE_HSI_INPUT:
        modules += [DAQModule(name = 'ttcm',
                          plugin = 'TimingTriggerCandidateMaker',
                          conf=ttcm.Conf(hsi_configs=TTCM_INPUT_MAP,
                                         prescale=TTCM_PRESCALE))]

    if USE_FAKE_HSI_INPUT and not FAKE_HSI_CTB:
        modules += [DAQModule(name = 'ttcm_fake',
                          plugin = 'TimingTriggerCandidateMaker',
                          conf=ttcm.Conf(hsi_configs=TTCM_INPUT_MAP,
                                         prescale=TTCM_PRESCALE))]

    if USE_CTB_INPUT:
        modules += [DAQModule(name = 'ctbtcm',
                          plugin = 'CTBTriggerCandidateMaker',
                          conf=ctbtcm.Conf(prescale=CTB_PRESCALE,
                                           time_before=CTB_TIME_BEFORE,
                                           time_after=CTB_TIME_AFTER))]

        
    if USE_FAKE_HSI_INPUT and FAKE_HSI_CTB:
        modules += [DAQModule(name = 'ctbtcm_fake',
                          plugin = 'CTBTriggerCandidateMaker',
                          conf=ctbtcm.Conf(prescale=CTB_PRESCALE,
                                           time_before=CTB_TIME_BEFORE,
                                           time_after=CTB_TIME_AFTER))]
    
    if USE_CIB_INPUT:
        modules += [DAQModule(name = 'cibtcm',
                          plugin = 'CIBTriggerCandidateMaker',
                          conf=cibtcm.Conf(prescale=CIB_PRESCALE,
                                           time_before=CIB_TIME_BEFORE,
                                           time_after=CIB_TIME_AFTER))]

    if USE_CUSTOM_MAKER:
        if (len(CTCM_TYPES) != len(CTCM_INTERVAL)):
            raise RuntimeError(f'CTCM requires same size of types and intervals!')
        modules += [DAQModule(name = 'ctcm',
                       plugin = 'CustomTriggerCandidateMaker',
                       conf=ctcm.Conf(trigger_types=CTCM_TYPES,
                       trigger_intervals=CTCM_INTERVAL,
                       clock_frequency_hz=CLOCK_SPEED_HZ,
                       timestamp_method=CTCM_TIMESTAMP_METHOD))]
        modules += [DAQModule(name = 'tctee_ctcm',
                       plugin = 'TCTee')]

    if USE_RANDOM_MAKER:
        modules += [DAQModule(name = 'rtcm',
                       plugin = 'RandomTriggerCandidateMaker',
                       conf=rtcm.Conf(trigger_interval_ticks=RTCM_INTERVAL,
                       clock_frequency_hz=CLOCK_SPEED_HZ,
                       timestamp_method=RTCM_TIMESTAMP_METHOD,
                       time_distribution=RTCM_DISTRIBUTION))]
        modules += [DAQModule(name = 'tctee_rtcm',
                       plugin = 'TCTee')]

    ### get trigger bitwords for mlt
    MLT_TRIGGER_FLAGS = get_trigger_bitwords(MLT_TRIGGER_BITWORDS)

    ### check ROI probability is valid
    if MLT_USE_ROI_READOUT:
        check_mlt_roi_config(MLT_ROI_CONF, len(TP_SOURCE_IDS))
    
    # We need to populate the list of links based on the fragment
    # producers available in the system. This is a bit of a
    # chicken-and-egg problem, because the trigger app itself creates
    # fragment producers (see below). Eventually when the MLT is its
    # own process, this problem will probably go away, but for now, we
    # leave the list of links here blank, and replace it in
    # util.connect_fragment_producers
    modules += [DAQModule(name = 'mlt',
                          plugin = 'ModuleLevelTrigger',
                          conf=mlt.ConfParams(mandatory_links=[],  # To be updated later - see comment above
                                              groups_links=[],     # To be updated later - see comment above
                                              merge_overlapping_tcs=MLT_MERGE_OVERLAPPING_TCS,
                                              buffer_timeout=MLT_BUFFER_TIMEOUT,
                                              td_out_of_timeout=MLT_SEND_TIMED_OUT_TDS,
                                              ignore_tc=MLT_IGNORE_TC,
                                              td_readout_limit=max_td_length_ticks,
                                              use_readout_map=MLT_USE_READOUT_MAP,
                                              td_readout_map=MLT_READOUT_MAP,
                                              use_roi_readout=MLT_USE_ROI_READOUT,
                                              roi_conf=MLT_ROI_CONF,
					      use_bitwords=MLT_USE_BITWORDS,
					      trigger_bitwords=MLT_TRIGGER_FLAGS))]

    mgraph = ModuleGraph(modules)

    if USE_HSI_INPUT:
        mgraph.connect_modules("ttcm.output",     "tctee_t.input",               "TriggerCandidate", "ttcm_input", size_hint=1000)
        mgraph.connect_modules("tctee_t.output1", "mlt.trigger_candidate_input", "TriggerCandidate", "tcs_to_mlt", size_hint=1000)
        mgraph.connect_modules("tctee_t.output2", "tc_buf.tc_source",            "TriggerCandidate", "tcs_to_buf", size_hint=1000)
        mgraph.add_endpoint("dts_hsievents", "ttcm.hsi_input", "HSIEvent", Direction.IN)

    if USE_FAKE_HSI_INPUT and not FAKE_HSI_CTB:
        mgraph.connect_modules("ttcm_fake.output",      "tctee_tcmfake.input",         "TriggerCandidate", "ttcm_fake_input", size_hint=1000)
        mgraph.connect_modules("tctee_tcmfake.output1", "mlt.trigger_candidate_input", "TriggerCandidate", "tcs_to_mlt",      size_hint=1000)
        mgraph.connect_modules("tctee_tcmfake.output2", "tc_buf.tc_source",            "TriggerCandidate", "tcs_to_buf",      size_hint=1000)
        mgraph.add_endpoint("fake_hsievents", "ttcm_fake.hsi_input", "HSIEvent", Direction.IN)

    if USE_CTB_INPUT:
        mgraph.connect_modules("ctbtcm.output",     "tctee_ctb.input",             "TriggerCandidate", "ctbtcm_input", size_hint=1000)
        mgraph.connect_modules("tctee_ctb.output1", "mlt.trigger_candidate_input", "TriggerCandidate", "tcs_to_mlt",   size_hint=1000)
        mgraph.connect_modules("tctee_ctb.output2", "tc_buf.tc_source",            "TriggerCandidate", "tcs_to_buf",   size_hint=1000)
        mgraph.add_endpoint("ctb_hsievents", "ctbtcm.hsi_input", "HSIEvent", Direction.IN)
    if USE_FAKE_HSI_INPUT and FAKE_HSI_CTB:
        mgraph.connect_modules("ctbtcm_fake.output",    "tctee_ctbfake.input",         "TriggerCandidate", "ctbtcm_fake_input", size_hint=1000)
        mgraph.connect_modules("tctee_ctbfake.output1", "mlt.trigger_candidate_input", "TriggerCandidate", "tcs_to_mlt",        size_hint=1000)
        mgraph.connect_modules("tctee_ctbfake.output2", "tc_buf.tc_source",            "TriggerCandidate", "tcs_to_buf",        size_hint=1000)
        mgraph.add_endpoint("fake_hsievents", "ctbtcm_fake.hsi_input", "HSIEvent", Direction.IN)

    if USE_CIB_INPUT:
        mgraph.connect_modules("cibtcm.output",              "tctee_cibtcm.input",          "TriggerCandidate", "cibtcm_input", size_hint=1000)
        mgraph.connect_modules("tctee_cibtcm.output1",       "mlt.trigger_candidate_input", "TriggerCandidate", "tcs_to_mlt",   size_hint=1000)
        mgraph.connect_modules("tctee_cibtcm.output2",       "tc_buf.tc_source",            "TriggerCandidate", "tcs_to_buf",   size_hint=1000)
        mgraph.add_endpoint("cib_hsievents", "cibtcm.hsi_input", "HSIEvent", Direction.IN)
    if USE_CUSTOM_MAKER:
        mgraph.connect_modules("ctcm.trigger_candidate_sink", "tctee_ctcm.input",            "TriggerCandidate", "ctcm_input", size_hint=1000)
        mgraph.connect_modules("tctee_ctcm.output1",          "mlt.trigger_candidate_input", "TriggerCandidate", "tcs_to_mlt", size_hint=1000)
        mgraph.connect_modules("tctee_ctcm.output2",          "tc_buf.tc_source",            "TriggerCandidate", "tcs_to_buf", size_hint=1000)
    if USE_RANDOM_MAKER:
        mgraph.connect_modules("rtcm.trigger_candidate_sink", "tctee_rtcm.input",            "TriggerCandidate", "rtcm_input", size_hint=1000)
        mgraph.connect_modules("tctee_rtcm.output1",          "mlt.trigger_candidate_input", "TriggerCandidate", "tcs_to_mlt", size_hint=1000)
        mgraph.connect_modules("tctee_rtcm.output2",          "tc_buf.tc_source",            "TriggerCandidate", "tcs_to_buf", size_hint=1000)

    if len(TP_SOURCE_IDS) > 0:
        for j in range(num_algs):
            mgraph.connect_modules(f"tazipper_{j}.output", f"tcm_{j}.input", data_type="TASet", size_hint=1000)

        for tp_sid,tp_conf in TP_SOURCE_IDS.items():
            ru_sid = f'{tp_conf.tp_ru_sid}'
            region = f'{tp_conf.region_id}'
            plane = f'{tp_conf.plane}'
            if USE_CHANNEL_FILTER:
                if(num_algs > 1):
                    mgraph.connect_modules(f'tpcf_{region}_{plane}.tpset_sink', f'tpsettee_ma_{region}_{plane}.input', data_type="TPSet", size_hint=1000)
                else:
                    mgraph.connect_modules(f'tpcf_{region}_{plane}.tpset_sink', f'tam_{region}_{plane}_0.input', data_type="TPSet", size_hint=1000)

        ## # Use connect_modules to connect up the Tees to the buffers/MLT,
        ## # as manually adding Queues doesn't give the desired behaviour

        for region_id in TA_SOURCE_IDS.keys():
            # Send the output of the new TPSetTee module to each of the activity makers
            if(num_algs > 1):
                for j in range(num_algs):
                    mgraph.connect_modules(f'tpsettee_ma_{region_id}_{plane}.output{j+1}', f'tam_{region_id}_{plane}_{j}.input', "TPSet", size_hint=1000)

        # For each TCMaker config applied, connect the TCMaker to it's copyer, then to the MLT and TCBuffer via that copyer.
        for j in range(len(cm_configs)):
            mgraph.connect_modules(f"tcm_{j}.output", f"tctee_swt_{j}.input", "TriggerCandidate", f"chain_input_{j}", size_hint=1000)
            mgraph.connect_modules(f"tctee_swt_{j}.output1", "mlt.trigger_candidate_input", "TriggerCandidate", "tcs_to_mlt",  size_hint=1000)
            mgraph.connect_modules(f"tctee_swt_{j}.output2", "tc_buf.tc_source", "TriggerCandidate","tcs_to_buf", size_hint=1000)

        # For each TAMaker applied, connect the makers output to it's copyer, then connect the copyer's output to the buffer and TAZipper
        for region_id, plane in TA_SOURCE_IDS.keys():
            for j in range(num_algs):
                mgraph.connect_modules(f'tam_{region_id}_{plane}_{j}.output', f'tasettee_{region_id}_{plane}_{j}.input', data_type="TASet", size_hint=1000)
                mgraph.connect_modules(f'tasettee_{region_id}_{plane}_{j}.output1', f'tazipper_{j}.input', queue_name=f"tas{j}_to_tazipper{j}", data_type="TASet", size_hint=1000)
                mgraph.connect_modules(f'tasettee_{region_id}_{plane}_{j}.output2', f'ta_buf_{region_id}_{plane}.taset_source',data_type="TASet", size_hint=1000)

    mgraph.add_endpoint("td_to_dfo", "mlt.td_output", "TriggerDecision", Direction.OUT, toposort=True)
    mgraph.add_endpoint("df_busy_signal", "mlt.dfo_inhibit_input", "TriggerInhibit", Direction.IN)

    mgraph.add_fragment_producer(id=TC_SOURCE_ID["source_id"], subsystem="Trigger",
                                 requests_in="tc_buf.data_request_source",
                                 fragments_out="tc_buf.fragment_sink")

    if len(TP_SOURCE_IDS) > 0:
        for tp_sid,tp_conf in TP_SOURCE_IDS.items():
                ru_sid = f'{tp_conf.tp_ru_sid}'
                region = f'{tp_conf.region_id}'
                plane = f'{tp_conf.plane}'
              
                if USE_CHANNEL_FILTER:
                    mgraph.add_endpoint(f"tpsets_tplink{ru_sid}", f"tpcf_{region}_{plane}.tpset_source", "TPSet", Direction.IN, is_pubsub=True)
                else:
                    mgraph.add_endpoint(f"tpsets_tplink{ru_sid}", f'tam_{region}_{plane}_0.input', "TPSet", Direction.IN, is_pubsub=True)

        for (region_id, plane), ta_conf in TA_SOURCE_IDS.items():
            buf_name = f'ta_buf_{region_id}_{plane}'
            mgraph.add_fragment_producer(id=ta_conf["source_id"], subsystem="Trigger",
                                         requests_in=f"{buf_name}.data_request_source",
                                         fragments_out=f"{buf_name}.fragment_sink")


    trigger_app = App(modulegraph=mgraph, host=HOST, name='TriggerApp')
    
    return trigger_app

