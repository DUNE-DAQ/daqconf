'''
Extended explanation of the RelationalGraph class:

The RelationalGraph class is used to generate a graph of the relationships between the DALs in the configuration file.
The class is used to generate a topological ordering of the DALs, and to calculate the longest path in the graph.
The reasoning is that the configuration should naturally group similar objects together based on how far they are from the system object

Current this is only really used to find "top level" objects

'''

import numpy as np
from numpy.typing import NDArray
from collections import deque

from daqconf.textual_dbe.data_structures.configuration_handler import ConfigurationHandler

class RelationalGraph:
    def __init__(self, config_handler: ConfigurationHandler):
        """Construct relational graph

        Arguments:
            config_handler -- ConfigurationHandler object
        """        

        # Configuration handler
        self._handler = config_handler
        self.generate_graph()
        
    def generate_graph(self):
        # Matrices etc. we require [maybe don't need to be defined at the constructor level, could be
        # class methods]
        self._topological_ordered_matrix = np.array([[]])

        # Adjacency matrix has 1 for direct connection, 0 for no connection
        self._adjacency_matrix = np.zeros((self._handler.n_dals, self._handler.n_dals))
        # Maximum distance from the "top level" to a given node
        self._max_distance = np.zeros(self._handler.n_dals)-np.inf

        # Generate the graph
        self.__generate_adjacency_matrix()
        # Sort topologically and get longest paths
        self.__calculate_longest_paths()

            
    def __generate_adjacency_matrix(self):
        """Generates adjacency matrix from configuration handler object i.e. finds connected DALs
        """
        for i, dal in enumerate(self._handler.conf_obj_list):
            for connection_category in self._handler.get_relationships_for_conf_object(dal):
                # Allows for multiply connected nodes
                for connection in list(connection_category.values())[0]:
                    # Loop over just conf objects
                    self._adjacency_matrix[i][self._handler.conf_obj_list.index(connection)] += 1
                    
    
    def __compute_degree(self):
        """Get number of incoming nodes for each node"""
        return np.sum(self._adjacency_matrix !=0, axis=0)
    
    def __get_topological_order(self):
        """
        Topological sort of the adjacency graph
        
        Algorithm implementation roughly based on: https://en.wikipedia.org/wiki/Topological_sorting#Kahn's_algorithm
        
        """
        in_degree = self.__compute_degree()
        queue = deque(np.where(in_degree == 0)[0])
        topological_ordering = []
        
        while queue:
            node = queue.popleft()
            # Add node to topological ordering
            topological_ordering.append(node)
            # Check out going edges
            outgoing_edges = np.where(self._adjacency_matrix != 0)[0]
            # Reduce the number of incoming edges for each outgoing edge
            in_degree[outgoing_edges] -= 1
            # Change the number of nodes with no outgoing edges
            zero_in_degree_nodes = outgoing_edges[in_degree[outgoing_edges] == 0]
            # Add to the queue
            queue.extend(zero_in_degree_nodes)
        
        return topological_ordering
    
    def __update_distances(self, distance: NDArray, node_id: int):
        """Update maximum distance to each node

        Arguments:
            distance -- List of distancezs to each node
            node_id -- ID of a node
        """        
        outgoing_edges = np.where(self._adjacency_matrix[node_id] != 0)[0]
        distance[outgoing_edges] = np.maximum(distance[outgoing_edges], distance[node_id] + self._adjacency_matrix[node_id][outgoing_edges])
        
    def __longest_path(self, start_id: int):
        """Calculate the longest path in a DAG from the start node."""
        dist = np.full(self._handler.n_dals, -np.inf)
        dist[start_id] = 0

        for u in self._topological_ordered_matrix:
            if dist[u] != -np.inf:
                self.__update_distances(dist, u)
        return dist
    
    def __calculate_longest_paths(self)->None:
        '''
        Idea is to find shortest paths on -G for each top level node where G is the connection graph.
        Layer each item lives on is then simply max(longest_path) for each top level item
        '''
        
        self._topological_ordered_matrix = self.__get_topological_order()
        for node_id in range(self._handler.n_dals):
            self._max_distance = np.maximum(self._max_distance, self.__longest_path(node_id))

        self._max_distance = self._max_distance.astype(int)
    
    @property
    def top_level_nodes(self):
        return [dal for i, dal in enumerate(self._handler.conf_obj_list) if self._max_distance[i]==0]
    
    
    