"""
HW: Finds non-unique DAL objects and provides a simple CLI to rename them iteratively
"""
# Python defaults
from typing import List, Dict, Any, Set, Callable, Optional
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass
from itertools import combinations
import re

# rich
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from typing import List
from rich.panel import Panel


import click

# Conffwk
from conffwk import Configuration
from conffwk.dal import DalBase

console = Console()
#  ----- Errors --------------------
class RenameDalError(Exception):
    ...

class NamesMatchError(RenameDalError):
    '''For when the user has renamed DALs to still
       have the same name
    '''
    
class ConfigCommitError(Exception):
    def __init__(self, config) -> None:
        super().__init__(f"Cannot commit changes to {config}, make sure you are not currently modifying it in some other process!")

class DalConfigLenMismatch(ValueError):
    def __init__(self, dals: List[DalBase], configs: List[Configuration]) -> None:
        super().__init__(f"DalCollection expects same number of dals and configs but has {len(dals)} dals and {len(configs)} configs")

#  ----- Cache relations to avoid many lookup to get parent(s) of objects efficiently -----
class RelationshipCache:
    '''
    simple class to cache relationships between objects and get their parents
    '''
    def __init__(self, db: Configuration | str):
        if isinstance(db, str):
            db = Configuration("oksconflibs:" + db)  
        self.db = db
        self._relations_cache = {}
        self._parents_cache = {}
        
        self.graph = self.cache_relations()
    
    def _get_relations(self, class_name: str):
        """Cache relations queries to avoid repeated DB calls"""
        if class_name not in self._relations_cache:
            self._relations_cache[class_name] = self.db.relations(class_name, all=True)
        return self._relations_cache[class_name]
    
    def cache_relations(self):
        """Iterative tree building using BFS to avoid recursion overhead"""
        graph = {}        
        objects = self.db.get_all_dals()        
        for obj in objects.values():
        
            rels = self._get_relations(obj.className())
            related_objects_list = []
            
            for rel in rels:
                related_objects = getattr(obj, rel, [])
                
                if related_objects is None:
                    continue
                
                if not isinstance(related_objects, list):
                    related_objects = [related_objects]
                
                related_objects_list.extend(related_objects)
                
            if related_objects_list:
                graph[obj] = related_objects_list
        return graph
    
    def get_parents(self, obj: DalBase):
        """Get all parent objects of the given object in the tree"""
        if obj in self._parents_cache:
            return self._parents_cache[obj]

        parents = []
        for parent, children in self.graph.items():
            if obj in children:
                parents.append(parent)
        
        self._parents_cache[obj] = parents
        return parents


