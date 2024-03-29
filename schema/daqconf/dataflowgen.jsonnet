// This is the configuration schema for fddaqconf_gen or nddaqconf_gen
//

local moo = import "moo.jsonnet";

local stypes = import "daqconf/types.jsonnet";
local types = moo.oschema.hier(stypes).dunedaq.daqconf.types;

local s = moo.oschema.schema("dunedaq.daqconf.dataflowgen");
local nc = moo.oschema.numeric_constraints;

local cs = {

  dataflowapp: s.record("dataflowapp",[
    s.field( "app_name", types.string, default="dataflow0"),
    s.field( "output_paths",types.paths, default=['.'], doc="Location(s) for the dataflow app to write data. Former -o"),
    s.field( "host_df", types.host, default='localhost'),
    s.field( "max_file_size",types.count, default=4*1024*1024*1024, doc="The size threshold when raw data files are closed (in bytes)"),
    s.field( "data_store_mode", types.string, default="all-per-file", doc="all-per-file or one-event-per-file"),
    s.field( "max_trigger_record_window",types.count, default=0, doc="The maximum size for the window of data that will included in a single TriggerRecord (in ticks). Readout windows that are longer than this size will result in TriggerRecords being split into a sequence of TRs. A zero value for this parameter means no splitting."),

  ], doc="Element of the dataflow.apps array"),

  dataflowapps: s.sequence("dataflowapps", self.dataflowapp, doc="List of dataflowapp instances"),

  dataflow: s.record("dataflow", [
    s.field( "host_dfo", types.host, default='localhost', doc="Sets the host for the DFO app"),
    s.field( "apps", self.dataflowapps, default=[], doc="Configuration for the dataflow apps (see dataflowapp for options)"),
    s.field( "token_count",types.count, default=10, doc="Number of tokens the dataflow apps give to the DFO. Former -c"),
    // Trigger 
    s.field( "host_tpw", types.host, default='localhost', doc='Host to run the TPWriter app on'),
    s.field( "enable_tpset_writing", types.flag, default=false, doc="Enable the writing of TPs to disk (only works with enable_tpg or enable_firmware_tpg)"),
    s.field( "tpset_output_path", types.path,default='.', doc="Output directory for TP Stream files"),
    s.field( "tpset_output_file_size",types.count, default=4*1024*1024*1024, doc="The size threshold when TP Stream files are closed (in bytes)"),
    s.field("tp_accumulation_interval_ticks", types.count, 62500000, doc="Size of the TP accumulation window in the TP Stream writer, measured in clock ticks"),
    s.field("tp_accumulation_inactivity_time_before_write_sec", types.float4, 1.0,
            doc="Amount of time in which there must be no new data arriving at the TP Stream writer before a given time slice is written out"),
  ]),

};


stypes + moo.oschema.sort_select(cs)
