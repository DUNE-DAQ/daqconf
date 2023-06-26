// This is the configuration schema for daqconf_multiru_gen
//

local moo = import "moo.jsonnet";

local s = moo.oschema.schema("dunedaq.daqconf.readoutgen");
local nc = moo.oschema.numeric_constraints;
// A temporary schema construction context.
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


  data_file_entry: s.record("data_file_entry", [
    s.field( "data_file", self.path, default='./frames.bin', doc="File containing data frames to be replayed by the fake cards. Former -d. Uses the asset manager, can also be 'asset://checksum/somelonghash', or 'file://somewhere/frames.bin' or 'frames.bin'"),
    s.field( "detector_id", self.count, default=3, doc="Detector ID that this file applies to"),
  ]),
  data_files: s.sequence("data_files", self.data_file_entry),

  numa_exception:  s.record( "NUMAException", [
    s.field( "host", self.host, default='localhost', doc="Host of exception"),
    s.field( "card", self.count, default=0, doc="Card ID of exception"),
    s.field( "numa_id", self.count, default=0, doc="NUMA ID of exception"),
    s.field( "felix_card_id", self.count, default=-1, doc="CARD ID override, -1 indicates no override"),
    s.field( "latency_buffer_numa_aware", self.flag, default=false, doc="Enable NUMA-aware mode for the Latency Buffer"),
    s.field( "latency_buffer_preallocation", self.flag, default=false, doc="Enable Latency Buffer preallocation"),
  ], doc="Exception to the default NUMA ID for FELIX cards"),

  numa_exceptions: s.sequence( "NUMAExceptions", self.numa_exception, doc="Exceptions to the default NUMA ID"),
    
  numa_config: s.record("numa_config", [
    s.field( "default_id", self.count, default=0, doc="Default NUMA ID for FELIX cards"),
    s.field( "default_latency_numa_aware", self.flag, default=false, doc="Default for Latency Buffer NUMA awareness"),
    s.field( "default_latency_preallocation", self.flag, default=false, doc="Default for Latency Buffer Preallocation"),
    s.field( "exceptions", self.numa_exceptions, default=[], doc="Exceptions to the default NUMA ID"),
  ]),

  readout: s.record("readout", [
    s.field( "detector_readout_map_file", self.path, default='./DetectorReadoutMap.json', doc="File containing detector hardware map for configuration to run"),
    s.field( "use_fake_data_producers", self.flag, default=false, doc="Use fake data producers that respond with empty fragments immediately instead of (fake) cards and DLHs"),
    // s.field( "memory_limit_gb", self.count, default=64, doc="Application memory limit in GB")
    // Fake cards
    s.field( "use_fake_cards", self.flag, default=false, doc="Use fake cards"),
    s.field( "emulated_data_times_start_with_now", self.flag, default=false, doc="If active, the timestamp of the first emulated data frame is set to the current wallclock time"),
    s.field( "default_data_file", self.path, default='asset://?label=ProtoWIB&subsystem=readout', doc="File containing data frames to be replayed by the fake cards. Former -d. Uses the asset manager, can also be 'asset://?checksum=somelonghash', or 'file://somewhere/frames.bin' or 'frames.bin'"),
    s.field( "data_files", self.data_files, default=[], doc="Files to use by detector type"),
    // DPDK
    s.field( "dpdk_eal_args", self.string, default='-l 0-1 -n 3 -- -m [0:1].0 -j', doc='Args passed to the EAL in DPDK'),
    s.field( "dpdk_rxqueues_per_lcore", self.count, default=1, doc='Number of rx queues per core'),
    // FLX
    s.field( "numa_config", self.numa_config, default=self.numa_config, doc='Configuration of FELIX NUMA IDs'),
    // DLH
    s.field( "emulator_mode", self.flag, default=false, doc="If active, timestamps of data frames are overwritten when processed by the readout. This is necessary if the felix card does not set correct timestamps. Former -e"),
    s.field( "thread_pinning_file", self.path, default="", doc="A thread pinning configuration file that gets executed after conf."),
    // s.field( "data_rate_slowdown_factor",self.count, default=1, doc="Factor by which to suppress data generation. Former -s"),
    s.field( "latency_buffer_size", self.count, default=499968, doc="Size of the latency buffers (in number of elements)"),
    s.field( "fragment_send_timeout_ms", self.count, default=10, doc="The send timeout that will be used in the readout modules when sending fragments downstream (i.e. to the TRB)."),
    s.field( "enable_tpg", self.flag, default=false, doc="Enable TPG"),
    s.field( "tpg_threshold", self.count, default=120, doc="Select TPG threshold"),
    s.field( "tpg_algorithm", self.string, default="SimpleThreshold", doc="Select TPG algorithm (SimpleThreshold, AbsRS)"),
    s.field( "tpg_channel_mask", self.channel_list, default=[], doc="List of offline channels to be masked out from the TPHandler"),
    s.field( "enable_raw_recording", self.flag, default=false, doc="Add queues and modules necessary for the record command"),
    s.field( "raw_recording_output_dir", self.path, default='.', doc="Output directory where recorded data is written to. Data for each link is written to a separate file")
  ]),

};

moo.oschema.sort_select(cs)
