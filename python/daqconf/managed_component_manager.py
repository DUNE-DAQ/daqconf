
from typing import List, Dict
from conffwk import Configuration
from conffwk.dal import DalBase

class ConfigTree:
    '''
    simple class to turn configuration into a tree
    '''
            
    def __init__(self, db: Configuration | str, session_name: str):
        if isinstance(db, str):
            db = Configuration("oksconflibs:" + db)  
        self.db = db
        self.session_name = session_name
        self.session = self.db.get_dal("Session", session_name)
        self._relations_cache = {}
        self._is_disabled_cache = {}
        self._is_nested_cache = {}
        
        self.graph = self.build_tree(self.session)
    
    def _get_relations(self, class_name: str):
        """Cache relations queries to avoid repeated DB calls"""
        if class_name not in self._relations_cache:
            self._relations_cache[class_name] = self.db.relations(class_name, all=True)
        return self._relations_cache[class_name]
    
    def build_tree(self, top_object: DalBase):
        """Iterative tree building using BFS to avoid recursion overhead"""
        graph = {}
        visited = set()
        queue = [top_object]
        
        while queue:
        
            current = queue.pop(0)                
            obj_id = id(current)
            
            if obj_id in visited:
                continue
            visited.add(obj_id)
            
            rels = self._get_relations(current.className())
            related_objects_list = []
            
            for rel in rels:
                related_objects = getattr(current, rel, [])
                
                if related_objects is None:
                    continue
                
                if not isinstance(related_objects, list):
                    related_objects = [related_objects]
                
                related_objects_list.extend(related_objects)
                
                # Add unvisited objects to queue
                for related in related_objects:
                    if id(related) not in visited:
                        queue.append(related)
            
            if related_objects_list:
                graph[current] = related_objects_list
        
        return graph
    
    def _get_parents(self, obj: DalBase):
        """Get all parent objects of the given object in the tree"""
        parents = []
        for parent, children in self.graph.items():
            if obj in children:
                parents.append(parent)
        return parents
    
    def is_disabled(self, obj: DalBase):
        '''
        For resources checks if the resource AND all top level resources are disabled
        other wise just checks if all top level resources are disabled.
        Also checks if all parent objects are disabled.
        '''
        
        obj_id = id(obj)
        if obj_id in self._is_disabled_cache:
            return self._is_disabled_cache[obj_id]
            
        # Otherwise we loop through containing resources
        disabled_dals = [self.is_disabled(d) for d in self.db.get_dals("Resource") if self.is_nested(d, obj) and d!=obj]
        
        disabled = all(disabled_dals) and len(disabled_dals)
        
        if 'Resource' in self.db.superclasses(obj.className(), True) and not disabled:
                disabled = (obj in self.session.disabled) or disabled
        
        # Check if all parent objects are disabled
        if not disabled:
            parents = self._get_parents(obj)
            if parents and all(self.is_disabled(parent) for parent in parents):
                disabled = True
        
        self._is_disabled_cache[obj_id] = disabled
        return disabled

    
    def is_nested(self, obj_a: DalBase, obj_b: DalBase) -> bool:
        ''' Check if obj_b is nested within obj_a using BFS for efficiency '''
        # Create a cache key from object ids
        cache_key = (id(obj_a), id(obj_b))

        if obj_a == obj_b:
            # No need to cache
            return False
        
        if cache_key in self._is_nested_cache:
            return self._is_nested_cache[cache_key]
        
        visited = set()
        queue = [obj_a]
        
        while queue:
            current = queue.pop(0)
            if current == obj_b:
                self._is_nested_cache[cache_key] = True
                return True
            if current in visited:
                continue
            visited.add(current)
            
            # Add direct children to queue
            for related in self.graph.get(current, []):
                if related not in visited:
                    queue.append(related)
        
        self._is_nested_cache[cache_key] = False
        return False
    

class ManagedComponentManager:
    # Here so it's easy to change (but const!)
    __MANAGED_COMPONENT_CLASS="ManagedComponent"

    def __init__(self, db: str | Configuration, session_name: str):
        if isinstance(db, str):
            db = Configuration("oksconflibs:" + db)  
            
        self.db = db
        self.session_name = session_name
        self.session = db.get_dal("Session", session_name)
        
        if not self.session:
            raise ValueError(f"Session '{session_name}' not found in database '{db}'")

        self._managed_components = None
        self._config_tree = None
        self._nested_components = None

    @property
    def managed_components(self)->List[DalBase]:
        """Function to list enabled managed components in the specified OKS database file"""
        if self._managed_components is None:
        
            resources = self.db.get_dals(self.__MANAGED_COMPONENT_CLASS)
            resource_rule = lambda resource: not self.config_tree.is_disabled(resource) and getattr(resource, 'tag', '')!=''
            self._managed_components = [{'dal': r, 'tag': r.tag} for r in resources if resource_rule(r)]

        return self._managed_components
    
    @property
    def config_tree(self)->ConfigTree:
        '''Cache config tree'''
        if self._config_tree is None:
            self._config_tree = ConfigTree(self.db, self.session_name)
        return self._config_tree

    def _find_nested_managed_components(self):
        """Function to check if any of the enabled managed components in the specified OKS database file are nested"""
        if self._nested_components is not None:
            return self._nested_components
        
        tree = self.config_tree
        nested_comps = {c['dal']: [] for c in self.managed_components}
        
        # Cache to avoid duplicate checks
        checked_pairs = set()
        
        # Check if any of the managed components are nested within each other
        for i, comp_a in enumerate(self.managed_components):
            dal_a = comp_a['dal']
            for comp_b in self.managed_components[i+1:]:
                dal_b = comp_b['dal']
                
                # Use object id for hashable set membership
                pair_key = (id(dal_a), id(dal_b))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                if tree.is_nested(dal_a, dal_b):
                    nested_comps[dal_a].append(dal_b)
                elif tree.is_nested(dal_b, dal_a):
                    nested_comps[dal_b].append(dal_a)

        # Now remove all non-nested entries
        self._nested_components = {c: v for c,v in nested_comps.items() if len(v)}
        return self._nested_components

    @property
    def nested_managed_components(self)->Dict[DalBase, List[DalBase]]:
        if self._nested_components is None:
            self._find_nested_managed_components()
        return self._nested_components

    def any_component_nested(self):
        return len(self.nested_managed_components) > 0
