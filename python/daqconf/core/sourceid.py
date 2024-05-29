# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()
from rich.console import Console
from enum import Enum
from collections import namedtuple, defaultdict

from .console import console


from daqdataformats import SourceID
from detchannelmaps import *
from detdataformats import DetID

TAID = namedtuple('TAID', ['detector', 'crate', 'plane'])
TPID = namedtuple('TPID', ['detector', 'crate', 'plane'])
#FWTPID = namedtuple('FWTPID', ['host', 'card', 'slr'])
#FWTPOUTID = namedtuple('FWTPOUTID', ['host', 'card', 'fwtpid'])

class RUEndpointInfo:
    def __init__(self, ru_desc=None, plane=None):
        self.ru_desc = ru_desc
        self.plane = plane

class TPInfo:
    def __init__(self):
        self.region_id = 0
        self.plane_id = 0
        self.tp_ru_sid = 0
        self.link_count = 0

class TAInfo:
    def __init__(self):
        self.region_id = 0
        self.plane_id = 0
        self.link_count = 0

class TCInfo:
    def __init__(self):
        self.ru_count = 0

class SourceIDBroker:


    def __init__(self):
        self.sourceid_map = {}
        self.debug: bool = False

    def get_next_source_id(self, subsystem, start_id = 0):
        while self.source_id_exists(subsystem, start_id):
            start_id += 1
        if self.debug: console.log(f"Returning {start_id} from get_next_source_id for subsystem {subsystem}")
        return start_id

    def get_all_source_ids(self, subsystem):
        if subsystem in self.sourceid_map:
            if self.debug: console.log(f"Returning {len(self.sourceid_map[subsystem])} SourceIDs for subsystem {subsystem}")
            return self.sourceid_map[subsystem]

        if self.debug: console.log(f"Subsystem {subsystem} not in sourceid_map")
        return {}

    def source_id_exists(self, subsystem, sid):
        if subsystem in self.sourceid_map:
            return sid in self.sourceid_map[subsystem]
        return False

    def register_source_id(self, subsystem, sid, info):
        if self.debug: console.log(f"Going to register Source ID {sid} for Subsystem {subsystem} with info object {info}")
        if not subsystem in self.sourceid_map:
            self.sourceid_map[subsystem] = {}
        if not self.source_id_exists(subsystem, sid):
            self.sourceid_map[subsystem][sid] = info
        else:
            raise ValueError(f"SourceID {sid} already exists for Subsystem {subsystem}!")

    def register_readout_source_ids(self, dro_streams):
        if self.debug: console.log(f"Registering {len(dro_streams)} Detector-Readout Source IDs ")
        for stream in dro_streams:
            if not self.source_id_exists("Detector_Readout", stream.src_id):
                self.register_source_id("Detector_Readout", stream.src_id, [stream])
            else:
                self.sourceid_map["Detector_Readout"][stream.src_id].append(stream)


    def generate_trigger_source_ids(self, ru_descrs, tp_mode: bool):
        tc_info = TCInfo()
        ta_infos = {}
        tp_infos = {}
        # dro_sids = self.get_all_source_ids("Detector_Readout")

        if self.debug: console.log(f"Registering Trigger Source IDs, tp_mode is {tp_mode}, dro_configs are {ru_descrs}")

        for ru_name, ru_desc in ru_descrs.items():
            det_id = ru_desc.det_id
            crate_id = ru_desc.streams[0].geo_id.crate_id

            det_str = DetID.subdetector_to_string(DetID.Subdetector(ru_desc.streams[0].geo_id.det_id))
            if tp_mode and ru_desc.kind == "eth" and det_str in ("HD_TPC","VD_Bottom_TPC"):
                for plane in range(3):
                    tp_ru_sid = self.get_next_source_id("Trigger")
                    self.register_source_id("Trigger", tp_ru_sid, RUEndpointInfo(ru_desc, plane)),

                    tpid = TPID(det_id, crate_id, plane)
                    tp_infos[tpid] = TPInfo()
                    tp_infos[tpid].region_id = crate_id
                    tp_infos[tpid].plane = plane
                    tp_infos[tpid].tp_ru_sid = tp_ru_sid
                    tp_infos[tpid].link_count = 1

                    taid = TAID(det_id, crate_id, plane)
                    ta_infos[taid] = TAInfo()
                    ta_infos[taid].region_id = crate_id
                    ta_infos[taid].plane = plane
                    ta_infos[taid].link_count = 1

            tc_info.ru_count += 1

        for tp_info in tp_infos.values():
            tpsid = self.get_next_source_id("Trigger")
            if self.debug: console.log(f"Registering Trigger TP Source IDs {tpsid} for region {tp_info.region_id} {tp_info.plane}")
            self.register_source_id("Trigger", tpsid, tp_info)
        for ta_info in ta_infos.values():
            tasid = self.get_next_source_id("Trigger")
            if self.debug: console.log(f"Registering Trigger TA Source IDs {tasid} for region {ta_info.region_id} {ta_info.plane}")
            self.register_source_id("Trigger", tasid, ta_info)
        self.register_source_id("Trigger", self.get_next_source_id("Trigger"), tc_info)


# def get_tpg_mode(enable_fw_tpg, enable_tpg):
#     if enable_fw_tpg and enable_tpg:
#         raise ValueError("Cannot enable both FW and SW TPG!")
#     if enable_fw_tpg:
#         return TPGenMode.FWTPG
#     if enable_tpg:
#         return TPGenMode.SWTPG

#     return TPGenMode.DISABLED
                

def source_id_raw_str(source_id: SourceID):
    """Get a string representation of a SourceID suitable for using in queue names"""
    return source_id.to_string()

def ensure_subsystem_string(subsystem):
    if isinstance(subsystem, str):
        return subsystem
    
    return SourceID.subsystem_to_string(SourceID.Subsystem(subsystem))

def ensure_subsystem(subsystem):
    if isinstance(subsystem, str):
        return SourceID.string_to_subsystem(subsystem)

    return SourceID.Subsystem(subsystem)
