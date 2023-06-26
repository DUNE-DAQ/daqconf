// This is the configuration schema for daqconf_multiru_gen
//

local moo = import "moo.jsonnet";

local s = moo.oschema.schema("dunedaq.daqconf.bootgen");
local nc = moo.oschema.numeric_constraints;

local cs = {
  port:            s.number(   "Port", "i4", doc="A TCP/IP port number"),
  count:           s.number(   "count", "i8", doc="A count of things"),
  flag:            s.boolean(  "Flag", doc="Parameter that can be used to enable or disable functionality"),
  monitoring_dest: s.enum(     "MonitoringDest", ["local", "cern", "pocket"]),
  path:            s.string(   "Path", doc="Location on a filesystem"),
  paths:           s.sequence( "Paths",         self.path, doc="Multiple paths"),
  host:            s.string(   "Host",          moo.re.dnshost, doc="A hostname"),
  hosts:           s.sequence( "Hosts",         self.host, "Multiple hosts"),
  string:          s.string(   "Str",           doc="Generic string"),
  strings:         s.sequence( "Strings",  self.string, doc="List of strings"),
  tpg_channel_map: s.enum(     "TPGChannelMap", ["VDColdboxChannelMap", "ProtoDUNESP1ChannelMap", "PD2HDChannelMap", "HDColdboxChannelMap"]),
  readout_time:    s.number(   "ROTime",        "i8", doc="A readout time in ticks"),
  pm_choice:       s.enum(     "PMChoice", ["k8s", "ssh"], doc="Process Manager choice: ssh or Kubernetes"),
  rte_choice:      s.enum(     "RTEChoice", ["auto", "release", "devarea"], doc="Kubernetes DAQ application RTE choice"),
  


  boot: s.record("boot", [
    // s.field( "op_env", self.string, default='swtest', doc="Operational environment - used for raw data filename prefix and HDF5 Attribute inside the files"),
    s.field( "base_command_port", self.port, default=3333, doc="Base port of application command endpoints"),

    # Obscure
    s.field( "capture_env_vars", self.strings, default=['TIMING_SHARE', 'DETCHANNELMAPS_SHARE'], doc="List of variables to capture from the environment"),
    s.field( "disable_trace", self.flag, false, doc="Do not enable TRACE (default TRACE_FILE is /tmp/trace_buffer_${HOSTNAME}_${USER})"),
    s.field( "opmon_impl", self.monitoring_dest, default='local', doc="Info collector service implementation to use"),
    s.field( "ers_impl", self.monitoring_dest, default='local', doc="ERS destination (Kafka used for cern and pocket)"),
    s.field( "pocket_url", self.host, default='127.0.0.1', doc="URL for connecting to Pocket services"),
    s.field( "process_manager", self.pm_choice, default="ssh", doc="Choice of process manager"),

    # K8S
    s.field( "k8s_image", self.string, default="dunedaq/c8-minimal", doc="Which docker image to use"),
    s.field( "k8s_rte", self.rte_choice, default="auto", doc="0 - Use an RTE script if not in a dev environment, 1 - Always use RTE, 2 - never use RTE"),

    # Connectivity Service
    s.field( "use_connectivity_service", self.flag, default=true, doc="Whether to use the ConnectivityService to manage connections"),
    s.field( "start_connectivity_service", self.flag, default=true, doc="Whether to use the ConnectivityService to manage connections"),
    s.field( "connectivity_service_threads", self.count, default=2, doc="Number of threads for the gunicorn server that serves connection info"),
    s.field( "connectivity_service_host", self.host, default='localhost', doc="Hostname for the ConnectivityService"),
    s.field( "connectivity_service_port", self.port, default=15000, doc="Port for the ConnectivityService"),
    s.field( "connectivity_service_interval", self.count, default=1000, doc="Publish interval for the ConnectivityService")
    ]),
};


moo.oschema.sort_select(cs)
