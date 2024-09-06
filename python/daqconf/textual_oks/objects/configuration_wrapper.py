'''
Lets start by abstracting what we mean by a database
'''
import os
import conffwk

class ConfigurationWrapper:
        
    def __init__(self, database_file_name: str):
        self._open_database(database_file_name)
        
        self._relations_dict = {}
        self._loaded_dals = [] # Contains all DALS loaded that we care about
    
    def _open_database(self, database_file_name: str):
        if not os.path.isfile(database_file_name):
            raise Exception(f"Cannot open {database_file_name}")
        
        try:
            self._configuration = conffwk.Configuration(f"oksconflibs:{database_file_name}")
        except Exception as e:
            raise e 

    def get_kernel(self):
        return self._configuration

    def get_dal(self, class_name: str, uid_name: str):
        # Get individual dal object
        try:
            dal = self._configuration.get_dal(class_name, uid_name)                
            return dal
            
        except Exception as e:
            raise e

    def get_relations(self, input_dal):
        relations = self._configuration.relations(input_dal.className(), True)
        # Relations are potentially grouped 
        relations_list = []
        for rel_id in relations.keys():
            
            # Convert to list so it can be iterated over
            rel_val = getattr(input_dal, rel_id)
            
            if not isinstance(rel_val, list):
                rel_val = [rel_val]
            
            for r in rel_val:
                if r is None: continue
            
                # Gets dals? Do we want the dal?
                relations_list.append(r)
                
        return relations_list
        
    def load_all_dals(self):
        """
        Fills list with all dal objects, 
        to avoid multiple copies has check to ensure dal not in list
        """
        for class_ in self._configuration.classes():
            for class_instance in self._configuration.get_objs(class_):
                # This is dumb and I hate it but it makes things ✨nicer✨
                dal = self.get_dal(class_instance.class_name(), class_instance.UID())
                if dal not in self._loaded_dals:
                    self._loaded_dals.append(dal)
    
    def get_all_dals(self):
        if not self._loaded_dals:
            self.load_all_dals()
            
        return self._loaded_dals
    
    def get_all_relations(self):
        if not len(self._loaded_dals):
            self.load_all_dals()
        
        # Map from DAL to relations, only fill if it's empty
        if not self._relations_dict:
            self._relations_dict = {dal : self.get_relations(dal) for dal in self._loaded_dals}
        
        return self._relations_dict
        

if __name__=="__main__":
    x= ConfigurationWrapper("/home/hwallace/scratch/dune_software/daq/daq_work_areas/fddaq-v5.1.0-a9-1/sourcecode/appmodel/test/config/test-session.data.xml")
    u = x.get_all_relations()    
    
