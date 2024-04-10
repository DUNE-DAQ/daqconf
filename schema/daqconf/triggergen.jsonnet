// This is the configuration schema for common (fd/nd)daqconf_gen
//

local moo = import "moo.jsonnet";

local stypes = import "daqconf/types.jsonnet";
local types = moo.oschema.hier(stypes).dunedaq.daqconf.types;

local s = moo.oschema.schema("dunedaq.daqconf.triggergen");
local nc = moo.oschema.numeric_constraints;
// A temporary schema construction context.
local cs = {
  tc_type:         s.number(   "TCType",        "i4", nc(minimum=0, maximum=28), doc="Number representing TC type."),
  tc_type_name:     s.string(   "TCTypeName"),
  tc_types:        s.sequence( "TCTypes",       self.tc_type, doc="List of TC types"),
  tc_interval:     s.number(   "TCInterval",    "i8", nc(minimum=1, maximum=30000000000), doc="The intervals between TCs that are inserted into MLT by CTCM, in clock ticks"),
  tc_intervals:    s.sequence( "TCIntervals",   self.tc_interval, doc="List of TC intervals used by CTCM"),
  tm_algorithms:   s.sequence( "TriggerAlgorithms", types.string, doc="List of TAMaker algorithms to run concurrently."),
  tm_configs:      s.sequence( "TriggerAlgorithmsConfigs", self.trigger_algo_config, doc="List of TAMaker algorithm configs."),
  timestamp_estimation: s.enum("timestamp_estimation", ["kTimeSync", "kSystemClock"]),
  distribution_type: s.enum("distribution_type", ["kUniform", "kPoisson"]),
  readout_time:    s.number(   "ROTime",        "i8", doc="A readout time in ticks"),
  bitword:	   s.string(   "Bitword",       doc="A string representing the TC type name, to be set in the trigger bitword."),
  bitword_list:    s.sequence( "BitwordList",   self.bitword, doc="A sequence of bitword (TC type bits) forming a bitword."),
  bitwords:        s.sequence( "Bitwords",      self.bitword_list, doc="List of bitwords to use when forming trigger decisions in MLT"),
  number_of_groups: s.number(  "Ngroups",       "i4", nc(minimum=0, maximum=150), doc="Number of groups of detector links to readout, useful for MLT ROI"),
  probability:      s.number(  "Prob",          "f4", nc(minimum=0.0, maximum=1.0), doc="Probability to read out a group of links, useful for MLT ROI"),
  group_selection:  s.enum(    "GroupSelection", ["kRandom", "kSequential"]),

  trigger_algo_config: s.record("trigger_algo_config", [
    s.field("prescale", types.count, default=100),
    s.field("window_length", types.count, default=10000),
    s.field("adjacency_threshold", types.count, default=6),
    s.field("adj_tolerance", types.count, default=4),
    s.field("trigger_on_adc", types.flag, default=false),
    s.field("trigger_on_n_channels", types.flag, default=false),
    s.field("trigger_on_adjacency", types.flag, default=true),
    s.field("adc_threshold", types.count, default=10000),
    s.field("n_channels_threshold", types.count, default=8),
    s.field("print_tp_info", types.flag, default=false),
    s.field("bundle_size", types.count, default=100),
    s.field("min_tps", types.count, default=20),
    s.field("max_channel_distance", types.count, default=50),
    s.field("max_tp_count", types.count, default=1000),
    s.field("min_pts", types.count, default=7),
    s.field("eps", types.count, default=20),
  ]),

  tc_readout: s.record( "tc_readout", [
    s.field("candidate_type", self.tc_type,      default=0,     doc="The TC type, 0=Unknown"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),

  tc_readout_map: s.sequence( "tc_readout_map", self.tc_readout),

  hsi_input: s.record("hsi_input", [
    s.field("signal",         types.count, default=1, doc="HSI candidate maker accepted HSI signal ID"),
    s.field("tc_type_name",   self.tc_type_name, default="kTiming", doc="Name of the TC type"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),

  hsi_input_map: s.sequence("hsi_input_map", self.hsi_input),

  mlt_roi_group_conf: s.record("mlt_roi_group_conf", [
    s.field("number_of_link_groups", self.number_of_groups, default=1,         doc="Number of groups of links to readout"),
    s.field("probability",           self.probability,      default=0.1,       doc="Probability to select this configuration [0 to 1]"),
    s.field("time_window",           self.readout_time,     default=1000,      doc="Time window to read out pre/post decision, [clock ticks]"),
    s.field("groups_selection_mode", self.group_selection,  default="kRandom", doc="Whether to read out random groups or in sequence"), 
  ]),
 
  mlt_roi_conf_map: s.sequence("mlt_roi_conf_map", self.mlt_roi_group_conf),

  trigger: s.record("trigger",[
    s.field( "host_trigger", types.host, default='localhost', doc='Host to run the trigger app on'),
    # trigger options
    s.field( "trigger_window_before_ticks",types.count, default=1000, doc="Trigger window before marker. Former -b"),
    s.field( "trigger_window_after_ticks", types.count, default=1000, doc="Trigger window after marker. Former -a"),
    s.field( "ttcm_input_map", self.hsi_input_map, default=[
      {"signal":0, "tc_type_name":"kTiming", "time_before":1000, "time_after":1000},
      {"signal":1, "tc_type_name":"kTiming", "time_before":1000, "time_after":1000},
      {"signal":2, "tc_type_name":"kTiming", "time_before":1000, "time_after":1000},
      {"signal":3, "tc_type_name":"kTiming", "time_before":1000, "time_after":1000}
    ], doc="Timing trigger candidate maker accepted HSI signal map"),
    s.field( "ttcm_prescale", types.count, default=1, doc="Option to prescale TTCM TCs"),
    s.field( "ctb_prescale", types.count, default=1, doc="Option to prescale CTB TCs"),
    s.field( "ctb_time_before", self.readout_time, default=1000, doc="Trigger readout window before CTB TC"),
    s.field( "ctb_time_after", self.readout_time, default=1000, doc="Trigger readout window after CTB TC"),
    s.field( "trigger_activity_plugin", self.tm_algorithms, default=['TriggerActivityMakerPrescalePlugin'], doc="List of trigger activity algorithm plugins"),
    s.field( "trigger_activity_config", self.tm_configs, default=[self.trigger_algo_config], doc="List of trigger activity algorithm configs (strings containing python dictionary)"),
    s.field( "trigger_candidate_plugin", self.tm_algorithms, default=['TriggerCandidateMakerPrescalePlugin'], doc="List of trigger candidate algorithm plugins"),
    s.field( "trigger_candidate_config", self.tm_configs, default=[self.trigger_algo_config], doc="List of trigger candidate algorithm configs (strings containing python dictionary)"),
    s.field( "mlt_merge_overlapping_tcs", types.flag, default=true, doc="Option to turn off merging of overlapping TCs when forming TDs in MLT"),
    s.field( "mlt_buffer_timeout", types.count, default=100, doc="Timeout (buffer) to wait for new overlapping TCs before sending TD"),
    s.field( "mlt_send_timed_out_tds", types.flag, default=true, doc="Option to drop TD if TC comes out of timeout window"),
    s.field( "mlt_max_td_length_ms", types.count, default=1000, doc="Maximum allowed time length [ms] for a readout window of a single TD"),
    s.field( "mlt_ignore_tc", self.tc_types, default=[], doc="Optional list of TC types to be ignored in MLT"),
    s.field( "mlt_use_readout_map", types.flag, default=false, doc="Option to use custom readout map in MLT"),
    s.field( "mlt_td_readout_map", self.tc_readout_map, default=[self.tc_readout], doc="The readout windows assigned to TDs in MLT, based on TC type."),
    s.field( "mlt_use_bitwords", types.flag, default=false, doc="Option to use bitwords (ie trigger types, coincidences) when forming trigger decisions in MLT" ),
    s.field( "mlt_trigger_bitwords", self.bitwords, default=[], doc="Optional dictionary of bitwords to use when forming trigger decisions in MLT" ),
    s.field( "mlt_use_roi_readout", types.flag, default=false, doc="Option to use ROI readout in MLT: only readout selection of fragment producers"),
    s.field( "mlt_roi_conf", self.mlt_roi_conf_map, default=[self.mlt_roi_group_conf], doc="The configuration (table) for ROI readout"),
    s.field( "use_custom_maker", types.flag, default=false, doc="Option to use a Custom Trigger Candidate Maker (plugin)"),
    s.field( "ctcm_trigger_types", self.tc_types, default=[4], doc="Optional list of TC types to be used by the Custom Trigger Candidate Maker (plugin)"),
    s.field( "ctcm_trigger_intervals", self.tc_intervals, default=[10000000], doc="Optional list of intervals (clock ticks) for the TC types to be used by the Custom Trigger Candidate Maker (plugin)"),
    s.field( "ctcm_timestamp_method", self.timestamp_estimation, "kSystemClock", doc="Option to pick source for timing (system / timesync)"),
    s.field( "use_random_maker", types.flag, default=false, doc="Option to use a Random Trigger Candidate Maker (plugin)"),
    s.field( "rtcm_trigger_interval_ticks", self.tc_interval, default=62500000, doc="Interval between triggers in 16 ns time ticks (default 1.024 s)"),
    s.field( "rtcm_timestamp_method", self.timestamp_estimation, "kSystemClock", doc="Option to pick source for timing (system / timesync)"),
    s.field( "rtcm_time_distribution", self.distribution_type, "kUniform", doc="Type of distribution used for random timestamps (uniform or poisson)"),
  ]),

};

stypes + moo.oschema.sort_select(cs)
