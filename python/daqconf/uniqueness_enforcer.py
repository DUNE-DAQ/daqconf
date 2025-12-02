'''
HW: Enforces uniqueness of configuration elements within a set of configuration files.
'''

from typing import Any, List, Dict, Set, Tuple, Optional

from conffwk import Configuration
from pathlib import Path
from dataclasses import dataclass, field
import rich
    
        

@dataclass
class UniquenessEnforcer:
    dal_id: str
    dal_class: str
    relationships_match: bool = True
    attributes_match: bool = True
    conflicted_sessions: list[str] = field(default_factory=lambda: [])
    
    def as_table(self)->rich.table.Table:
        if not self.conflicted_sessions:
            return f"No uniqueness violations for {self.dal_class}:{self.dal_id}"
        
        table = rich.table.Table(title=f"Uniqueness Violation for [bold red]{self.dal_class}, {self.dal_id}")


        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        
        rels_status = "Match" if self.relationships_match else "Do Not Match"
        attrs_status = "Match" if self.attributes_match else "Do Not Match"
        
        table.add_row("Relationships", rels_status)
        table.add_row("Attributes", attrs_status)
        
        sessions = ", ".join(self.conflicted_sessions)
        table.add_row("Conflicted Sessions", sessions)
        
        return table
    
    def to_csv_row(self) -> str:
        '''
        Convert the uniqueness violation to a CSV row
        '''
        sessions = ";".join(self.conflicted_sessions)
        return f"{self.dal_class},{self.dal_id},{self.relationships_match},{self.attributes_match},\"{sessions}\"\n"
    
# Helper functions to convert DAL to unique key and back
def dal_to_key(dal) -> str:
    '''Converts dal to dal_class:dal_id string'''
    return f"{dal.className()}:{dal.id}"

def key_to_dal(key: str) -> Tuple[str, str]:
    '''
    Converts to dal_class:dal_id to tuple
    '''
    dal_class, dal_id = key.split(":")
    return dal_class, dal_id


# Pretty printing for UniquenessEnforcer
    

# Firstly we're going to load ALL configurations in a folder as SEPARATE configurations
class ConfigLoader:
    def __init__(self, config_folder: Path):
        if not config_folder.is_dir():
            raise ValueError(f"Provided path {config_folder} is not a directory.")
        self.configs = self.load_configs(config_folder)
        
        self._session_names = {c: c.get_dals("Session")[0].id for c in self.configs}
        
        self.dals = self.collect_dals()

    def load_configs(self, config_folder: Path) -> List[Configuration]:
        configs = [Configuration(f"oksconflibs:{f}") for f in config_folder.glob('*.data.xml')]
        return configs
    
    def collect_dals(self) -> Dict[str, List[Configuration]]:
        '''
        For each DAL id, get all configuration files that define it
        '''
        dal_map: Dict[str, List[Configuration]] = {}
        for config in self.configs:
            dals = config.get_all_dals()
            for dal in dals.values(): 
                unique_key = dal_to_key(dal)
                    
                if unique_key not in dal_map:
                    dal_map[unique_key] = []
                dal_map[unique_key].append(config)
        return dal_map
    
    def dal_uniquely_defined(self, dal_class_id_key: str, configs: List[Configuration])-> UniquenessEnforcer:
        '''
        Enforce that each DAL id/class combination is uniquely defined
        '''        
        dal_class, dal_id = key_to_dal(dal_class_id_key)

        enforcer = UniquenessEnforcer(dal_id=dal_id, dal_class=dal_class)

        if len(configs) <= 1:
            return enforcer # No conflict
        
        init_dal = configs[0].get_dal(dal_class, dal_id)        


        for config in configs[1:]:
            compare_dal = config.get_dal(dal_class, dal_id)
            comparison = DalComparison(init_dal, compare_dal, configs[0])
            rels_match, attrs_match = comparison()
            
            if rels_match and attrs_match:
                continue    
            
            if not rels_match:
                enforcer.relationships_match = False
            if not attrs_match:
                enforcer.attributes_match = False
                
            enforcer.conflicted_sessions.append(self._session_names[config])

        # If there are conflicts, add the first session as well for reference
        if enforcer.conflicted_sessions:
            enforcer.conflicted_sessions.insert(0, self._session_names[configs[0]])

        return enforcer
    
    def check_dal_uniqueness(self) -> List[UniquenessEnforcer]:
        '''
        Enforce uniqueness across all DALs
        '''
        results: List[UniquenessEnforcer] = []
        
        for dal_key, configs in self.dals.items():
            enforcer = self.dal_uniquely_defined(dal_key, configs)
            if enforcer.conflicted_sessions:
                results.append(enforcer)
        
        return results
            
    def __call__(self) -> List[UniquenessEnforcer]:
        return self.check_dal_uniqueness()

class DalComparison:
    def __init__(self, dal_1, dal_2, reference_config: Configuration):
        self.dal_1 = dal_1
        self.dal_2 = dal_2
        self.reference_config = reference_config
    
    def compare_attributes(self) -> bool:
        '''
        Compare attributes of the two DALs
        '''
        attrs = self.reference_config.attributes(self.dal_1.className())
        
        for attr in attrs:
            val1 = getattr(self.dal_1, attr)
            val2 = getattr(self.dal_2, attr)
            if val1 != val2:
                return {}
        return True
    
    def compare_relationships(self) -> bool:
        '''
        Compare relationships of the two DALs
        '''
        rels = self.reference_config.relations(self.dal_1.className(), all=True)
        
        for rel in rels:
            rels_1 = self.__rels_to_ids(self.dal_1, rel)
            rels_2 = self.__rels_to_ids(self.dal_2, rel)
            
            if rels_1 != rels_2:
                return False
            
        return True
    
    def __rels_to_ids(self, dal, rel_name: str) -> Set[str]:
        '''
        Convert related DALs to their unique keys for comparison
        '''
        related_dals = getattr(dal, rel_name, [])

        if related_dals is None:
            return set()
        
        if not isinstance(related_dals, list):
            related_dals = [related_dals]
        return set([dal_to_key(r) for r in related_dals])

    def __call__(self) -> Any:
        rels_equal = self.compare_relationships()
        attrs_equal = self.compare_attributes()
        return rels_equal, attrs_equal

class UniquenessReportPrinter:
    def __init__(self, enforcers: List[UniquenessEnforcer]):
        self.enforcers = enforcers
    
    def print_report(self):
        console = rich.console.Console()
        if not self.enforcers:
            console.print("No uniqueness violations found!", style="bold green")
            return
        
        for enforcer in self.enforcers:
            console.print(enforcer.as_table())
    
    def to_csv(self) -> str:
        '''
        Convert the report to CSV format
        '''
        header = "DAL Class,DAL ID,Relationships Match,Attributes Match,Conflicted Sessions\n"
        rows = [enforcer.to_csv_row() for enforcer in self.enforcers]
        return header + "".join(rows)
    
    def __call__(self, output_csv: Optional[Path] = None):
        self.print_report()
        if output_csv:
            csv_content = self.to_csv()
            with open(output_csv, 'w') as f:
                f.write(csv_content)
        # Save 

