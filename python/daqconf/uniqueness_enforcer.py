'''
HW: Enforces uniqueness of configuration elements within a set of configuration files.
'''

from typing import Any, List, Dict, Set, Tuple, Optional

from matplotlib.pyplot import table

from conffwk import Configuration
from pathlib import Path
from dataclasses import dataclass, field
from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt    

# ------ Helper Classes ------ #

# Helper functions to convert DAL to unique key and back
class DALKeyConverter:
    '''
    Helper class to convert DAL objects to unique string keys and back, this means we can use sets (because DAL hashes don't work)
    '''
    DELIMITER = "@"
    
    @staticmethod
    def dal_to_key(dal) -> str:
        '''Converts dal to dal_class:dal_id string'''
        return f"{dal.className()}{DALKeyConverter.DELIMITER}{dal.id}"

    @staticmethod
    def key_to_dal(key: str) -> Tuple[str, str]:
        '''
        Converts to dal_class:dal_id to tuple
        '''
        dal_class, dal_id = key.split(DALKeyConverter.DELIMITER)
        return dal_class, dal_id
    
# ------ Uniqueness Enforcement Classes ------ #

@dataclass
class UniquenessInformant:
    '''
    Dataclass containing information from the uniqueness enforcer
    '''
    dal_id: str
    dal_class: str
    relationships_match: bool = True
    attributes_match: bool = True
    conflicted_sessions: list[str] = field(default_factory=lambda: [])
    contained_in_files: list[Path] = field(default_factory=lambda: [])
    names: list[str] = field(default_factory=lambda: [])
    
    def as_table(self)->Table:
        if not self.conflicted_sessions:
            return Table(title=f"No uniqueness violations for {self.dal_class}, {self.dal_id}")

        table = Table(title=f"Uniqueness Violation for [bold red]{self.dal_class}, {self.dal_id}")

        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Status / Details", style="magenta")

        rels_status = "[green]Match[/green]" if self.relationships_match else "[red]Do Not Match[/red]"
        attrs_status = "[green]Match[/green]" if self.attributes_match else "[red]Do Not Match[/red]"

        table.add_row("Relationships", rels_status)
        table.add_row("Attributes", attrs_status)

        # Existing summary rows
        sessions = ", ".join(self.conflicted_sessions)
        table.add_row("Conflicted Sessions", sessions)

        contained_in = ", ".join(str(f.name) for f in self.contained_in_files)
        table.add_row("Contained In Files", contained_in)

        if self.names:
            names = ", ".join(self.names)
            table.add_row("DAL Names", names)

        table.add_row("Renaming Info", "")
        for file, session, new_name in zip(self.contained_in_files, self.conflicted_sessions, self.names):
            table.add_row(
                f"• {file.name}",
                f"Session: {session}\nRenamed to: [bold]{new_name}[/bold]"
            )

        return table
    
    def to_csv_row(self) -> str:
        '''
        Convert the uniqueness violation to a CSV row
        '''
        sessions = ";".join(self.conflicted_sessions)
        contained_in = ";".join(str(f.name) for f in self.contained_in_files)
        names = ";".join(self.names)
        return f"{self.dal_class},{self.dal_id},{self.relationships_match},{self.attributes_match},\"{sessions}\",\"{names}\",\"{contained_in}\"\n"

class UniquenessReportPrinter:
    '''
    Class to print and export uniqueness reports
    '''
    def __init__(self, enforcers: List[UniquenessInformant]):
        self.enforcers = enforcers
    
    def print_report(self):
        console = Console()
        if not self.enforcers:
            console.print("No uniqueness violations found!", style="bold green")
            return
        
        for enforcer in self.enforcers:
            console.print(enforcer.as_table())
    
    def to_csv(self) -> str:
        '''
        Convert the report to CSV format
        '''
        header = "DAL Class,DAL ID,Relationships Match,Attributes Match,Conflicted Sessions,New Names,Contained In Files\n"
        rows = [enforcer.to_csv_row() for enforcer in self.enforcers]
        return header + "".join(rows)
    
    def __call__(self, output_csv: Optional[Path] = None):
        self.print_report()
        if output_csv:
            csv_content = self.to_csv()
            with open(output_csv, 'w') as f:
                f.write(csv_content)

# ------ Config and DAL operations ------ #

