// This is the configuration schema for daqconf_multiru_gen
//

local moo = import "moo.jsonnet";

local sctb = import "ctbmodules/ctbmodule.jsonnet";
local ctbmodule = moo.oschema.hier(sctb).dunedaq.ctbmodules.ctbmodule;

local s = moo.oschema.schema("dunedaq.daqconf.confgen");
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
  pm_kind:         s.enum(     "PMKind", ["k8s", "ssh"]),
  


  boot: s.record("boot", [
    s.field( "op_env", self.string, default='swtest', doc="Operational environment - used for raw data filename prefix and HDF5 Attribute inside the files"),
    s.field( "base_command_port", self.port, default=3333, doc="Base port of application command endpoints"),

    # Obscure
    s.field( "RTE_script_settings", self.three_choice, default=0, doc="0 - Use an RTE script iff not in a dev environment, 1 - Always use RTE, 2 - never use RTE"),
    s.field( "capture_env_vars", self.strings, default=['TIMING_SHARE', 'DETCHANNELMAPS_SHARE'], doc="List of variables to capture from the environment"),
    s.field( "disable_trace", self.flag, false, doc="Do not enable TRACE (default TRACE_FILE is /tmp/trace_buffer_${HOSTNAME}_${USER})"),
    s.field( "opmon_impl", self.monitoring_dest, default='local', doc="Info collector service implementation to use"),
    s.field( "ers_impl", self.monitoring_dest, default='local', doc="ERS destination (Kafka used for cern and pocket)"),
    s.field( "pocket_url", self.host, default='127.0.0.1', doc="URL for connecting to Pocket services"),
    s.field( "process_manager", self.pm_kind, default="ssh", doc="Choice of process manager"),

    # K8S
    s.field( "image", self.string, default="dunedaq/c8-minimal", doc="Which docker image to use"),

    # Connectivity Service
    s.field( "use_connectivity_service", self.flag, default=true, doc="Whether to use the ConnectivityService to manage connections"),
    s.field( "start_connectivity_service", self.flag, default=true, doc="Whether to use the ConnectivityService to manage connections"),
    s.field( "connectivity_service_threads", self.count, default=2, doc="Number of threads for the gunicorn server that serves connection info"),
    s.field( "connectivity_service_host", self.host, default='localhost', doc="Hostname for the ConnectivityService"),
    s.field( "connectivity_service_port", self.port, default=15000, doc="Port for the ConnectivityService"),
    s.field( "connectivity_service_interval", self.count, default=1000, doc="Publish interval for the ConnectivityService"),
    
    # To move away
    s.field( "use_data_network", self.flag, default = false, doc="Whether to use the data network (Won't work with k8s)"),
    s.field( "data_request_timeout_ms", self.count, default=1000, doc="The baseline data request timeout that will be used by modules in the Readout and Trigger subsystems (i.e. any module that produces data fragments). Downstream timeouts, such as the trigger-record-building timeout, are derived from this."),
  ]),




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

  ctb_hsi: s.record("ctb_hsi", [
    # ctb options
    s.field( "use_ctb_hsi", self.flag, default=false, doc='Flag to control whether CTB HSI config is generated. Default is false'),
    s.field( "host_ctb_hsi", self.host, default='localhost', doc='Host to run the HSI app on'),
    s.field( "hlt_triggers", ctbmodule.Hlt_trigger_seq, []),
    s.field( "beam_llt_triggers", ctbmodule.Llt_mask_trigger_seq, []),
    s.field( "crt_llt_triggers", ctbmodule.Llt_count_trigger_seq, []),
    s.field( "pds_llt_triggers", ctbmodule.Llt_count_trigger_seq, []),
    s.field( "fake_trig_1", ctbmodule.Randomtrigger, ctbmodule.Randomtrigger),
    s.field( "fake_trig_2", ctbmodule.Randomtrigger, ctbmodule.Randomtrigger)
  ]),

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
    s.field( "emulator_mode", self.flag, default=false, doc="If active, timestamps of data frames are overwritten when processed by the readout. This is necessary if the felix card does not set correct timestamps. Former -e"),
    s.field( "thread_pinning_file", self.path, default="", doc="A thread pinning configuration file that gets executed after conf."),
    s.field( "data_rate_slowdown_factor",self.count, default=1, doc="Factor by which to suppress data generation. Former -s"),
    s.field( "clock_speed_hz", self.freq, default=62500000),
    s.field( "default_data_file", self.path, default='asset://?label=ProtoWIB&subsystem=readout', doc="File containing data frames to be replayed by the fake cards. Former -d. Uses the asset manager, can also be 'asset://?checksum=somelonghash', or 'file://somewhere/frames.bin' or 'frames.bin'"),
    s.field( "data_files", self.data_files, default=[], doc="Files to use by detector type"),
    s.field( "use_fake_cards", self.flag, default=false, doc="Use fake cards"),
    s.field( "latency_buffer_size", self.count, default=499968, doc="Size of the latency buffers (in number of elements)"),
    s.field( "fragment_send_timeout_ms", self.count, default=10, doc="The send timeout that will be used in the readout modules when sending fragments downstream (i.e. to the TRB)."),
    s.field( "enable_tpg", self.flag, default=false, doc="Enable TPG"),
    s.field( "tpg_threshold", self.count, default=120, doc="Select TPG threshold"),
    s.field( "tpg_algorithm", self.string, default="SWTPG", doc="Select TPG algorithm (SWTPG, AbsRS)"),
    s.field( "tpg_channel_mask", self.channel_list, default=[], doc="List of offline channels to be masked out from the TPHandler"),
    s.field( "enable_raw_recording", self.flag, default=false, doc="Add queues and modules necessary for the record command"),
    s.field( "raw_recording_output_dir", self.path, default='.', doc="Output directory where recorded data is written to. Data for each link is written to a separate file"),
    s.field( "host_dpdk_reader", self.hosts, default=['np04-srv-022'], doc="Which host to use to receive frames"),
    s.field( "eal_args", self.string, default='-l 0-1 -n 3 -- -m [0:1].0 -j', doc='Args passed to the EAL in DPDK'),
    s.field( "base_source_ip", self.string, default='10.73.139.', doc='First part of the IP of the source'),
    s.field( "destination_ip", self.string, default='10.73.139.17', doc='IP of the destination'),
    s.field( "numa_config", self.numa_config, default=self.numa_config, doc='Configuration of FELIX NUMA IDs'),
    s.field( "emulated_data_times_start_with_now", self.flag, default=false, doc="If active, the timestamp of the first emulated data frame is set to the current wallclock time"),
  ]),

  trigger_algo_config: s.record("trigger_algo_config", [
    s.field("prescale", self.count, default=100),
    s.field("window_length", self.count, default=10000),
    s.field("adjacency_threshold", self.count, default=6),
    s.field("adj_tolerance", self.count, default=4),
    s.field("trigger_on_adc", self.flag, default=false),
    s.field("trigger_on_n_channels", self.flag, default=false),
    s.field("trigger_on_adjacency", self.flag, default=true),
    s.field("adc_threshold", self.count, default=10000),
    s.field("n_channels_threshold", self.count, default=8),
    s.field("print_tp_info", self.flag, default=false),
  ]),

  c0_readout: s.record("c0_readout", [
    s.field("candidate_type", self.tc_type,      default=0,     doc="The TC type, 0=Unknown"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c1_readout: s.record("c1_readout", [
    s.field("candidate_type", self.tc_type,      default=1,     doc="The TC type, 1=Timing"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c2_readout: s.record("c2_readout", [
    s.field("candidate_type", self.tc_type,      default=2,     doc="The TC type, 2=TPCLowE"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c3_readout: s.record("c3_readout", [
    s.field("candidate_type", self.tc_type,      default=3,     doc="The TC type, 3=Supernova"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c4_readout: s.record("c4_readout", [
    s.field("candidate_type", self.tc_type,      default=4,     doc="The TC type, 4=Random"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c5_readout: s.record("c5_readout", [
    s.field("candidate_type", self.tc_type,      default=5,     doc="The TC type, 5=Prescale"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c6_readout: s.record("c6_readout", [
    s.field("candidate_type", self.tc_type,      default=6,     doc="The TC type, 6=ADCSimpleWindow"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c7_readout: s.record("c7_readout", [
    s.field("candidate_type", self.tc_type,      default=7,     doc="The TC type, 7=HorizontalMuon"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c8_readout: s.record("c8_readout", [
    s.field("candidate_type", self.tc_type,      default=8,     doc="The TC type, 8=MichelElectron"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),
  c9_readout: s.record("c9_readout", [
    s.field("candidate_type", self.tc_type,      default=9,     doc="The TC type, 9=LowEnergyEvent"),
    s.field("time_before",    self.readout_time, default=1000, doc="Time to readout before TC time [ticks]"),
    s.field("time_after",     self.readout_time, default=1001, doc="Time to readout after TC time [ticks]"),
  ]),

  tc_readout_map: s.record("tc_readout_map", [
    s.field("c0", self.c0_readout, default=self.c0_readout, doc="TC readout for TC type 0"),
    s.field("c1", self.c1_readout, default=self.c1_readout, doc="TC readout for TC type 1"),
    s.field("c2", self.c2_readout, default=self.c2_readout, doc="TC readout for TC type 2"),
    s.field("c3", self.c3_readout, default=self.c3_readout, doc="TC readout for TC type 3"),
    s.field("c4", self.c4_readout, default=self.c4_readout, doc="TC readout for TC type 4"),
    s.field("c5", self.c5_readout, default=self.c5_readout, doc="TC readout for TC type 5"),
    s.field("c6", self.c6_readout, default=self.c6_readout, doc="TC readout for TC type 6"),
    s.field("c7", self.c7_readout, default=self.c7_readout, doc="TC readout for TC type 7"),
    s.field("c8", self.c8_readout, default=self.c8_readout, doc="TC readout for TC type 8"),
    s.field("c9", self.c9_readout, default=self.c9_readout, doc="TC readout for TC type 9"),
  ]),

  trigger: s.record("trigger",[
    s.field( "trigger_rate_hz", self.rate, default=1.0, doc='Fake HSI only: rate at which fake HSIEvents are sent. 0 - disable HSIEvent generation. Former -t'),
    s.field( "trigger_window_before_ticks",self.count, default=1000, doc="Trigger window before marker. Former -b"),
    s.field( "trigger_window_after_ticks", self.count, default=1000, doc="Trigger window after marker. Former -a"),
    s.field( "host_trigger", self.host, default='localhost', doc='Host to run the trigger app on'),
    s.field( "host_tpw", self.host, default='localhost', doc='Host to run the TPWriter app on'),
    # trigger options
    s.field( "completeness_tolerance", self.count, default=1, doc="Maximum number of inactive queues we will tolerate."),
    s.field( "tolerate_incompleteness", self.flag, default=false, doc="Flag to tell trigger to tolerate inactive queues."),
    s.field( "ttcm_s1", self.count,default=1, doc="Timing trigger candidate maker accepted HSI signal ID 1"),
    s.field( "ttcm_s2", self.count, default=2, doc="Timing trigger candidate maker accepted HSI signal ID 2"),
    s.field( "trigger_activity_plugin", self.string, default='TriggerActivityMakerPrescalePlugin', doc="Trigger activity algorithm plugin"),
    s.field( "trigger_activity_config", self.trigger_algo_config, default=self.trigger_algo_config,doc="Trigger activity algorithm config (string containing python dictionary)"),
    s.field( "trigger_candidate_plugin", self.string, default='TriggerCandidateMakerPrescalePlugin', doc="Trigger candidate algorithm plugin"),
    s.field( "trigger_candidate_config", self.trigger_algo_config, default=self.trigger_algo_config, doc="Trigger candidate algorithm config (string containing python dictionary)"),
    s.field( "hsi_trigger_type_passthrough", self.flag, default=false, doc="Option to override trigger type in the MLT"),
    s.field( "enable_tpset_writing", self.flag, default=false, doc="Enable the writing of TPs to disk (only works with enable_tpg or enable_firmware_tpg)"),
    s.field( "tpset_output_path", self.path,default='.', doc="Output directory for TPSet stream files"),
    s.field( "tpset_output_file_size",self.count, default=4*1024*1024*1024, doc="The size threshold when TPSet stream files are closed (in bytes)"),
    s.field( "tpg_channel_map", self.tpg_channel_map, default="ProtoDUNESP1ChannelMap", doc="Channel map for TPG"),
    s.field( "mlt_merge_overlapping_tcs", self.flag, default=true, doc="Option to turn off merging of overlapping TCs when forming TDs in MLT"),
    s.field( "mlt_buffer_timeout", self.count, default=100, doc="Timeout (buffer) to wait for new overlapping TCs before sending TD"),
    s.field( "mlt_send_timed_out_tds", self.flag, default=true, doc="Option to drop TD if TC comes out of timeout window"),
    s.field( "mlt_max_td_length_ms", self.count, default=1000, doc="Maximum allowed time length [ms] for a readout window of a single TD"),
    s.field( "mlt_ignore_tc", self.tc_types, default=[], doc="Optional list of TC types to be ignored in MLT"),
    s.field( "mlt_use_readout_map", self.flag, default=false, doc="Option to use custom readout map in MLT"),
    s.field( "mlt_td_readout_map", self.tc_readout_map, default=self.tc_readout_map, doc="The readout windows assigned to TDs in MLT, based on TC type."),
    s.field( "use_custom_maker", self.flag, default=false, doc="Option to use a Custom Trigger Candidate Maker (plugin)"),
    s.field( "ctcm_trigger_types", self.tc_types, default=[4], doc="Optional list of TC types to be used by the Custom Trigger Candidate Maker (plugin)"),
    s.field( "ctcm_trigger_intervals", self.tc_intervals, default=[10000000], doc="Optional list of intervals (clock ticks) for the TC types to be used by the Custom Trigger Candidate Maker (plugin)"),
  ]),

  dataflowapp: s.record("dataflowapp",[
    s.field("app_name", self.string, default="dataflow0"),
    s.field( "output_paths",self.paths, default=['.'], doc="Location(s) for the dataflow app to write data. Former -o"),
    s.field( "host_df", self.host, default='localhost'),
    s.field( "max_file_size",self.count, default=4*1024*1024*1024, doc="The size threshold when raw data files are closed (in bytes)"),
    s.field( "data_store_mode", self.string, default="all-per-file", doc="all-per-file or one-event-per-file"),
    s.field( "max_trigger_record_window",self.count, default=0, doc="The maximum size for the window of data that will included in a single TriggerRecord (in ticks). Readout windows that are longer than this size will result in TriggerRecords being split into a sequence of TRs. A zero value for this parameter means no splitting."),

  ], doc="Element of the dataflow.apps array"),
  dataflowapps: s.sequence("dataflowapps", self.dataflowapp, doc="List of dataflowapp instances"),

  dataflow: s.record("dataflow", [
    s.field( "host_dfo", self.host, default='localhost', doc="Sets the host for the DFO app"),
    s.field("apps", self.dataflowapps, default=[], doc="Configuration for the dataflow apps (see dataflowapp for options)"),
    s.field( "token_count",self.count, default=10, doc="Number of tokens the dataflow apps give to the DFO. Former -c"),
  ]),

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

  dpdk_sender: s.record("dpdk_sender", [
      s.field( "enable_dpdk_sender", self.flag, default=false, doc="Enable sending frames using DPDK"),
      s.field( "host_dpdk_sender", self.hosts, default=['np04-srv-021'], doc="Which host to use to send frames"),
      s.field( "eal_args", self.string, default='-l 0-1 -n 3 -- -m [0:1].0 -j', doc='Args passed to the EAL in DPDK'),
  ]),

  daqconf_multiru_gen: s.record('daqconf_multiru_gen', [
    s.field('boot',     self.boot,    default=self.boot,      doc='Boot parameters'),
    s.field('dataflow', self.dataflow, default=self.dataflow, doc='Dataflow paramaters'),
    s.field('dqm',      self.dqm,      default=self.dqm,      doc='DQM parameters'),
    s.field('hsi',      self.hsi,      default=self.hsi,      doc='HSI parameters'),
    s.field('ctb_hsi',  self.ctb_hsi,  default=self.ctb_hsi,  doc='CTB parameters'),
    s.field('readout',  self.readout,  default=self.readout,  doc='Readout parameters'),
    s.field('timing',   self.timing,   default=self.timing,   doc='Timing parameters'),
    s.field('trigger',  self.trigger,  default=self.trigger,  doc='Trigger parameters'),
    s.field('dpdk_sender', self.dpdk_sender, default=self.dpdk_sender, doc='DPDK sender parameters'),
  ]),

};

// Output a topologically sorted array.
sctb + moo.oschema.sort_select(cs)
