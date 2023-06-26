// This is the configuration schema for daqconf_multiru_gen
//

local moo = import "moo.jsonnet";

local s = moo.oschema.schema("dunedaq.daqconf.dqmgen");
local nc = moo.oschema.numeric_constraints;

local cs = {
  port:            s.number(   "Port", "i4", doc="A TCP/IP port number"),
  freq:            s.number(   "Frequency", "u4", doc="A frequency"),
  rate:            s.number(   "Rate", "f8", doc="A rate as a double"),
  count:           s.number(   "count", "i8", doc="A count of things"),
  three_choice:    s.number(   "threechoice", "i8", nc(minimum=0, exclusiveMaximum=3), doc="A choice between 0, 1, or 2"),
  flag:            s.boolean(  "Flag", doc="Parameter that can be used to enable or disable functionality"),
  monitoring_dest: s.enum(     "MonitoringDest", ["local", "cern", "pocket"]),
  path:            s.string(   "Path", doc="Location on a filesystem"),
  paths:           s.sequence( "Paths",         self.path, doc="Multiple paths"),
  host:            s.string(   "Host",          moo.re.dnshost, doc="A hostname"),
  hosts:           s.sequence( "Hosts",         self.host, "Multiple hosts"),
  string:          s.string(   "Str",           doc="Generic string"),
  strings:         s.sequence( "Strings",  self.string, doc="List of strings"),
  tpg_channel_map: s.enum(     "TPGChannelMap", ["VDColdboxChannelMap", "ProtoDUNESP1ChannelMap", "PD2HDChannelMap", "HDColdboxChannelMap"]),
  dqm_channel_map: s.enum(     "DQMChannelMap", ['HD', 'VD', 'PD2HD', 'HDCB']),
  dqm_params:      s.sequence( "DQMParams",     self.count, doc="Parameters for DQM (fixme)"),
  tc_types:        s.sequence( "TCTypes",       self.count, doc="List of TC types"),
  tc_type:         s.number(   "TCType",        "i4", nc(minimum=0, maximum=9), doc="Number representing TC type. Currently ranging from 0 to 9"),
  tc_interval:     s.number(   "TCInterval",    "i8", nc(minimum=1, maximum=30000000000), doc="The intervals between TCs that are inserted into MLT by CTCM, in clock ticks"),
  tc_intervals:    s.sequence( "TCIntervals",   self.tc_interval, doc="List of TC intervals used by CTCM"),
  readout_time:    s.number(   "ROTime",        "i8", doc="A readout time in ticks"),
  channel_list:    s.sequence( "ChannelList",   self.count, doc="List of offline channels to be masked out from the TPHandler"),
  tpg_algo_choice: s.enum(     "TPGAlgoChoice", ["SimpleThreshold", "AbsRS"], doc="Trigger algorithm choice"),
  pm_choice:       s.enum(     "PMChoice", ["k8s", "ssh"], doc="Process Manager choice: ssh or Kubernetes"),
  rte_choice:      s.enum(     "RTEChoice", ["auto", "release", "devarea"], doc="Kubernetes DAQ application RTE choice"),
  


  dqm: s.record("dqm", [
    s.field('enable_dqm', self.flag, default=false, doc="Enable Data Quality Monitoring"),
    s.field('impl', self.monitoring_dest, default='local', doc="DQM destination (Kafka used for cern and pocket)"),
    s.field('cmap', self.dqm_channel_map, default='HD', doc="Which channel map to use for DQM"),
    s.field('host_dqm', self.hosts, default=['localhost'], doc='Host(s) to run the DQM app on'),
    s.field('raw_params', self.dqm_params, default=[60, 50], doc="Parameters that control the data sent for the raw display plot"),
    s.field('std_params', self.dqm_params, default=[10, 1000], doc="Parameters that control the data sent for the mean/rms plot"),
    s.field('rms_params', self.dqm_params, default=[0, 1000], doc="Parameters that control the data sent for the mean/rms plot"),
    s.field('fourier_channel_params', self.dqm_params, default=[0, 0], doc="Parameters that control the data sent for the fourier transform plot"),
    s.field('fourier_plane_params', self.dqm_params, default=[600, 1000], doc="Parameters that control the data sent for the summed fourier transform plot"),
    s.field('df_rate', self.count, default=10, doc='How many seconds between requests to DF for Trigger Records'),
    s.field('df_algs', self.string, default='raw std fourier_plane', doc='Algorithms to be run on Trigger Records from DF (use quotes)'),
    s.field('max_num_frames', self.count, default=32768, doc='Maximum number of frames to use in the algorithms'),
    s.field('kafka_address', self.string, default='', doc='kafka address used to send messages'),
    s.field('kafka_topic', self.string, default='DQM', doc='kafka topic used to send messages'),
  ]),
};


moo.oschema.sort_select(cs)
