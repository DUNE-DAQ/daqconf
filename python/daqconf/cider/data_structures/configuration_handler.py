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
            raise Exception(f"Cannot find file:  {configuration_file_name}")
        
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
            List of related objects
        """        
        relations =  self.get_related_classes(conf_object.className())

        relations_list = []
        
        # Loop over relations                
        for rel, rel_info in relations.items():
            rel_val = getattr(conf_object, rel)
            # Hacky but pybind got fussy about casting list(dal)
            if not isinstance(rel_val, list):
                rel_val = [rel_val]

            relations_list.append({rel: [v for v in rel_val if v is not None], 'rel_info': rel_info})

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
        return self._configuration.relations(class_id, True)
        
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
        """dummy method in case I try to do something silly
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
        
    def modify_relationship(self, class_id, uid, relationship_name: str, updated_value,
                            append: bool=False):
        """Modify TODO: EDIT THIS

        :param class_id: _description_
        :type class_id: _type_
        :param uid: _description_
        :type uid: _type_
        :param relationship_name: _description_
        :type relationship_name: str
        :param updated_value: _description_
        :type updated_value: _type_
        :param append: _description_, defaults to False
        :type append: bool, optional
        """
        # Firstly we need to find the relationship this is referring to
        selected_dal = self.configuration.get_dal(class_id, uid)
        # Okay need a better way of doing this...
        rel_list = self.get_relationships_for_conf_object(selected_dal)
        
        for relations in rel_list:
            # Need to find our dal
            if list(relations.keys())[0] != relationship_name:
                continue
            
            # Next we need to check the type of our object is okay
            if updated_value not in self.get_conf_objects_class(relations['rel_info']['type']):
                raise Exception(updated_value)
                # raise TypeError(f"Cannot use object {updated_value} for relation expecting type {relations['rel_info']['type']}")
            
            # Need to make sure everything is typed correctly
            if append and relations['rel_info']['multivalue']:
                rel = list(relations.items)[0]
                rel.append(updated_value)
            
            elif relations['rel_info']['multivalue']:
                rel = [updated_value]
            else:
                rel = updated_value

            # Should update the dal 
            setattr(selected_dal, relationship_name, rel)
            self.configuration.update_dal(selected_dal)
            
            
            return
        
        raise RuntimeError(f"Cannot find relationship with name {relationship_name}")