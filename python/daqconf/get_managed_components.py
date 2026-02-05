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
        
        self.graph = self.build_tree(self.session)
    
    def build_tree(self, top_object: DalBase, graph=None):
        if graph is None:
            graph = {}
        
        rels = self.db.relations(top_object.className(), all=True)
        for rel in rels:            
            related_objects = getattr(top_object, rel, [])
            
            if related_objects is None:
                continue
            
            if not isinstance(related_objects, list):
                related_objects = [related_objects]
            graph[top_object] = related_objects
            for related in related_objects:
                graph.update(self.build_tree(related, graph))

        return graph
    
    def get_object_subtree(self, dal: DalBase):
        '''Get sub-tree with dal at the top'''
        subtree = {dal: self.graph.get(dal, [])}
        for related in self.graph.get(dal, []):
            subtree.update(self.get_object_subtree(related))
        return subtree
    
    def is_nested(self, obj_a: DalBase, obj_b: DalBase) -> bool:
        ''' find obj_a in the graph and then check if obj_b is nested in it
        '''
        subtree = self.get_object_subtree(obj_a)
        # Check all objects in the subtree (both keys and values)
        for key in subtree:
            if key == obj_b:
                return True
            for related in subtree[key]:
                if related == obj_b:
                    return True
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
        
        if not session:
            raise ValueError(f"Session '{session_name}' not found in database '{db}'")

        self._managed_components = None
        self._config_tree = None
        self._nested_components = None

    @property
    def managed_components(self)->List[DalBase]:
        """Function to list enabled managed components in the specified OKS database file"""
        if self._managed_components is None:
        
            resources = self.db.get_dals(self.__MANAGED_COMPONENT_CLASS)

            resource_rule = lambda resource: not resource in self.session.disabled and getattr(resource, 'tag', '')!=''
            self._managed_components = [(r, r.tag) for r in resources if resource_rule(r)]

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
        
        nested_comps = {c[0]: [] for c in self.managed_components}
        
        # Check if any of the managed components are nested within each other
        for i, comp_a in enumerate(self.managed_components):
            for comp_b in self.managed_components[i+1:]:
                if tree.is_nested(comp_a[0], comp_b[0]):
                    nested_comps[comp_a].append(comp_b)
        
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

if __name__=='__main__':
    import sys
    
    config_path = sys.argv[1]
    session = sys.argv[2]
    
    if len(sys.argv)!=3:
        raise Exception("usage: <blah> config_path session")
    
    mgr = ManagedComponentManager(config_path, session)
    
    print(f"Checking {config_path}")
    print(f"Managed components: {mgr.managed_components}")
    print(f"Nested managed components: {mgr.nested_managed_components}")
