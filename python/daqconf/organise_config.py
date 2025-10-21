from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tqdm import tqdm

from conffwk import Configuration

import logging 


'''
Usage:
    1. Need to source setup_db_path.sh
    2. If you want to make a separate directory THAT ALSO needs to source setup_db_path.sh
    3. python organise_config.py -o outputfolder [-c /path/to/config1.data.xml -c /path/to/config2.data.xml OR -c /path/to/configs_dir/] 
    4. Optionally you can "split" certain DAL classes into their own files using -s DALClassName. NOTE This really only works for root nodes like Session.
'''
@dataclass
class OrganisedConfig:
    path: Path
    id: int
    dals: List[Tuple[str, str]]
    connected_to: List[int]

class ConfigOrganiser(ABC):
    def __init__(self, configs: List[Path]| Path):
        self.config_paths = []
        
        if isinstance(configs, Path):
            if configs.is_file():
                self.config_paths = [configs]
            else:
                self.config_paths = list(configs.rglob("**/*.data.xml"))
        else:
            for config in configs:
                if config.is_file():
                    self.config_paths.append(config)
                elif config.is_dir():
                    self.config_paths.extend(list(config.rglob("**/*.data.xml")))
                else:
                    raise ValueError(f"Config path {config} is neither a file nor a directory")                    
            
        
        
        self.config = [Configuration(f"oksconflibs:{s}") for s in self.config_paths]

        self._organised_configs = self.apply_rules()
        self.get_all_connected()
        
        
    @abstractmethod
    def apply_rules(self) -> List[OrganisedConfig]:
        pass

    def get_by_idx(self, idx: int) -> OrganisedConfig:
        org = next((org for org in self._organised_configs if org.id == idx), None)
        if org is None:
            raise ValueError(f"OrganisedConfig with id {idx} not found")
        return org

    def get_organised_configs(self) -> List[OrganisedConfig]:
        if not self._organised_configs:
            self._organised_configs = self.apply_rules()
            self.get_all_connected()
        return self._organised_configs

    def get_all_includes(self, db, file):
        
        includes = db.get_includes(file)

        for include in includes:
            if "data.xml" not in include:
                continue
            includes += self.get_all_includes(db, include)

        return list(set(includes))
    
    def get_all_connected(self):
        if not self._organised_configs:
            self._organised_configs = self.apply_rules()

        for org in self._organised_configs:
            connected = set()
            for dal_class, dal_id in org.dals:
                connected.update(self.__parse_relationships(dal_class, dal_id, org))
                
            org.connected_to = list(connected)
    
    def __parse_relationships(self, dal_class: str, dal_id: str, org: OrganisedConfig) -> Set[int]:
        # We now get the relationships for this DAL
        connected = set()
        dal, selected_config = self.get_dal(dal_class, dal_id)

        relationships = selected_config.relations(dal_class, all=True)

        for rel in relationships:
            rel_obj = getattr(dal, rel, None)
            if rel_obj is None:
                continue

            if not isinstance(rel_obj, list):
                rel_obj = [rel_obj]
                
            for related_dal in rel_obj:
                try:
                    idx = self.__find_idx_for_dal(related_dal)
                    
                    if idx!= org.id:
                        connected.add(idx)
                except ValueError as e:
                    logging.warning(f"Warning: Related DAL {related_dal.className()}:{related_dal.id} not found in organised config - {e}")
        return connected

    def __find_idx_for_dal(self, dal) -> int:
        '''
        Finds the organised config index for a given DAL
        '''
        
        dal_id = dal.id
        dal_class = dal.className()

        idx = next((org for org in self._organised_configs if (dal_class, dal_id) in org.dals), None)
        if idx is None:
            raise ValueError(f"DAL {dal_class}:{dal_id} not found in organised config")
        return idx.id
    
    def get_dal(self, dal_class: str, dal_id: str):
        for c in self.config:
            try:
                dal = c.get_dal(dal_class, dal_id)
                return dal, c
            except Exception:
                continue
        raise ValueError(f"DAL {dal_class}:{dal_id} not found in any config")

