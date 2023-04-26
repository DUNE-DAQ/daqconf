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

from collections import namedtuple

import sys

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


class DROMapService:
    """Detector - Readout Link mapping"""

    def __init__(self):
        self._map = {}


    def load(self, map_path: str):
        
        map_fp = pathlib.Path(map_path)

        # Opening JSON file
        with open(map_fp) as f:
        
            # returns JSON object as 
            # a dictionary
            data = json.load(f)

        self.validate(data)
        self.build(data)

    
    def validate(self, data):

        # Make a copy to work locally
        data = copy.deepcopy(data)

        dro_links = []
        srcid_list = []
        geoid_list = []
        
        for e in data:

            srcid_list.append(e['src_id'])
            geoid_list.append(GeoID(**e['geo_id']))
            info = e.pop('config')

            dro_en = dlm.DROStreamEntry(**e)

            if dro_en.tech == "flx":
                dro_en.config = dlm.FelixStreamConf(**info)
            elif dro_en.tech == "eth":
                dro_en.config = dlm.EthStreamConf(**info)

            dro_links.append(dro_en)

        dlmap = dlm.DROStreamMap(dro_links)
        _ = dlmap.pod()

        dups_srcids = [item for item, count in collections.Counter(srcid_list).items() if count > 1]
        if len(dups_srcids):
            raise ValueError(f"Found duplicated source ids : {', '.join([str(i) for i in dups_srcids])}")

        dups_geoids = [item for item, count in collections.Counter(geoid_list).items() if count > 1]
        if len(dups_geoids):
            raise ValueError(f"Found duplicated source ids : {', '.join([str(i) for i in dups_geoids])}")

    
    def build(self, data):

        self._map = {}
        for e in data:

            tech = e['tech']
            config = None

            if tech == "flx":
                config = FelixStreamConf(**e['config'])
            elif tech == "eth":
                config = EthStreamConf(**e['config'])
                

            e.update({
                'config':config,
                'geo_id':GeoID(**e['geo_id'])
            })
            en = DROStreamEntry(**e)
            self._map[en.src_id] = en


    def get(self):
        return self._map


    def get_by_type(self, type: str):

        return {
            k:v for k,v in self._map.items()
            if v.tech == type
        }
    
    def get_src_ids(self):
        return list(self._map)

    def get_geo_ids(self):
        return [v.geo_id for v in self._map.values()]


    def as_table(self):
        m = self._map
        # cols = ['src_id'] + list(GeoID._fields) + ['tech'] + [f"eth_{f}" for f in FelixStreamConf._fields] + [f"eth_{f}" for f in EthStreamConf._fields]

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
        m = self._map

        dro_seq = []
        for _,en in m.items():

            dro_en = dlm.DROStreamEntry()
            dro_en.src_id = en.src_id
            dro_en.tech = en.tech
            dro_en.geo_id = hdf5rdf.GeoID(**(en.geo_id._asdict()))

            if en.tech == 'flx':
                dro_en.config = dlm.FelixStreamConf(**(en.config._asdict()))
            elif en.tech == 'eth':
                dro_en.config = dlm.EthStreamConf(**(en.config._asdict()))
            dro_seq.append(dro_en)

        dlmap = dlm.DROStreamMap(dro_seq)
        return dlmap.pod()
    

    def remove_srcid(self, srcid):
        return self._map.pop(srcid)


    def add_srcid(self, src_id, geo_id, tech, **kwargs):

        if src_id in self._map:
            raise KeyError(f"Source ID {src_id} is already present in the map")
        
        if geo_id in self.get_geo_ids():
            raise KeyError(f"Geo ID {geo_id} is already present in the map")



        if tech == 'flx':
            config = FelixStreamConf(**(dlm.FelixStreamConf(**kwargs).pod()))
        elif tech == 'eth':
            config = EthStreamConf(**(dlm.EthStreamConf(**kwargs).pod()))
        else:
            print(f"What the tech {tech}")

        self._map[src_id] = DROStreamEntry(src_id=src_id, geo_id=geo_id, tech=tech, config=config)