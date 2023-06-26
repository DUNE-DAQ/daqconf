// This is the configuration schema for daqconf_multiru_gen
//

local moo = import "moo.jsonnet";

local s = moo.oschema.schema("dunedaq.daqconf.dataflowgen");
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


  dataflowapp: s.record("dataflowapp",[
    s.field( "app_name", self.string, default="dataflow0"),
    s.field( "output_paths",self.paths, default=['.'], doc="Location(s) for the dataflow app to write data. Former -o"),
    s.field( "host_df", self.host, default='localhost'),
    s.field( "max_file_size",self.count, default=4*1024*1024*1024, doc="The size threshold when raw data files are closed (in bytes)"),
    s.field( "data_store_mode", self.string, default="all-per-file", doc="all-per-file or one-event-per-file"),
    s.field( "max_trigger_record_window",self.count, default=0, doc="The maximum size for the window of data that will included in a single TriggerRecord (in ticks). Readout windows that are longer than this size will result in TriggerRecords being split into a sequence of TRs. A zero value for this parameter means no splitting."),

  ], doc="Element of the dataflow.apps array"),

  dataflowapps: s.sequence("dataflowapps", self.dataflowapp, doc="List of dataflowapp instances"),

  dataflow: s.record("dataflow", [
    s.field( "host_dfo", self.host, default='localhost', doc="Sets the host for the DFO app"),
    s.field( "apps", self.dataflowapps, default=[], doc="Configuration for the dataflow apps (see dataflowapp for options)"),
    s.field( "token_count",self.count, default=10, doc="Number of tokens the dataflow apps give to the DFO. Former -c"),
    // Trigger 
    s.field( "host_tpw", self.host, default='localhost', doc='Host to run the TPWriter app on'),
    s.field( "enable_tpset_writing", self.flag, default=false, doc="Enable the writing of TPs to disk (only works with enable_tpg or enable_firmware_tpg)"),
    s.field( "tpset_output_path", self.path,default='.', doc="Output directory for TPSet stream files"),
    s.field( "tpset_output_file_size",self.count, default=4*1024*1024*1024, doc="The size threshold when TPSet stream files are closed (in bytes)"),
  ]),

};


moo.oschema.sort_select(cs)
