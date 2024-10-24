"""
Structed configuration object. Effectively just a ConfigurationHandler with combined with a graph
"""

from daqconf.cider.data_structures.configuration_handler import ConfigurationHandler
from daqconf.cider.data_structures.relational_graph import RelationalGraph

class StructuredConfiguration:
    def __init__(self, configuration_file_name: str):
        """Structured configuration object, essentially a wrapper around a 
        ConfigurationHandler object and a RelationalGraph object. 
        
        Provides access to both the configuration and its relational structure

        Arguments:
            configuration_file_name -- name of the configuration .database.xml file to open
        """        
        self._configuration_handler = ConfigurationHandler(configuration_file_name)
        self._relational_graph = RelationalGraph(self._configuration_handler)
        
    @property
    def configuration_handler(self)->ConfigurationHandler:
        return self._configuration_handler
    
    @property
    def relational_graph(self)->RelationalGraph:
        return self._relational_graph
    