class ConfigLoader:
    '''Loads all configurations in a given folder'''
    def __init__(self, config_folder: Path):
        ''' Load all configurations in the given folder
        '''
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
                unique_key = DALKeyConverter.dal_to_key(dal)
                    
                if unique_key not in dal_map:
                    dal_map[unique_key] = []
                dal_map[unique_key].append(config)
        return dal_map
    
    def dal_uniquely_defined(self, dal_class_id_key: str, configs: List[Configuration], rename: bool=False)-> UniquenessInformant:
        '''
        Enforce that each DAL id/class combination is uniquely defined
        '''        
        dal_class, dal_id = DALKeyConverter.key_to_dal(dal_class_id_key)

        enforcer = UniquenessInformant(dal_id=dal_id, dal_class=dal_class)


        if len(configs) <= 1:
            return enforcer # No conflict
        
        init_dal = configs[0].get_dal(dal_class, dal_id)        
        contained_in_init = self.__get_contained_in(init_dal, configs[0])

        for config in configs[1:]:
            compare_dal = config.get_dal(dal_class, dal_id)
            contained_in_compare = self.__get_contained_in(compare_dal, config)
            
            if contained_in_init == contained_in_compare:
                continue  # Same file, no conflict

            comparison = DalComparison(init_dal, compare_dal, configs[0])
            rels_match, attrs_match = comparison()
            
            if rels_match and attrs_match :
                continue
            
            if not rels_match:
                enforcer.relationships_match = False
            if not attrs_match:
                enforcer.attributes_match = False

            if rename:
                renamer = DalNameGenerator(compare_dal, config)
                new_name = renamer.name
                enforcer.names.append(new_name)
                renamer.rename()
            
            enforcer.conflicted_sessions.append(self._session_names[config])
            enforcer.contained_in_files.append(self.__get_contained_in(compare_dal, config))

        # If there are conflicts, add the first session as well for reference
        if enforcer.conflicted_sessions:
            enforcer.conflicted_sessions.insert(0, self._session_names[configs[0]])
            enforcer.contained_in_files.insert(0, self.__get_contained_in(init_dal, configs[0]))
            if rename:
                renamer = DalNameGenerator(init_dal, configs[0])
                new_name = renamer.name
                enforcer.names.insert(0, new_name)
                renamer.rename()

        return enforcer
    
    def __get_contained_in(self, dal, config)-> Path:
        '''Bit hacky but finds the file that contains the DAL'''
        obj = config.get_obj(dal.className(), dal.id)
        return Path(obj.contained_in())
    
    def check_dal_uniqueness(self, rename: bool=False) -> List[UniquenessInformant]:
        '''
        Enforce uniqueness across all DALs
        '''
        results: List[UniquenessInformant] = []
        
        for dal_key, configs in self.dals.items():
            enforcer = self.dal_uniquely_defined(dal_key, configs, rename=rename)
            if enforcer.conflicted_sessions:
                results.append(enforcer)
        
        return results
            
    def __call__(self, rename: bool=False) -> List[UniquenessInformant]:
        return self.check_dal_uniqueness(rename=rename)

    def commit_changes(self):
        '''
        Commit any changes made to the configurations
        '''
        for config in self.configs:
            try:
                config.commit('update')
            except Exception as e:
                console = Console()
                console.print(f"[bold red]Failed to commit changes for configuration {config}:[/bold red] {e}")

class DalComparison:
    def __init__(self, dal_1, dal_2, reference_config: Configuration):
        '''
        Compares relationships and attributes of two DALs
        '''
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
                return False
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
        return set([DALKeyConverter.dal_to_key(r) for r in related_dals])

    def __call__(self) -> Any:
        rels_equal = self.compare_relationships()
        attrs_equal = self.compare_attributes()
        return rels_equal, attrs_equal


class DalNameGenerator:
    '''
    Generate a unique name for a DAL based on its class and id
    '''
    def __init__(self, dal, config: Configuration):
        self.dal = dal
        self.config = config
        self.name = self.generate_name()
    
    def find_related_dal(self):
        '''
        Finds the DAL that includes this DAL in its relationships
        '''
        all_dals = list(self.config.get_all_dals().values())
        
        for candidate in all_dals:
            relations = self.config.relations(candidate.className(), all=True)
            for rel in relations:
                related = getattr(candidate, rel, [])
                if not isinstance(related, list):
                    related = [related]
                if self.dal in related:
                    return candidate
        return None
    
    def generate_name(self) -> str:
        related_dal = self.find_related_dal()
        if related_dal:
            return f"{related_dal.id}_{self.dal.id}"
        else:
            return f"{self.dal.id}_orphaned"
    
    def rename(self):
        new_name = self.name
        self.dal.rename(new_name)
        self.config.update_dal(self.dal)
