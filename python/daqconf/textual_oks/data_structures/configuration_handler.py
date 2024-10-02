import os
from typing import Any, Dict, List

import conffwk 


class ConfigurationHandler:
    # Contains the full configuration of a single configuration instance
    def __init__(self, configuration_file_name: str):
        """Configuration handler object, essentially a wrapper around a conffwk.Configuration object

        Arguments:
            configuration_file_name -- name of the configuration .database.xml file to open
        """        
        
        # Load configuration
        self._configuration = self.__open_configuration(configuration_file_name)
        
        # To be filled with ALL config objects (as DALs)
        self._loaded_dals = []
        # Fills self._loaded_dals,
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
        """Adds all loaded dals to self._loaded_dals
        """
        for conf_class in  self._configuration.classes():
            for conf_obj in self._configuration.get_dals(conf_class):                
                if conf_obj in self._loaded_dals: continue
                
                self._loaded_dals.append(conf_obj)

    #==============================  Getters + Setters ==============================#
    def get_relationships_for_conf_object(self, conf_object)->List[Any]:
        """For a given configuration object, return all related objects

        Arguments:
            conf_object -- Any DAL object

        Returns:
            _description_
        """        
        relations = self.get_related_classes(conf_object.className())

        relations_list = []
        
        # Loop over relations                
        for rel in relations:
            rel_val = getattr(conf_object, rel)
            # Hacky but pybind got fussy about casting list(dal)
            if not isinstance(rel_val, list):
                rel_val = [rel_val]

            # Loop over sub-relations
            for v in rel_val:
                if v is None: continue
            
                relations_list.append(v)

        return relations_list
    
    def get_conf_objects_class(self, conf_class: str):
        """Get all configuration objects of a given class

        Arguments:
            conf_class -- Coniguration class to get objects of

        Returns:
            List of configuration objects of the given class
        """        
        return self._configuration.get_dals(conf_class)
        
    def get_all_conf_classes(self)->Dict[str, Any]:
        """Gets all classes + objects of that class in the configuration

        Returns:
            dictionary of class : dal objects
        """        
        return {conf_class: self.get_conf_objects_class(conf_class)
                for conf_class in self._configuration.classes()}
    
    def get_related_classes(self, class_id: str)->List[str]:
        """Get all related to classes to a given input class

        Arguments:
            class_id -- Name of class

        Returns:
            List of all related classses
        """        
        related_classes = [class_ for class_ in self._configuration.relations(class_id, True).keys()]
        return related_classes
        
    def get_inherited_classes(self, class_id: str)->List[str]:
        inherited_classes = [class_ for class_ in self._configuration.classes()\
                                if self._configuration.is_subclass(class_, class_id)]
        return inherited_classes            

    
    @property
    def configuration(self)->conffwk.Configuration:
        """Access the underlying configuration object
        """        
        return self._configuration
    
    @configuration.setter
    def configuration(self)->None:
        """Dunder method in case I try to do something silly

        """
        raise NotImplementedError(f"Configuration object is not mutable, please create new object")
    
    @property
    def conf_obj_list(self):
        """List of loaded in dals
        """        
        return self._loaded_dals
    
    def get_obj(self, class_id: str, uid: str):
        """Get a particular configuration object 

        Arguments:
            class_id -- Class name
            uid -- Unique object ID

        Returns:
            DAL object satisfying the input
        """        
        return self.configuration.get_obj(class_id, uid)
    
    def commit(self, update_message: str):
        """Commit changes to the database

        Arguments:
            update_message -- Add message to the update
        """        
        self.configuration.commit(update_message)

    @property
    def n_dals(self)->int:
        """Lists the total number of loaded objects
            _description_
        """        
        return len(self._loaded_dals)
    
    def add_new_conf_obj(self, class_id: str, uid: str):
        """Add new configuration object

        Arguments:
            class_id -- Class name
            uid -- Unique object ID
        """        
        self.configuration.create_obj(class_id, uid, at=self.configuration.active_database)
        config_as_dal = self.configuration.get_dal(class_id, uid)
        self.configuration.update_dal(config_as_dal)
        self._loaded_dals.append(config_as_dal)

    def destroy_conf_obj(self, class_id: str, uid: str):
        """Destroy a configuration object

        Arguments:
            class_id -- class name
            uid -- unique object ID
        """
        dal = self.configuration.get_dal(class_id, uid)
        self.configuration.destroy_dal(dal)
        self._loaded_dals.remove(dal)