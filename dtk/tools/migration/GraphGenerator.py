import abc
import csv
import json
import os
from typing import Union, TextIO, Tuple
import networkx as nx
import matplotlib.pyplot as plt


def generate_node_properties(demographics_file_path: str) -> Tuple[dict, dict]:
    """
    Generate a node label to EMOD ID lookup and a list of dictionary of select node properties
    needed for building graphs.

    Args:
        demographics_file_path: The path to the demographics file. 

    Returns:
        The **node_label_2_id** map and **node_properties** dictionary.

    """
    node_label_2_id = {}
    node_properties = {}
    with open(demographics_file_path, 'r') as demo_f:
        demographics = json.load(demo_f)
        nodes = demographics['Nodes']
        for node in nodes:
            node_attributes = node['NodeAttributes']

            node_properties[int(node['NodeID'])] = [float(node_attributes['Longitude']),
                                                    float(node_attributes['Latitude']),
                                                    int(node_attributes['InitialPopulation']),
                                                    node_attributes['FacilityName']]

            node_label_2_id[node_attributes['FacilityName']] = int(node['NodeID'])

    return node_label_2_id, node_properties


def read_csv_migration_network_file(migration_network_file: TextIO) -> dict:
    """
    Read a CSV migration file and converts it into an adjacency list that can be used by GraphGenerators.

    Args:
        migration_network_file: A file-like object that is read from. Must be in the following format::
            
            node_label 1,  2,  3,  4,  5
            1     w11 w12  w13 w14 w15
            2     w21       ...
            3     w31       ...
            4     w41       ...
            5     w51       ...

    Returns:
        A dictionary representing the network **adjacency_list**.
    """

    reader = csv.DictReader(migration_network_file)

    # assume a node is not connected to itself
    adjacency_list = {}

    for row in reader:
        node = row['node_label']
        adjacency_list[node] = {}
        node_connections = row.keys()[1:]

        # if graph is undirected; csv matrix should be symmetric and this should work
        for node_connection in node_connections:
            adjacency_list[node][node_connection] = row[node_connection]
    return adjacency_list


class GraphGenerator(object):
    def __init__(self, migration_network_file_path: str, demographics_file_path: Union[str, None] = None,
                 node_label_2_id: Union[dict, None] = None,
                 node_properties: Union[dict, None] = None):
        """
        Generate the graph of the nodes used in migration.

        Args:
            migration_network_file_path: The path to the migration network file.

            The file should be in the following format::
            
                {
                    "node_id1": {
                                    #key         # weight
                                    "node_id2": 0.5,
                                    "node_id4": 0.4,
                                    "node_id3": 0.4,
                                    "node_id5": 1,
                                    ...
                                  },

                    "node_id2": {
                                    #key         # weight
                                    "node_id2": 0.4,
                                    "node_id3": 0.4,
                                    "node_id10": 1,
                                    ...
                                  },
                    ...
                }
                
            demographics_file_path: The path to the demographics file. Used to extract the node properties and the build the node **label_2_id** array.
            node_label_2_id: Optional, dictionary that maps node IDs to labels. If the **demographics_file_path**, is specified this is ignored. You must also specify the **node_properties** when providing **node_label_2_id**.
            node_properties: Optional, dictionary that specifies the node properties. If the **demographics_file_path** is specified, this is ignored. You must also specify **node_label_2_id** with this parameter.
        """
        self.migration_network_file_path = migration_network_file_path

        if all([x is None for x in [node_label_2_id, node_properties, demographics_file_path]]):
            raise ValueError("Either the node properties and a node label to id map are required or a "
                             "demographics file ")

        if demographics_file_path:
            self.node_properties, self.node_label_2_id = generate_node_properties(demographics_file_path)
        else:
            self.node_properties = node_label_2_id
            self.node_label_2_id = node_properties
        self.adjacency_list = self.load_migration_network_file()
        self.graph = None

    def load_migration_network_file(self) -> dict:
        """
        Load a migration network file into an adjacency list. The file is read from **migration_network_file_path** that
        was passed in during the initialization of the class. The the input file contains '.csv', it is read in
        using **read_csv_migration_network_file**. if the input file contains '.json' in its name, the migration file is loaded from a JSON file.

        Returns:
            None.
        """
        with open(self.migration_network_file_path, 'r') as mig_f:

            if '.csv' in self.migration_network_file_path.lower():
                return read_csv_migration_network_file(mig_f)

            elif '.json' in self.migration_network_file_path.lower():
                # convert the adjacency list node labels to the corresponding dtk ids from the demographics file,
                # so that the adjacency list can be consumed downstream (e.g. see class GeoGraphGenerator)
                # note that nodes that are in the adjacency list but not in the demographics will be filtered out
                json_data = json.load(mig_f)
                return self.extract_dtk_adjacency_list(json_data)
            else:
                raise ValueError("Unknown Migration Network File Format. Please provide the file in either"
                                 " csv or json format.")

    def extract_dtk_adjacency_list(self, src: dict) -> dict:
        """
        Convert the input dictionary into an EMOD adjacency list by matching node labels to EMOD IDs.

        Args:
            src: Adjacency list by node label. For example::
            
                    {
                    "node_label1": {
                                    #key         # weight
                                    "node_label2": 0.5,
                                    "node_label4": 0.4,
                                    "node_label3": 0.4,
                                    "node_label5": 1,
                                    ...
                                  },

                    "node_label2": {
                                    #key         # weight
                                    "node_label1": 0.4,
                                    "node_label3": 0.4,
                                    "node_label10": 1,
                                    ...
                                  },
                    ...
                    }
            
        Returns:
            An adjacency list by EMOD node ID.

        """
        adj_list_dtk_node_ids = {}
        for src_node_label, dst_records in src.items():
            if src_node_label not in self.node_label_2_id:
                continue
            src_node_id = self.node_label_2_id[src_node_label]

            adj_list_dtk_node_ids[src_node_id] = {}
            for dst_node_label, w in dst_records.items():
                if dst_node_label not in self.node_label_2_id:
                    continue
                dst_node_id = self.node_label_2_id[dst_node_label]
                adj_list_dtk_node_ids[src_node_id][dst_node_id] = w
        return adj_list_dtk_node_ids

    @abc.abstractmethod
    def generate_graph(self) -> nx.Graph():
        """
        Build the a networkx graph object from the specified topology,  **migration_network_file**.

        Returns:
            The generated graph object.
        """
        pass

    def get_topology(self) -> nx.Graph():
        """
        Return the previously generated graph object.

        Returns: 
            The previously generated graph. Is the graph has not been generated, this will return None.

        """
        return self.graph

    @abc.abstractmethod
    def get_shortest_paths(self):
        pass

    def save_migration_graph_topo_visualization(self, output_dir):
        self.get_topology()
        graph = self.get_topology()

        pos = {}
        node_sizes = []
        max_marker = 400

        # following loops are not most efficient given networx graph data struct

        # find max pop
        max_pop = 0.0
        for i, node_id in enumerate(graph.nodes(data=False)):
            pop = graph.population[node_id]
            if pop > max_pop:
                max_pop = pop

        # calculate node sizes for figure
        for i, node_id in enumerate(graph.nodes(data=False)):
            pos[node_id] = graph.position[node_id]  # assume a graph topo has nodes positions and populations
            node_sizes.append(max_marker * graph.population[node_id] / max_pop)

        nx.draw_networkx(graph, pos, with_labels=False, node_size=node_sizes, alpha=0.75, node_color='blue')

        plt.savefig(os.path.join(output_dir, "migration_network_topo.png"), bbox_inches="tight")
        plt.close()
