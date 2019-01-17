import random
import networkx as nx
import warnings
from dtk.tools.migration.GraphGenerator import GraphGenerator


class SmallWorldGridGraphGenerator(GraphGenerator):
    """
    A geographical graph generator (connectivity depends on the distance between nodes).
    """

    def __init__(self, migration_network_file_path: str, demographics_file_path: str):
        super().__init__(migration_network_file_path, demographics_file_path)
        warnings.warn("SmallWorldGridGraphGenerator is deprecated.", DeprecationWarning)
        self.graph = None

    def generate_graph(self) -> nx.Graph():
        """
        Generate a small world networkx graph on a 2D grid, assuming the following:

        - Assume nodes occupy a subset of points on a regular square 2D grid.
        - You provide **adjacency_list** which specifies the *local* grid
          connections of nodes; the long range links will be automatically added.

            .. note:: You may specify your own local neighborhood per node instead of using related networkx graph implementations.

        - While the networkx implementation of small-world graphs assume ring topology, realistic scenarios are interested in a grid.
        - While the networkx implementation of 2D grid graphs assumes no diagonal edges, we need the ability to get neighbors from a (sub)set of the full neighborhood (of 8 nodes aside from boundary, corner or missing nodes)
        - Because you have likely already generated a lat/lon grid, it is trivial to create the neighborhood generation yourself.
        - Assume that the grid small-world network's non-local/long-range edges are wired for optimal decentralized
          efficiency, which coincides with most of the real-world small-world network examples. That is, the probability p((u,v)) of a an edge from node u to v is given by :math:`p(u,v) ~ d(u,v)^{-2}``, where d(u,v)
          is the topological shortest path length (i.e. hop length) between u and v *on the grid*.
        """

        G = nx.Graph()
        G.position = {}
        G.population = {}
        G.name = {}

        # add nodes
        for node_id, properties in self.node_properties.items():
            G.add_node(node_id)
            G.name[properties[3]] = node_id
            G.population[node_id] = properties[2]
            G.position[node_id] = (properties[0], properties[1])  # (x,y) for matplotlib

        # add provided local links
        nodes = G.nodes()
        if self.adjacency_list:
            for node_id, node_links in self.adjacency_list.items():
                for node_link_id, w in node_links.items():
                    if node_id in nodes and node_link_id in nodes:  # only add an edge between existing nodes
                        G.add_edge(int(node_id), int(node_link_id), weight=w)
        else:
            raise ValueError('SmallWorldGridGraphGenerator requires an adjacency list input!')

        print("Populated small world graph nodes and local edges.")

        # add long range links
        # calculate shortest hops paths and create an edge between two nodes w/ probability proportional to the inverse square of the distance between the two nodes
        # shortest_path_lengths = nx.shortest_path_length(G, weight = 'weight').items()
        # for src_id, dst_records in shortest_path_lengths:
        # 	for dst_id, dist in dst_records.items():
        # 		if dist > 0:
        # 			if random.uniform(0,1) <= pow(dist, -2): # need to calculate normalization constant!
        # 				G.add_edge(src_id, dst_id)

        # go over isolated nodes and add edges to a random node; can be more realistic and add edges based on distance; but for now that should suffice to get a connected network
        # note that this does not create a fully connected network but a set of connected components with no isolated nodes
        for iso_node in nx.isolates(G):
            G.add_edge(iso_node, nodes[int(len(nodes) * random.uniform(0, 1))])

        print("Generated long links' connections.")

        self.graph = G

        return G

    def get_shortest_paths(self):
        """
        Get shortest paths based on link weights.
        
        Returns:
            The shortest paths.
        """
        return nx.shortest_path_length(self.graph, weight='weight')