class TreeSorter:
    """Sorts ConsolidatedDals by their position in tree structures"""
    
    def __init__(self, trees: Dict[Configuration, RelationshipCache], consolidated_dals: List['ConsolidatedDals']):
        self.trees = list(trees.values())
        self.consolidated_dals = consolidated_dals
        self.all_dal_ids = set(c.dals[0].id for c in consolidated_dals)
        self.covered = set()
        self.sorted_list = []
    
    def sort(self) -> List['ConsolidatedDals']:
        """Sort consolidated_dals by iteratively building trees until all objects are covered"""
        iteration = 0
        
        while self.covered != self.all_dal_ids:
            iteration += 1
            root = self._get_root_for_iteration(iteration)
            
            if root is None:
                break
            
            self._process_tree_from_root(root)
        
        return self.sorted_list
    
    def _get_root_for_iteration(self, iteration: int) -> DalBase:
        """Get the root object for the current iteration"""
        if iteration == 1:
            # First iteration: use the Session root from the first tree
            session = self.trees[0].db.get_dals("Session")
            if not session:
                raise ValueError("Your files must contain a session!")
            return session[0]
        else:
            # Subsequent iterations: pick an uncovered DAL as root
            remaining = self.all_dal_ids - self.covered
            if not remaining:
                return None
            
            # Find a ConsolidatedDals with an uncovered DAL
            for consolidated in self.consolidated_dals:
                if consolidated.dals[0].id in remaining:
                    return consolidated.dals[0]
            
            return None
    
    def _process_tree_from_root(self, root: DalBase):
        """Process trees starting from the given root using BFS across all trees"""
        depth_map = self._build_depth_map(root)
        self._add_sorted_batch(depth_map)
    
    def _build_depth_map(self, root: DalBase) -> Dict[str, int]:
        """Build a depth map from the root using BFS, checking all trees for children"""
        depth_map = {}
        queue = [(root, 0)]
        visited = set()
        
        while queue:
            obj, depth = queue.pop(0)
            obj_id = id(obj)
            
            if obj_id in visited:
                continue
            visited.add(obj_id)
            
            depth_map[obj.id] = depth
            self.covered.add(obj.id)
            
            # Check all trees for children of this object
            all_children = []
            for tree in self.trees:
                children = tree.graph.get(obj, [])
                all_children.extend(children)
            
            # Deduplicate children by id (same DAL may appear in multiple trees)
            seen_child_ids = set()
            for child in all_children:
                child_obj_id = id(child)
                if child_obj_id not in visited and child_obj_id not in seen_child_ids:
                    queue.append((child, depth + 1))
                    seen_child_ids.add(child_obj_id)
        
        return depth_map
        
    @staticmethod
    def _natural_sort_key(dal_id: str) -> list:
        """Split ID into alternating text/int chunks for natural alphanumeric ordering."""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', dal_id)]


    def _add_sorted_batch(self, depth_map: Dict[str, int]):
        """Add a batch of consolidated_dals sorted by depth, then naturally by DAL ID."""
        batch = [
            c for c in self.consolidated_dals 
            if c.dals[0].id in depth_map
        ]
        batch.sort(key=lambda c: (depth_map[c.dals[0].id], self._natural_sort_key(c.dals[0].id)))
        self.sorted_list.extend(batch)
#  ----- Uniqueness Operations -----

class ExtendedDal:
    def __init__(self, dal: DalBase, config: Configuration, tree: RelationshipCache):
        self.dal = dal
        self.configuration = config
        self.tree = tree
        
        self._attributes = None
        self._relations = None
        
    @property
    def attributes(self)->Dict[str, Any]:
        '''Gets attributes as [attr: list[attribute]]'''
        if self._attributes is None:
            self._attributes = {a: getattr(self.dal, a, None) for a 
                                in self.configuration.attributes(self.dal.className())}

        return self._attributes
        
    def _get_relations(self)->Dict[str, Set[str]]:
        '''
        Gets all the relations, assumes DAL string representation is unique for each DAL
        '''
        relations =  self.configuration.relations(self.dal.className(), all=True)

        # We now convet
        rel_dict = {}
        for relation in relations.keys():
            related_dals = getattr(self.dal, relation, None)

            # Makes comparison a bit "nicer" since it's a
            if related_dals is None:
                related_dals = []
            elif not isinstance(related_dals, list):
                related_dals = [related_dals]
            rel_dict[relation] = set([repr(rel) for rel in related_dals])
        return rel_dict

    def get_parents(self):
        return self.tree.get_parents(self.dal)

    def get_parents_extended(self):
        return [ExtendedDal(d, self.configuration, self.tree) for d in self.get_parents()]

    @property
    def relations(self)->Dict[str, Set[str]]:
        '''Gets relations as {rel name : [list of strings of dal]}'''
        if self._relations is None:
            self._relations = self._get_relations()
        
        return self._relations
    
    def rename(self, name: str)->None:
        self.dal.rename(name)
        self.configuration.update_dal(self.dal)

    def get_name(self)->str:
        return self.dal.id
    
    
    def __eq__(self, other: 'ExtendedDal')->bool:
        '''Check 2 dals are different (can't use dal==dal because different configs potentially!)'''
        if not isinstance(other, ExtendedDal):
            return False

        return (
            other.dal.className() == self.dal.className() and
            other.dal.id          == self.dal.id and
            other.attributes      == self.attributes and
            other.relations       == self.relations
        )

    def has_same_parents(self, other: 'ExtendedDal'):
        return other.get_parents_extended() == self.get_parents_extended()


