# Set moo schema search path
from dunedaq.env import get_moo_model_path
import moo.io
moo.io.default_load_path = get_moo_model_path()
from rich.console import Console
from enum import Enum

console = Console()

from daqdataformats._daq_daqdataformats_py import SourceID
from detchannelmaps._daq_detchannelmaps_py import *

class SourceIDBroker:
    sourceid_map = {}

    class TPGenMode(Enum):
        DISABLED = 1
        SWTPG = 2
        FWTPG = 3
        

    def get_next_source_id(self, subsystem):
        next_id = 1
        while self.source_id_exists(subsystem, next_id):
            next_id += 1
        return next_id

    def get_all_source_ids(self, subsystem):
        return self.sourceid_map[subsystem]

    def source_id_exists(self, subsystem, sid):
        return sid in self.sourceid_map[subsystem]

    def register_source_id(self, subsystem, sid, info):
        if not self.source_id_exists(subsystem, sid):
            self.sourceid_map[subsystem][sid] = info
        else:
            raise ValueError(f"SourceID {sid} already exists for Subsystem {subsystem}!")

    def generate_trigger_source_ids(self, dro_configs, tp_mode: TPGenMode):
        if tp_mode == self.TPGenMode.DISABLED:
            pass
        for dro_config in dro_configs:
            if tp_mode == self.TPGenMode.FWTPG:
                slr0_found = False
                slr1_found = False
                for link in dro_config.links:
                    if link.dro_slr == 0 and not slr0_found:
                        sid = self.get_next_source_id("Trigger")
                        self.register_source_id("Trigger", sid, link)
                        slr0_found = True
                    if link.dro_slr == 1 and not slr1_found:
                        self.register_source_id("Trigger", sid, link)
                        slr1_found = True
            else:
                for link in dro_config.links:
                    if not self.source_id_exists("Trigger", link.dro_source_id):
                        self.register_source_id("Trigger", link.dro_source_id, link)
                    else:
                        sid = self.get_next_source_id("Trigger")
                        console.log("SourceID Conflict in Trigger! {link.dro_source_id} will correspond to Trigger SourceID {sid}!")
                        self.register_source_id("Trigger", sid, link)


def source_id_raw_str(source_id: SourceID):
    """Get a string representation of a SourceID suitable for using in queue names"""
    return f"sourceid{source_id.subsystem}_{source_id.id}"

def ensure_subsystem_string(subsystem):
    if isinstance(subsystem, str):
        return subsystem
    
    return SourceID.subsystem_to_string(SourceID.Subsystem(subsystem))
