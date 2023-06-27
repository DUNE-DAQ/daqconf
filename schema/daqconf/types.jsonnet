// This is the configuration schema for daqconf_multiru_gen
//

local moo = import "moo.jsonnet";

local s = moo.oschema.schema("dunedaq.daqconf.types");
local nc = moo.oschema.numeric_constraints;
// A temporary schema construction context.

local cs = {
  port:   s.number(   "port",    "i4",           doc="A TCP/IP port number"),
  freq:   s.number(   "freq",    "u4",           doc="A frequency"),
  rate:   s.number(   "rate",    "f8",           doc="A rate as a double"),
  count:  s.number(   "count",   "i8",           doc="A count of things"),
  flag:   s.boolean(  "flag",                    doc="Parameter that can be used to enable or disable functionality"),
  path:   s.string(   "path",                    doc="Location on a filesystem"),
  paths:  s.sequence( "paths",   self.path,      doc="Multiple paths"),
  string: s.string(   "string",                  doc="Generic string"),
  strings:s.sequence( "strings", self.string,    doc="List of strings"),
  host:   s.string(   "host",    moo.re.dnshost, doc="A hostname"),
  hosts:  s.sequence( "hosts",   self.host,      doc="A collection of host names"),
  ipv4:   s.string(   "ipv4",    pattern=moo.re.ipv4, doc="ipv4 string"),
  mac:    s.string(   "mac",     pattern="^[a-fA-F0-9]{2}(:[a-fA-F0-9]{2}){5}$", doc="mac string"),
};

// Output a topologically sorted array.
moo.oschema.sort_select(cs)