class ConsolidatedDals:
    '''
    It's very hard to work out if a 
    '''
    def __init__(self, dal_list: List[DalBase], config_list: List[Configuration], trees: Dict[Configuration, RelationshipCache]):
        full_collection = [ExtendedDal(d, c, trees[c]) for d, c in zip(dal_list, config_list)]
        self._consolidated = self._consolidate(full_collection)
        self._trees = trees
    
    def _consolidate(self, full_collection: List[ExtendedDal])->List[ExtendedDal]:
        consolidated = []
        for item in full_collection:
            if not any(item == existing for existing in consolidated):
                consolidated.append(item)
        return consolidated

    @property
    def dals(self)->List[DalBase]:
        return [c.dal for c in self._consolidated]
    
    @property
    def has_same_parents(self) -> bool:
        return any(
            a.has_same_parents(b)
            for a, b in combinations(self._consolidated, 2)
        )
    
    @property
    def configs(self)->List[Configuration]:
        return [c.configuration for c in self._consolidated]

    def __getitem__(self, idx: int):
        return self._consolidated[idx]
    
    def __len__(self)->int:
        return len(self._consolidated)
                


class DalCollector:
    '''
    All the DALs in one collection
    '''
    def __init__(self, configs: List[Configuration]):
        self._configs = configs
        self._trees = {}
        
        # Need the tree, using the Session as an entry point
        console.print("[blue]Generating configuration trees")
        for config in self._configs:
            self._trees[config] = RelationshipCache(config)
                
        dal_config_pairs = [
            (dal, config)
            for config in configs
            for dal in config.get_all_dals().values()
        ]
        
        # Group by DAL ID
        grouped_by_repr = defaultdict(list)
        for dal, config in dal_config_pairs:
            grouped_by_repr[repr(dal)].append((dal, config))
        
        # Consolidate each group
        dal_collection = [
            ConsolidatedDals(
                dal_list=[dal for dal, _ in pairs],
                config_list=[config for _, config in pairs],
                trees = self._trees
            )
            for pairs in grouped_by_repr.values()
        ]
        
        self._consolidated_dals = [c for c in dal_collection if len(c)>1]
        # Sort by tree depth
        if self._consolidated_dals and self._trees:
            self._sort_by_tree_depth()
    
    def _sort_by_tree_depth(self):
        """Sort consolidated_dals using tree structure"""
        sorter = TreeSorter(self._trees, self._consolidated_dals)
        self._consolidated_dals = sorter.sort()
        
    @property
    def consolidated_dals(self):
        return self._consolidated_dals
        
    def __getitem__(self, idx: int):
        return self._consolidated_dals[idx]
          
    def __len__(self):
        return len(self._consolidated_dals)
        
    def commit(self):
        '''
        The only way to save is to quit...
        '''
        for config in self._configs:
            config.commit()

#  ----- CLI -------------------
@dataclass
class Action:
    key: str
    description: str
    handler: Callable[[], Optional[str]]  # returns next command to remember, or None
    remember: bool = True
    terminates: bool = False


