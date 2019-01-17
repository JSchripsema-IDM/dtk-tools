import json
import logging
import os
from enum import Enum
from struct import pack
from typing import Union, Tuple, List
from dtk.tools.climate.BaseInputFile import BaseInputFile


class MigrationTypes(Enum):
    """
    Enum that lists the supported migration types.
    """
    local = 'local'
    sea = 'sea'
    regional = 'regional'
    air = 'air'

    def __str__(self):
        return self.value


# Define the max destinations(connections) depending on the migration type within the DTK
# max destinations is 100 for any migration type
MAX_DESTINATIONS_BY_ROUTE = {
    MigrationTypes.local: 100,
    MigrationTypes.regional: 100,
    MigrationTypes.sea: 100,
    MigrationTypes.air: 100
}

logger = logging.getLogger(__name__)


class MigrationFile(BaseInputFile):
    """
    Methods to create migration files for use with EMOD.
    """

    def __init__(self, idref, matrix):
        """
        Initialize a MigrationFile.

        Args:
            idref: The ID reference.
            matrix: The migration matrix must be in the following format::

                {
                   node_source1: {
                      node_destination_1: rate,
                      node_destination_2: rate
                    }
                }
        """
        super(MigrationFile, self).__init__(idref)
        self.idref = idref
        self.matrix = matrix

    @staticmethod
    def flatten_matrix(matrix) -> List[Tuple[int, int, float]]:
        """
        Flatten a migration matrix into a series of rows in the following format::
            
            [
                src_node_id1, dest_node_id_1, rate
                src_node_id1, dest_node_id_2, rate
                .....
            ]
        
        Args:
            matrix: The matrix to flatten. Must be in the following format::
                
                {
                   "node_source1": {
                      "node_destination_1": rate,
                      "node_destination_2": rate
                    }
                }
                

        Returns:
            A series of rows describing the migration patterns.
        """
        items: List[Tuple[int, int, float]] = []
        for src, v in matrix.items():
            for dest, mig in v.items():
                items.append((int(src), int(dest), mig))
        return items

    def save_as_txt(self, rates_txt_file_path: str):
        """
        Save the migration file to a human-readable format.

        Args:
            rates_txt_file_path: The path where the migration text file will be saved.
        Returns:
            None
        """
        with open(rates_txt_file_path, 'w') as fout:
            items = self.flatten_matrix(self.matrix)
            for src, dest, mig in items:
                fout.write('%d %d %0.1g\n' % (int(src), int(dest), mig))

    def load_from_text(self, rates_txt_file_path: str):
        """
        Load files from human-readable text files generated from :py:meth:`save_as_txt` into the matrix.

        Args:
            rates_txt_file_path: The path to the migration text file.
        Returns:
            None
        """
        with open(rates_txt_file_path) as fopen:
            self.matrix = {}
            lines = [l.strip() for l in fopen.readlines()]

            for id1, id2, rate in lines:
                if id1 not in self.matrix:
                    self.matrix[id1] = {}

                self.matrix[id1][id2] = rate

    def generate_file(self, migration_bin_file_path: str, route: Union[MigrationTypes, None] = None,
                      migration_header_file_path: Union[str, None] = None,
                      compiled_demographics_file_path: Union[str, None] = None):
        """
        Convert the input into an EMOD binary migration file.

        Args:
            migration_bin_file_path: The location to save the migration binary file.
            route: The route (**MigrationType**) to apply to the generated file. When set, this will take into account the MAX_DESTINATIONS_BY_ROUTE for the selected **MigrationType**.
            migration_header_file_path: Optional, the path where the migration header file will be saved. The default value is <migration_bin_file_path>.json.
            compiled_demographics_file_path: Optional, the path to the compiled demographics file. If included, the **creationmigrationheader** tool saves the migration header; otherwise, a simpler header is used. 
        Returns:
            None
        """

        # Before generating, transform the matrix
        matrix_id = self.nodes_to_id()

        offset = 0
        offset_str = ""

        # Make sure we have the same destinations size everywhere
        # First find the max size
        max_size = max([len(dest) for dest in matrix_id.values()])

        # Add a fake node destinations in nodes to make sure the destinations are all same size
        for source, dests in self.matrix.items():
            self.get_filler_nodes(source, dests, max_size, matrix_id.keys())

        with open(migration_bin_file_path, 'wb') as migration_file:
            max_destinations = 0
            for nodeid, destinations in matrix_id.items():
                if route is not None:
                    if len(destinations) > MAX_DESTINATIONS_BY_ROUTE[route]:
                        logger.warning(f'There are {len(destinations)} destinations from ID={nodeid}.  Trimming '
                                       f'to {MAX_DESTINATIONS_BY_ROUTE[route]} {route.value} migration max) with '
                                       f'largest rates.')

                        # trim destinations to max size of route
                        destinations = {k: destinations[k] for k in
                                        destinations.keys()[:MAX_DESTINATIONS_BY_ROUTE[route]]}
                    max_destinations = max(len(destinations), max_destinations)

                destinations_id = pack('L' * len(destinations.keys()), *destinations.keys())
                destinations_rate = pack('d' * len(destinations.values()), *destinations.values())

                # Write
                migration_file.write(destinations_id)
                migration_file.write(destinations_rate)

                # Write offset
                offset_str = "%s%s%s" % (offset_str, "{0:08X}".format(nodeid), "{0:08X}".format(offset))

                # Increment offset
                offset += 12 * len(destinations)

        # TODO, we should move migration header generation outside to its own class so it can be called by both the
        # createmigrationheader script and here
        if compiled_demographics_file_path:
            from dtk.tools.migration import createmigrationheader
            with open(compiled_demographics_file_path, 'r') as compiled_demo_file:
                demo_json = createmigrationheader.load_demographics_file(compiled_demo_file)
            migration_headers = createmigrationheader.get_migration_json(demo_json, max_destinations,
                                                                         route.value, 'dtk-tools')
        else:  # Use the short method
            # TODO Test that this is sufficient
            # Write the headers
            meta = self.generate_headers({
                "NodeCount": len(matrix_id),
                "DatavalueCount": max_destinations
            })
            migration_headers = {
                "Metadata": meta,
                "NodeOffsets": offset_str
            }

        if migration_header_file_path is None:
            migration_header_file_path = f"{migration_bin_file_path}.json"
        with open(migration_header_file_path, 'w') as migration_header_file:
            json.dump(migration_headers, migration_header_file, indent=3)

    @staticmethod
    def get_filler_nodes(source, dests, n, available_nodes):
        """
        Fill the destinations with n filler nodes.
        Verifies that the node IDs chosen are not the source, not the destinations, and come from the **available_nodes**.
        """
        while len(dests) < n:
            for node in available_nodes:
                if node not in dests and node != source:
                    dests[node] = 0

    def nodes_to_id(self):
        """
        Transform the matrix of ``{node:{destination:rate}}`` into ``{node.id: {dest.id:rate}}``
        
        Returns: 
            A matrix.
        """
        return {
            node.id if hasattr(node, 'id') else node: {
                dest.id if hasattr(dest, 'id') else dest: v for dest, v in dests.items()
            } for node, dests in self.matrix.items()
        }