class ClassConfigOrganiser(ConfigOrganiser):
    # Simple rule: one config per DAL class

    def apply_rules(self) -> List[OrganisedConfig]:
        # dal_list = [i for i in  self.config.get_all_dals().values()]
        dal_list = []
        classes = []
        
        for c in self.config:
            ext = [i for i in  c.get_all_dals().values() if i not in dal_list]
            dal_list.extend(ext)
            classes.extend([cl for cl in c.classes() if cl not in classes])
        
        organised_configs = []    
                
        for (i, class_) in tqdm(enumerate(classes), "Applying rules", total=len(classes)):
            # Bit slow... but hard to do this query otherwise
            dals_list = [(class_, dal.id) for dal in dal_list if dal.className() == class_]


            additional_type: OrganisedConfig = OrganisedConfig(
                path=Path(f"{class_}.data.xml"),
                id=i,
                dals=dals_list,
                connected_to = []
            )

            if dals_list:
                organised_configs.append(additional_type)
        return organised_configs

class ConfigGraph:
    '''
    Makes a graph of the config relationships and performs a topological sort
    '''
    def __init__(self, organiser: ConfigOrganiser):
        self.organiser = organiser
        self.graph = self.build_graph()
        self.sorted_configs = self.topological_sort()
        
    def build_graph(self) -> dict[int, List[int]]:
        graph = {}
        for org in self.organiser.get_organised_configs():
            graph[org.id] = org.connected_to
        return graph
    
    def topological_sort(self) -> List[int]:
        visited = set()
        stack = []
        
        def visit(node):
            if node in visited:
                return
            visited.add(node)
            for neighbor in self.graph.get(node, []):
                visit(neighbor)
            stack.append(node)
        
        for node in self.graph:
            visit(node)
        
        stack.reverse()
        return stack
    
    def get_longest_path(self, start_node: int, end_node: int) -> List[int]:
        # Simple DFS to find the longest path from start_node to end_node
        longest_path = []
        def dfs(current_node, path):
            nonlocal longest_path
            path.append(current_node)
            if current_node == end_node:
                if len(path) > len(longest_path):
                    longest_path = path.copy()
            else:
                for neighbor in self.graph.get(current_node, []):
                    dfs(neighbor, path)
            path.pop()
        dfs(start_node, [])
        return longest_path
        
    def get_graph_span(self)-> int:
        '''
        Get max distance from root to leaf nodes
        '''
        
        max_span = 0
        for node in self.find_root_nodes():
            for target in self.find_leaf_nodes():
                path = self.get_longest_path(node, target)
                if len(path) > max_span:
                    max_span = len(path)
        return max_span
    
    def find_root_nodes(self, graph: Optional[Dict[int, List[int]]] = None) -> List[int]:
        '''
        Find all nodes with only outgoing edges i.e. a session
        '''
        graph = graph or self.graph
        all_nodes = set(graph.keys())
        non_root_nodes = set()
        
        for edges in graph.values():
            non_root_nodes.update(edges)
        
        root_nodes = list(all_nodes - non_root_nodes)
        return root_nodes
    
    def find_leaf_nodes(self, graph: Optional[Dict[int, List[int]]] = None) -> List[int]:
        '''
        Find all nodes with only incoming edges 
        '''
        graph = graph or self.graph
        leaf_nodes = [node for node, edges in graph.items() if not edges]
        return leaf_nodes
    
    def get_include_dependencies(self, node_id: int) -> List[int]:
        '''
        Computes the include dependencies for a given node
        '''

        candidate_ids = set(self.graph.get(node_id, []))
        
        for candidate_id in list(candidate_ids):
            for other_id in self.organiser.get_by_idx(candidate_id).connected_to:
                if candidate_id == other_id:
                    continue
                path = self.get_longest_path(other_id, candidate_id)
                if len(path) > 1:
                    candidate_ids.discard(candidate_id)
                    break
        return sorted(candidate_ids)

    def build_include_graph(self) -> Dict[int, List[int]]:
        include_graph: Dict[int, List[int]] = {}
        for node_id in self.graph:
            include_graph[node_id] = self.get_include_dependencies(node_id)
        return include_graph

    def compute_processing_levels(self) -> Dict[int, int]:
        '''
        Computes processing levels for each node in the graph
        This ensure that dependent nodes are processed after their dependencies
        0 = root nodes, highest number = leaf nodes
        '''

        logging.info("Generating dependency levels for config graph...")

        remaining = set(self.graph.keys())
        dependencies = {node: set(edges) for node, edges in self.graph.items()}
        for edges in self.graph.values():
            remaining.update(edges)
        for node in remaining:
            dependencies.setdefault(node, set())

        levels: Dict[int, int] = {}
        current_level = self.get_graph_span()
        
        while remaining:
            current_nodes = [
                node for node in remaining if not any(dep in remaining for dep in dependencies.get(node, set()))
            ]

            if not current_nodes:
                current_nodes = [
                    node
                    for node in remaining
                    if not any(
                        dep in remaining
                        for dep in self.organiser.get_by_idx(node).connected_to
                    )
                ]

            if not current_nodes:
                current_nodes = list(remaining)

            for node in current_nodes:
                levels[node] = current_level
                remaining.discard(node)

            current_level -= 1
        return levels

