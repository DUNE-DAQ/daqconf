"""
Detector-Readout Stream MAP

BEWARE: Horrible things are done in this module, such that others don't have to suffer

Open questions:

- General vs specific validation (ETH, FLX) - delegate to spedific classes?
- Streams mapping to readout unit applications, consistency checks: delegate to a dedicated class?
"""
# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()

moo.otypes.load_types('daqconf/dromap.jsonnet')
moo.otypes.load_types('hdf5libs/hdf5rawdatafile.jsonnet')

import dunedaq.daqconf.dromap as dlm
import dunedaq.hdf5libs.hdf5rawdatafile as hdf5rdf

import collections
import json
import pathlib
import copy

from typing import Dict
from collections import namedtuple, defaultdict

import sys

from rich import print
from rich.table import Table


thismodule = sys.modules[__name__]

# Turn moo object into named tuples
for c in [
    hdf5rdf.GeoID,
    dlm.DROStreamEntry,
    dlm.EthStreamConf,
    dlm.FelixStreamConf,
]: 
    c_ost = c.__dict__['_ost']
    c_name = c_ost['name']
    setattr(thismodule, c_name, namedtuple(c_name, [f['name'] for f in c_ost['fields']]))



# # ROUnitID = namedtuple('ROUnitID', ['host_name', 'app_id', 'tech'])

# class ROUnitID:
#     """
#     """
    
#     def __init__(self, host_name, iface, tech):
#         self.host_name = host_name
#         self.iface = iface
#         self.tech = tech

#     def __repr__(self):
#         return f"ROUnitID({self.host_name}, {self.iface}, {self.tech})"
    

#     def __eq__(self, other):
#         return (
#             (self.host_name == other.host_name) and
#             (self.iface == other.iface) and 
#             (self.tech == other.tech) 
#         )
      
#     def __hash__(self):
#         return hash((self.host_name, self.iface, self.tech))  

#     @property
#     def safe_host_name(self):
#         return self.host_name.replace('-','')

#     @property
#     def label(self):
#         return f"{self.safe_host_name}{self.tech}{self.iface}"
    
class ReadoutUnitDescriptor:

    def __init__(self, host_name, iface, tech, det_id, streams):
        self.host_name = host_name
        self.iface = iface
        self.tech = tech
        self.det_id = det_id
        self.streams = streams

    @property
    def safe_host_name(self):
        return self.host_name.replace('-','')

    @property
    def label(self):
        return f"{self.safe_host_name}{self.tech}{self.iface}"
    
    @property
    def app_name(self):
        return f"ru{self.label}"
    