class RenameDalCli:
    def __init__(self, dal_collector: DalCollector):
        self.collector = dal_collector
        self.history = []
        self._current_idx = 0
        self._all_dals = None
        self._actions = self._build_actions()

    def _build_actions(self) -> Dict[str, Action]:
        actions = [
            Action("n", "next",           self._handle_next),
            Action("p", "prev",           self._handle_prev),
            Action("c", "commit",         self._handle_save,  remember=False, terminates=False),
            Action("s", "save and quit",  self._handle_save,  remember=False, terminates=True),
            Action("q", "quit",           self._handle_quit,  remember=False, terminates=True),
        ]
        return {a.key: a for a in actions}

    # --- handlers ---
    def _handle_next(self):
        self._current_idx += 1

    def _handle_prev(self):
        if self._current_idx > 0:
            self._current_idx -= 1
        else:
            console.print("[yellow]Already at the first item[/]")

    def _handle_save(self):
        self._commit()
        console.print("[bold green]Committing and exiting[/]")

    def _handle_quit(self):
        console.print("[bold red]Exiting without committing[/]")

    def _handle_digit(self, action: str, consolidated: ConsolidatedDals):
        if consolidated.has_same_parents:
            console.print(
                "\n[bold red]Cannot rename these DALs because they share the same parents."
                "\nRenaming is disabled for this group.[/]"
            )
            Prompt.ask("[dim]Press Enter to continue[/]", default="")
            return

        idx = int(action) - 1
        if 0 <= idx < len(consolidated):
            self._rename_item(consolidated[idx])
        else:
            console.print("[red]Invalid number[/]")
            Prompt.ask("[dim]Press Enter to continue[/]", default="")

    # --- main loop ---
    def run(self):
        self._all_dals = self.collector.consolidated_dals
        self._current_idx = 0
        last_command = "n"

        prompt_str = ", ".join(
            f"\\[{a.key}] {a.description}" for a in self._actions.values()
        ) + ", or a number to rename"

        while self._current_idx < len(self._all_dals):
            consolidated = self._all_dals[self._current_idx]
            self._render_consolidated(consolidated)
            console.print(f"[dim]({self._current_idx + 1}/{len(self._all_dals)})[/]")

            action = Prompt.ask(prompt_str, default=last_command).lower()

            if action in self._actions:
                entry = self._actions[action]
                entry.handler()
                if entry.remember:
                    last_command = action
                if entry.terminates:
                    return
            elif action.isdigit():
                self._handle_digit(action, consolidated)
                last_command = action
            else:
                console.print("[red]Unknown command[/]")                             
                
    def _render_consolidated(self, consolidated: ConsolidatedDals):
        console.clear()

        if consolidated.has_same_parents:
            console.print(
                Panel(
                    "[bold red]Renaming Disabled[/]\n\n"
                    "These duplicated DAL objects share the same parents.\n"
                    "Renaming them would cause commit inconsistencies.",
                    title="⚠ WARNING",
                    border_style="red",
                    expand=False,
                )
            )
            console.print()  # spacing

        table = Table(title="Duplicated DAL Objects")

        table.add_column("#", justify="right")
        table.add_column("DAL ID", style="cyan")
        table.add_column("Class", style="magenta")
        table.add_column("Configuration", style="purple")
        table.add_column("Parents", style="blue")
        table.add_column("Attributes", style="green")
        table.add_column("Relations", style="yellow")

        for i, ext_dal in enumerate(consolidated, 1):
            attr_str = ", ".join(f"{k}={v}" for k, v in ext_dal.attributes.items())
            rel_str = ", ".join(f"{k}=[{', '.join(v)}]" for k, v in ext_dal.relations.items())

            table.add_row(
                str(i),
                ext_dal.get_name(),
                ext_dal.dal.className(),
                str(ext_dal.configuration),
                str(ext_dal.get_parents()),
                attr_str,
                rel_str,
            )

        console.print(table)


    def _rename_item(self, ext_dal: ExtendedDal):
        console.print(f"Renaming [cyan]{ext_dal.get_name()}[/] ({ext_dal.dal.className()})")
        new_name = Prompt.ask("Enter new name (or empty to cancel)").strip()
        if not new_name:
            console.print("[yellow]Rename cancelled[/]")
            return

        old_name = ext_dal.get_name()
        try:
            ext_dal.rename(new_name)
            self.history.append((ext_dal, old_name))
            console.print(f"[green]Renamed {old_name} → {new_name}[/]")
        except NamesMatchError:
            console.print(f"[red]Cannot rename {old_name} to {new_name} — name already exists[/]")

    def _commit(self):
        self.collector.commit()
        

@click.command()
@click.option("--input-folder", "-i", required=True, type=click.Path())
def rename_duplicate_dals(input_folder: Path):
    input_folder = Path(input_folder)
    if not input_folder.exists or not input_folder.is_dir():
        raise FileNotFoundError(f"Cannot find {input_folder}")
    
    configs = [Configuration(f"oksconflibs:{f}") for f in input_folder.glob("*.data.xml")]
    if not configs:
        raise FileNotFoundError("No configs found, please ensure you point to the folder containing your .data.xml configs!")
    
    collector = DalCollector(configs)
    cli = RenameDalCli(collector)
    cli.run()
    

if __name__=="__main__":
    # 1. Generate 2 configs with identical dals
    # 2. Find ALL identical objects
    # 3. rename works as expected
    # 4. Reload config + check its worked
    rename_duplicate_dals()