class ConfigFileGenerator:
    '''
    Takes a graph and generates config files based on it starting with the leaf nodes
    '''
    def __init__(self, organiser: ConfigOrganiser, output_folder: Path, split_classes: Optional[List[str]] = None):
        self.organiser = organiser
        self.graph = ConfigGraph(organiser)
        self.output_folder = output_folder
        self.split_classes = split_classes if split_classes is not None else []        
        
        self.output_folder.mkdir(parents=True, exist_ok=True)

        self._schema_files: List[str] = []
        for conf in self.organiser.config:
            self._schema_files += [c for c in self.organiser.get_all_includes(conf, None) if "schema.xml" in c]
        self._schema_files = list(set(self._schema_files))
    
    def generate_files(self):
        '''Needs to iterate over ALL leaf nodes first, then work backwards'''

        # First we need to know the processing levels
        levels = self.graph.compute_processing_levels()
        
        # Next we group nodes by level
        nodes_by_level: Dict[int, List[int]] = {}
        
        # Populate nodes by level
        for node_id, level in levels.items():
            nodes_by_level.setdefault(level, []).append(node_id)

        total_nodes = len(levels)

        pbar = tqdm(total=total_nodes, desc="Generating config files")

        # Make sure to process from highest level (leaf nodes) to lowest
        for level in sorted(nodes_by_level, reverse=True):
            output_path = Path(f"level_{level}")
            for node_id in sorted(nodes_by_level[level]):
                org_config = self.organiser.get_by_idx(node_id)
                self._save_config(org_config, output_path)
                pbar.update(1)
        pbar.close()


    def _save_config(self, org_config: OrganisedConfig, out_path: Path):
        
        org_config.path = out_path / org_config.path
        
        
        file_path = self.output_folder  / org_config.path
        
        # Make sure folder exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        include_ids = self.graph.get_include_dependencies(org_config.id)
        include_paths = [str(self.organiser.get_by_idx(conn_id).path) for conn_id in include_ids]
        
        include_paths += self._schema_files

        commit_main = not any([dal_class in self.split_classes for dal_class, _ in org_config.dals])


        if commit_main:
            db = Configuration("oksconflibs")        
            try:
                db.create_db(str(file_path), include_paths)
            except Exception as e:
                raise RuntimeError(f"Failed to create DB for {file_path} with includes {include_paths}: {e}")

            db.commit()
        else:
            db = None
        
        for dal_class, dal_id in org_config.dals:
            if dal_class in self.split_classes:
                self._make_root_file(dal_class, dal_id, org_config, out_path)
            elif commit_main:
                dal, _ = self.organiser.get_dal(dal_class, dal_id)
                db.add_dal(dal)
    
        if commit_main:
            db.commit()
        
    def _make_root_file(self, dal_class: str, dal_id: str, org_config: OrganisedConfig, out_path: Path):
        '''
        Makes separate files for root nodes
        '''
        file_path = self.output_folder  / out_path
        
        # Make sure folder exists
        file_path.mkdir(parents=True, exist_ok=True)

        include_ids = self.graph.get_include_dependencies(org_config.id)
        include_paths = [str(self.organiser.get_by_idx(conn_id).path) for conn_id in include_ids]
        include_paths += self._schema_files

        root_path = file_path / f"{dal_id}.data.xml"
        
        try:
            db = Configuration("oksconflibs")
            db.create_db(str(root_path), include_paths)
        except Exception as e:
            raise RuntimeError(f"Failed to create DB for {root_path} with includes {include_paths}: {e}")

        db.commit()
        dal, _ = self.organiser.get_dal(dal_class, dal_id)
        db.add_dal(dal)
        db.commit()
