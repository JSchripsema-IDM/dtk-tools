import itertools
from math import radians, cos, sin, asin, sqrt
import warnings

import networkx as nx

from dtk.tools.migration.GraphGenerator import GraphGenerator


class GeoGraphGenerator(GraphGenerator):
    """
    A geographical graph generator (connectivity depends on the distance between nodes).
    A future refactor may have a number graph generator types implementing a generic interface GraphTopoGenerator.

    """

    def __init__(self, migration_network_file_path: str, demographics_file_path: str, migration_radius=2):
        """

        Args:
            migration_network_file_path: The path to migration network file.
            demographics_file_path: The path to the demographics file.
            migration_radius: How far people would travel on foot in units of neighborhood hops; 1 is equal to the 8 adjacent nodes, 2 is equal to 24 adjacent nodes.
        """
        super().__init__(migration_network_file_path, demographics_file_path)
        warnings.warn("GeoGraphGenerator is deprecated.", DeprecationWarning)

        self.migration_radius = migration_radius

    def generate_graph(self) -> nx.Graph():
        """
        Generate a networkx graph based on distances between vertices.

        Returns:
            A networkx graph.
        """

        G = nx.Graph()
        G.position = {}
        G.population = {}
        G.name = {}

        for node_id, properties in self.node_properties.items():
            G.add_node(node_id)
            G.name[properties[3]] = node_id
            G.population[node_id] = properties[2]
            G.position[node_id] = (properties[0], properties[1])  # (x,y) for matplotlib

        # add an edge between any two nodes distanced less than max_kms away

        for n in itertools.combinations(G.nodes(), 2):
            distance = self.get_haversine_distance(G.position[n[0]][0], G.position[n[0]][1], G.position[n[1]][0],
                                                   G.position[n[1]][1])
            if not self.migration_radius or distance < self.migration_radius:
                G.add_edge(n[0], n[1], weight=distance)

        # add edge based on adjacency matrix
        for node_id, node_links in self.adjacency_list.items():
            for node_link_id, w in node_links.items():
                distance = self.get_haversine_distance(G.position[int(node_id)][0], G.position[int(node_id)][1],
                                                       G.position[int(node_link_id)][0],
                                                       G.position[int(node_link_id)][1])
                G.add_edge(int(node_id), int(node_link_id), weight=distance * w)

        self.graph = G

        return G

    def get_shortest_paths(self):
        """
        Get the shortest paths based on link weights.

        Returns:
            Float value of shortest path.
        """

        return nx.shortest_path_length(self.graph, weight='weight')

    @staticmethod
    def get_haversine_distance(lon1, lat1, lon2, lat2) -> float:
        """
        Calculate the great circle distance between two points on the earth (specified in decimal degrees).
        
        Args:
            lon1: Longitude for point 1.
            lat1: Latitude for point 1.
            lon2: Longitude for point 2.
            lat2: Latitude for point 2.

        Returns:
            Float value of haversine distance.
        """

        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))

        # 6367 km is the radius of the Earth
        km = 6367 * c

        return km
