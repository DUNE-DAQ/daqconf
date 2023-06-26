// This is the configuration schema for daqconf_multiru_gen
//

local moo = import "moo.jsonnet";

local s = moo.oschema.schema("dunedaq.daqconf.hsigen");
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
  

  hsi: s.record("hsi", [
    # timing hsi options
    s.field( "use_timing_hsi", self.flag, default=false, doc='Flag to control whether real hardware timing HSI config is generated. Default is false'),
    s.field( "host_timing_hsi", self.host, default='localhost', doc='Host to run the HSI app on'),
    s.field( "hsi_hw_connections_file", self.path, default="${TIMING_SHARE}/config/etc/connections.xml", doc='Real timing hardware only: path to hardware connections file'),
    s.field( "enable_hardware_state_recovery", self.flag, default=true, doc="Enable (or not) hardware state recovery"),
    s.field( "hsi_device_name", self.string, default="", doc='Real HSI hardware only: device name of HSI hw'),
    s.field( "hsi_readout_period", self.count, default=1e3, doc='Real HSI hardware only: Period between HSI hardware polling [us]'),
    s.field( "control_hsi_hw", self.flag, default=false, doc='Flag to control whether we are controlling hsi hardware'),
    s.field( "hsi_endpoint_address", self.count, default=1, doc='Timing address of HSI endpoint'),
    s.field( "hsi_endpoint_partition", self.count, default=0, doc='Timing partition of HSI endpoint'),
    s.field( "hsi_re_mask",self.count, default=0, doc='Rising-edge trigger mask'),
    s.field( "hsi_fe_mask", self.count, default=0, doc='Falling-edge trigger mask'),
    s.field( "hsi_inv_mask",self.count, default=0, doc='Invert-edge mask'),
    s.field( "hsi_source",self.count, default=1, doc='HSI signal source; 0 - hardware, 1 - emulation (trigger timestamp bits)'),
    # fake hsi options
    s.field( "use_fake_hsi", self.flag, default=true, doc='Flag to control whether fake or real hardware HSI config is generated. Default is true'),
    s.field( "host_fake_hsi", self.host, default='localhost', doc='Host to run the HSI app on'),
    s.field( "hsi_device_id", self.count, default=0, doc='Fake HSI only: device ID of fake HSIEvents'),
    s.field( "mean_hsi_signal_multiplicity", self.count, default=1, doc='Fake HSI only: rate of individual HSI signals in emulation mode 1'),
    s.field( "hsi_signal_emulation_mode", self.count, default=0, doc='Fake HSI only: HSI signal emulation mode'),
    s.field( "enabled_hsi_signals", self.count, default=1, doc='Fake HSI only: bit mask of enabled fake HSI signals')
  ]),

};


moo.oschema.sort_select(cs)
