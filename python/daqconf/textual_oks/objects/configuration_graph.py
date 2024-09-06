# Graph of our configuration
from configuration_wrapper import ConfigurationWrapper
import numpy as np
from abc import abstractmethod, ABC
from numpy.typing import NDArray      
from collections import deque      
from tqdm import tqdm

class ConfigurationGraph(ABC):
    def __init__(self, configuration: ConfigurationWrapper) -> None:
        self._configuration = configuration

        self._n_nodes = len(configuration.get_all_dals())
        
        self._adjacency_matrix = np.array([[]])
        self._topological_ordered_matrix = np.array([[]])
        self._top_level_nodes = []
        self._max_distance = []
        self._object_layer = [] # layer each DAL lives on, given by longest path
        self.__generate_adjacency_matrix()
        self.__calculate_longest_paths()

    @abstractmethod
    def _get_connections(self):
        return [[]]
    
    def __generate_adjacency_matrix(self):
        dal_list = self._configuration.get_all_dals()
        dal_connections = self._get_connections()
        
        if len(dal_list)!=len(dal_connections):
            raise ValueError(f"Number of connections is not equal to number of nodes\n {self._n_nodes}!={len(dal_connections)}")
        
        self._adjacency_matrix = np.zeros((self._n_nodes, self._n_nodes))
        
        # We now loop over the connection graph and see what's connected
        for i, connection_list in enumerate(dal_connections):
            
            for connection in connection_list:
                # Assumption is that each dal is unique
                self._adjacency_matrix[i][dal_list.index(connection)] = 1

    def __calculate_longest_paths(self):
        '''
        Idea is to find shortest paths on -G for each top level node where G is the connection graph.
        Layer each item lives on is then simply max(longest_path) for each top level item
        '''
        # Let's make this simple...
        self._max_distance = np.zeros(self._n_nodes)-np.inf
        
        self._topological_ordered_matrix = self.__get_topological_order()
        for node_id in range(self._n_nodes):
            self._max_distance = np.maximum(self._max_distance, self.__longest_path(node_id))


    def __compute_degree(self):
        """Get number of incoming nodes for each node"""
        return np.sum(self._adjacency_matrix !=0, axis=0)
    
    def __get_topological_order(self):
        """Topological sort of the adjacency graph"""
        in_degree = self.__compute_degree()
        queue = deque(np.where(in_degree == 0)[0])
        topological_ordering = []
        
        while queue:
            node = queue.popleft()
            topological_ordering.append(node)
            outgoing_edges = np.where(self._adjacency_matrix != 0)[0]
            in_degree[outgoing_edges] -= 1
            zero_in_degree_nodes = outgoing_edges[in_degree[outgoing_edges] == 0]
            queue.extend(zero_in_degree_nodes)
        
        return topological_ordering
    
    def __update_distances(self, distance: NDArray, node_id: int):
        outgoing_edges = np.where(self._adjacency_matrix[node_id] != 0)[0]
        distance[outgoing_edges] = np.maximum(distance[outgoing_edges], distance[node_id] + self._adjacency_matrix[node_id][outgoing_edges])
        
    def __longest_path(self, start_id: int):
        """Calculate the longest path in a DAG from the start node."""
        dist = np.full(self._n_nodes, -np.inf)
        dist[start_id] = 0

        for u in self._topological_ordered_matrix:
            if dist[u] != -np.inf:
                self.__update_distances(dist, u)
        
        return dist

    def get_graph(self):
        return self._adjacency_matrix
    
    def get_longest_paths(self):
        return self._max_distance
    
# Specific implementation for getting dependencies
class DependencyGraph(ConfigurationGraph):
    def _get_connections(self):
        connections_list = np.empty(len(self._configuration.get_all_dals()), dtype=object)
        for i, dal in enumerate(self._configuration.get_all_dals()):
            connections_list[i] = list(self._configuration.get_relations(dal))
        
        return connections_list


if __name__=="__main__":
    config = ConfigurationWrapper("/home/hwallace/scratch/dune_software/daq/daq_work_areas/fddaq-v5.1.0-a9-1/sourcecode/appmodel/test/config/test-session.data.xml")
    graph = DependencyGraph(config)

    print(graph.get_longest_paths())