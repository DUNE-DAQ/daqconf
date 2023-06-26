// This is the configuration schema for daqconf_multiru_gen
//

local moo = import "moo.jsonnet";

local s = moo.oschema.schema("dunedaq.daqconf.timinggen");
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

  timing: s.record("timing", [
    s.field( "timing_session_name", self.string, default="", doc="Name of the global timing session to use, for timing commands"),
    s.field( "host_tprtc", self.host, default='localhost', doc='Host to run the timing partition controller app on'),
    # timing hw partition options
    s.field( "control_timing_partition", self.flag, default=false, doc='Flag to control whether we are controlling timing partition in master hardware'),
    s.field( "timing_partition_master_device_name", self.string, default="", doc='Timing partition master hardware device name'),
    s.field( "timing_partition_id", self.count, default=0, doc='Timing partition id'),
    s.field( "timing_partition_trigger_mask", self.count, default=255, doc='Timing partition trigger mask'),
    s.field( "timing_partition_rate_control_enabled", self.flag, default=false, doc='Timing partition rate control enabled'),
    s.field( "timing_partition_spill_gate_enabled", self.flag, default=false, doc='Timing partition spill gate enabled'),
  ]),
};


moo.oschema.sort_select(cs)
