'''
HW : Simple wrapper to go around configuration object
'''
import os
import conffwk 
from typing import Any, Dict, List


class ConfigurationHandler:
    # Contains the full configuration of a single configuration instance
    def __init__(self, configuration_file_name: str):
        self._configuration = self.__open_configuration(configuration_file_name)
        self._loaded_dals = []
    self.__cache_all_conf_objects()
        
    def __open_configuration(self, configuration_file_name: str)->conffwk.Configuration:
        '''Opens configuration object safely '''
        if not os.path.isfile(configuration_file_name):
            raise Exception(f"Cannot open {configuration_file_name}")
        
        try:
            configuration = conffwk.Configuration(f"oksconflibs:{configuration_file_name}")
        except Exception as e:
            raise e 

        return configuration
    
    def __cache_all_conf_objects(self)->None:
        # Adds all configuration objects to 
        for conf_class in  self._configuration.classes():
            for conf_obj in self._configuration.get_dals(conf_class):                
                if conf_obj ing self._loaded_dals: continue
                
                self._loaded_dals.append(conf_obj)

    #==============================  Getters + Setters ==============================#
    def get_relationships_for_conf_object(self, conf_object)->List[Any]:
        relations = self.get_related_classes(conf_object.className())

        relations_list = []
                
        for rel in relations:
            rel_val = getattr(conf_object, rel)
            # Hacky but pybind got fussy about casting
            if not isinstance(rel_val, list):
                rel_val = [rel_val]

            for v in rel_val:
                if v is None: continue
            
                relations_list.append(v)

        return relations_list
    
    def get_conf_objects_class(self, conf_class: str):
        return self._configuration.get_dals(conf_class)
        
    def get_all_conf_classes(self)->Dict[str, Any]:
        return {conf_class: self.get_conf_objects_class(conf_class)
                for conf_class in self._configuration.classes()}
    
    def get_related_classes(self, class_id: str)->List[str]:
        related_classes = [class_ for class_ in self._configuration.relations(class_id, True).keys()]
        return related_classes
        
    def get_inherited_classes(self, class_id: str)->List[str]:
        inherited_classes = [class_ for class_ in self._configuration.classes()\
                                if self._configuration.is_subclass(class_, class_id)]
        return inherited_classes            

    
    @property
    def configuration(self)->conffwk.Configuration:
        return self._configuration
    
    @configuration.setter
    def configuration(self)->None:
        # Dunder method in case I try to do something silly
        raise NotImplementedError(f"Configuration object is not mutable, please create new object")
    
    @property
    def conf_obj_list(self):
        return self._loaded_dals
    
    def get_obj(self, class_id: str, uid: str):
        return self.configuration.get_obj(class_id, uid)
    
    def commit(self, update_message: str):
        self.configuration.commit(update_message)

    @property
    def n_dals(self)->int:
        return len(self._loaded_dals)
    
    def add_new_conf_obj(self, class_id: str, uid: str):
        self.configuration.create_obj(class_id, uid, at=self.configuration.active_database)
        config_as_dal = self.configuration.get_dal(class_id, uid)
        self.configuration.update_dal(config_as_dal)
        self._loaded_dals.append(config_as_dal)

    def destroy_conf_obj(self, class_id: str, uid: str):
        dal = self.configuration.get_dal(class_id, uid)
        self.configuration.destroy_dal(dal)
        self._loaded_dals.remove(dal)