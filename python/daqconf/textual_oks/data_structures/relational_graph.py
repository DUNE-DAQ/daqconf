'''
Slightly abstract graph object, used for relational depedencies
'''

import numpy as np
from numpy.typing import NDArray
from textual_oks.data_structures.configuration_handler import ConfigurationHandler
from collections import deque
from typing import List

class RelationalGraph:
    def __init__(self, config_handler: ConfigurationHandler):

        # Setup various useful objects
        self._handler = config_handler
        
        # Matrices etc. we require [maybe don't need to be defined at the constructor level, could be
        # class methods]
        self._topological_ordered_matrix = np.array([[]])

        self._adjacency_matrix = np.zeros((self._handler.n_dals, self._handler.n_dals))
        self._max_distance = np.zeros(self._handler.n_dals)-np.inf


        self.__generate_adjacency_matrix()
        self.__calculate_longest_paths()
        
    
    # Need to generate a graph
    def __generate_adjacency_matrix(self):
        for i, dal in enumerate(self._handler.conf_obj_list):
            for connection in self._handler.get_relationships_for_conf_object(dal):
                # Allows for multiply connected nodes
                self._adjacency_matrix[i][self._handler.conf_obj_list.index(connection)] += 1
    
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
        # Let's make this simple...
        
        self._topological_ordered_matrix = self.__get_topological_order()
        for node_id in range(self._handler.n_dals):
            self._max_distance = np.maximum(self._max_distance, self.__longest_path(node_id))

        self._max_distance = self._max_distance.astype(int)
    
    @property
    def top_level_nodes(self):
        return [dal for i, dal in enumerate(self._handler.conf_obj_list) if self._max_distance[i]==0]