class DetReadoutMapService:
    """Detector - Readout Link mapping"""

    _tech_map =  {
        'flx': (FelixStreamConf, dlm.FelixStreamConf),
        'eth': (EthStreamConf, dlm.EthStreamConf),
    }

    _host_label_map = {
        'flx': 'host',
        'eth': 'rx_host',
    }

    _iflabel_map = {
        'flx': 'card',
        'eth': 'rx_iface',
    }

    def __init__(self):
        self._map = {}


    def load(self, map_path: str) -> None:
        
        map_fp = pathlib.Path(map_path)

        # Opening JSON file
        with open(map_fp) as f:
        
            # returns JSON object as 
            # a dictionary
            data = json.load(f)

        self._validate_json(data)
        
        streams = self._build_streams(data)

        self._validate_streams(streams)
        self._validate_eth(streams)
        self._validate_rohosts(streams)

        self._map = {s.src_id:s for s in streams}

    
    def _validate_json(self, data) -> None:

        # Make a copy to work locally
        data = copy.deepcopy(data)

        dro_links = []
        
        for e in data:

            info = e.pop('config')

            dro_en = dlm.DROStreamEntry(**e)
            
            _, tech_moo_t = self._tech_map[dro_en.tech]
            dro_en.config = tech_moo_t(**info)

            dro_links.append(dro_en)

        dlmap = dlm.DROStreamMap(dro_links)
        _ = dlmap.pod()

    
    def _build_streams(self, data) -> None:
        """Build a list of stream entries"""

        streams = []
        for s in data:

            tech_t, _ = self._tech_map[s['tech']]
            config = tech_t(**s['config'])

            s.update({
                'config':config,
                'geo_id':GeoID(**s['geo_id'])
            })
            en = DROStreamEntry(**s)
            streams.append(en)
        return streams
    
    def _validate_streams(self, streams):
        """Validates the list of stream entries"""

        src_id_list = [s.src_id for s in streams]
        geo_id_list = [s.geo_id for s in streams]

        # Ensure source id uniqueness
        dups_src_ids = [item for item, count in collections.Counter(src_id_list).items() if count > 1]
        if len(dups_src_ids):
            raise ValueError(f"Found duplicated source ids : {', '.join([str(i) for i in dups_srcids])}")
        
        # Ensure geo id uniqueness
        dups_geo_ids = [item for item, count in collections.Counter(geo_id_list).items() if count > 1]
        if len(dups_geo_ids):
            raise ValueError(f"Found duplicated geo ids : {', '.join([str(i) for i in dups_geo_ids])}")
        
        
    def _validate_rohosts(self, streams):
        # Check RU consistency, i.e. only one tech type per readout host
        host_label_map = {
            'flx': 'host',
            'eth': 'rx_host',
        }

        tech_m = defaultdict(set)
        det_id_m = defaultdict(set)
        for en in streams:
            ro_host = getattr(en.config, host_label_map[en.tech])
            tech_m[ro_host].add(en.tech)
            det_id_m[ro_host].add(en.geo_id.det_id)

        multi_tech_hosts = {k:v for k,v in tech_m.items() if len(v) > 1}
        if multi_tech_hosts:
            raise ValueError(f"Readout hosts with streams of different techs are not supported. Found {multi_tech_hosts}")

        multi_det_hosts = {k:v for k,v in det_id_m.items() if len(v) > 1}
        if multi_det_hosts:
            raise ValueError(f"Readout hosts with streams from different detectors are not supported. Found {multi_det_hosts}")
    
    # FIXME: Dedicated Ethernet Validator class?
    def _validate_eth(self, streams):
        """
        Apply rules:
        - ip and mac pairing is strict (one-to-one)
        - a mac can only belong to a single host
        """


        rx_mac_to_host = defaultdict(set)
        rx_mac_to_ip = defaultdict(set)
        rx_mac_to_iface = defaultdict(set)
        rx_ip_to_mac = defaultdict(set)

        tx_mac_to_host = defaultdict(set)
        tx_mac_to_ip = defaultdict(set)
        tx_ip_to_mac = defaultdict(set)

        for s in streams:
            if s.tech != 'eth':
                continue
            
            rx_mac_to_host[s.config.rx_mac].add(s.config.rx_host)
            rx_mac_to_ip[s.config.rx_mac].add(s.config.rx_ip)
            rx_mac_to_iface[s.config.rx_mac].add(s.config.rx_iface)
            rx_ip_to_mac[s.config.rx_ip].add(s.config.rx_mac)

            tx_mac_to_ip[s.config.tx_mac].add(s.config.tx_ip)
            tx_ip_to_mac[s.config.tx_ip].add(s.config.tx_mac)
            tx_mac_to_host[s.config.tx_mac].add(s.config.tx_host)


        dup_rx_hosts = { k:v for k,v in rx_mac_to_host.items() if len(v) > 1}
        dup_rx_macs = { k:v for k,v in rx_mac_to_ip.items() if len(v) > 1}
        dup_rx_iface = { k:v for k,v in rx_mac_to_iface.items() if len(v) > 1}
        dup_rx_ips = { k:v for k,v in rx_ip_to_mac.items() if len(v) > 1}

        dup_tx_hosts = { k:v for k,v in tx_mac_to_host.items() if len(v) > 1}
        dup_tx_macs = { k:v for k,v in tx_mac_to_ip.items() if len(v) > 1}
        dup_tx_ips = { k:v for k,v in tx_ip_to_mac.items() if len(v) > 1}
        

        errors = []
        if dup_rx_hosts:
            errors.append(f"Many rx hosts associated to the same rx mac {dup_rx_hosts}")
        if dup_rx_macs:
            errors.append(f"Many rx ips associated to the same rx mac {dup_rx_macs}")
        if dup_rx_iface:
            errors.append(f"Many rx interfaces associated to the same rx mac {dup_rx_iface}")
        if dup_rx_ips:
            errors.append(f"Many rx macs associated to the same rx ips {dup_rx_ips}")


        if dup_tx_hosts:
            errors.append(f"Many tx hosts associated to the same tx mac {dup_tx_hosts}")
        if dup_tx_macs:
            errors.append(f"Many tx macs associated to the same tx ips {dup_tx_macs}")
        if dup_tx_ips:
            errors.append(f"Many tx ips associated to the same tx mac {dup_tx_ips}")

        # FIXME : Create a dedicated exception
        if errors:
            nl = r'\n'
            raise RuntimeError(f"Ethernet streams validation failed: {nl.join(errors)}")

    @property
    def streams(self):
        return list(self._map.values())


    def get(self):
        return self._map


    def group_by_host(self) -> Dict:
        m = {}

        host_label_map = {
            'flx': 'host',
            'eth': 'rx_host',
        }

        for s in self._map.values():
            m.setdefault(getattr(s.config, host_label_map[s.tech]),[]).append(s)

        return m

    # # FIXME: This belongs to readout configuration. Should it be here?
    # def group_by_ro_unit(self) -> Dict:

    #     m = defaultdict(list)
    #     for s in self.streams:
    #         ru_host = getattr(s.config, self._host_label_map[s.tech])
    #         ru_iface = getattr(s.config, self._iflabel_map[s.tech])
    #         m[ROUnitID(ru_host, ru_iface, s.tech)].append(s)

    #     return dict(m)

    # FIXME: This belongs to readout configuration. Should it be here?
    def get_ru_descriptors(self) -> Dict:
        
        m = defaultdict(list)
        for s in self.streams:
            ru_host = getattr(s.config, self._host_label_map[s.tech])
            ru_iface = getattr(s.config, self._iflabel_map[s.tech])
            m[(ru_host, ru_iface, s.tech, s.geo_id.det_id)].append(s)

        # Repackage as a map of ReadoutUnitDescriptors
        rud_map = {}
        for (ru_host, ru_iface, tech, det_id),streams in m.items():
            d = ReadoutUnitDescriptor(ru_host, ru_iface, tech, det_id, streams)
            rud_map[d.app_name] = d

        return rud_map


    def get_by_tech(self, tech: str):
        return {
            k:v for k,v in self._map.items()
            if v.tech == tech
        }


    def get_src_ids(self):
        return list(self._map)


    def get_geo_ids(self):
        '''Return the list of GeoIDs in the map'''
        return [v.geo_id for v in self.streams]


    def get_src_geo_map(self):
        """Build the SrcGeoID map for HDF5RawDataFile"""
        return hdf5rdf.SrcGeoIDMap([
            hdf5rdf.SrcGeoIDEntry(
                src_id=s,
                geo_id=hdf5rdf.GeoID(**(en.geo_id._asdict()))
            ) for s,en in self._map.items()
        ])


    def as_table(self):
        """Export the table as a rich table"""
        m = self._map

        t = Table()
        t.add_column('src_id', style='blue')
        for f in GeoID._fields:
            t.add_column(f)
        t.add_column('tech')
        for f in FelixStreamConf._fields:
            t.add_column(f"flx_{f}", style='cyan')
        for f in EthStreamConf._fields:
            t.add_column(f"eth_{f}", style='magenta')

        for s,en in m.items():

            row = [str(s)]+[str(x) for x in en.geo_id]+[en.tech]

            if en.tech == "flx":
                infos = [str(x) for x in en.config]
                pads = ['-']*(len(t.columns)-len(row)-len(infos))
                row += infos + pads

            elif en.tech == "eth":
                infos = [str(x) for x in en.config]
                pads = ['-']*(len(t.columns)-len(row)-len(infos))
                row += pads + infos
                
            t.add_row(*row)
        
        return t
    

    def as_json(self):
        """Convert the map into a moo-json object"""
        m = self._map

        dro_seq = []
        for _,en in m.items():

            dro_en = dlm.DROStreamEntry()
            dro_en.src_id = en.src_id
            dro_en.tech = en.tech
            dro_en.geo_id = hdf5rdf.GeoID(**(en.geo_id._asdict()))

            _, tech_moo_t = self._tech_map[en.tech]
            dro_en.config = tech_moo_t(**(en.config._asdict()))

            dro_seq.append(dro_en)

        dlmap = dlm.DROStreamMap(dro_seq)
        return dlmap.pod()
    

    def remove_srcid(self, srcid):
        """Remove a source ID"""
        return self._map.pop(srcid)


    def add_srcid(self, src_id, geo_id, tech, **kwargs):
        """Add a new source id"""

        if src_id in self._map:
            raise KeyError(f"Source ID {src_id} is already present in the map")
        
        if geo_id in self.get_geo_ids():
            raise KeyError(f"Geo ID {geo_id} is already present in the map")


        tech_t, tech_moo_t = self._tech_map[tech]
        config = tech_t(**(tech_moo_t(**kwargs).pod()))


        s = DROStreamEntry(src_id=src_id, geo_id=geo_id, tech=tech, config=config)
        stream_list = list(self.streams)+[s]
        self._validate_streams(stream_list)
        self._validate_eth(stream_list)
        self._validate_rohosts(stream_list)
        self._map[src_id] = s
    