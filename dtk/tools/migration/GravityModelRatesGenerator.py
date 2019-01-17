import heapq
import warnings

import networkx as nx

from dtk.tools.migration.GraphGenerator import GraphGenerator
from dtk.tools.migration.LinkRatesModelGenerator import GraphGeneratedLinkRatesModelGenerator


class GravityModelRatesGenerator(GraphGeneratedLinkRatesModelGenerator):
    """
    Generate rates matrix based on source-destination pairs path lengths (path weights) and graph topology input;
    see :py:class:`~dtk.tools.migration.MigrationGenerator` for path lengths/weights and graph topology generation.
    """

    def __init__(self, graph_generator: GraphGenerator, coeff: float = 1e-4):
        """
        Create a rates matrix based on the graph provided.

        Args:
            graph_generator: A :py:class:`~dtk.tools.migration.GraphGenerator` object.
            coeff: A gravity model coefficient for calculating the **mig_rate**.
        """
        super().__init__(graph_generator)
        warnings.warn("GravityModelRatesGenerator is deprecated.", DeprecationWarning)
        self.graph_generator = graph_generator
        if not isinstance(graph_generator, GraphGenerator):
            raise ValueError("A Graph Generator is required for the GravityModelRatesGenerator")

        self.coeff = coeff
        self.link_rates = None # output of gravity model based migration links generation
        self.path_lengths = None

    def generate(self) -> dict:
        """
        Generate the link rates(weighted adjacency list) from the provided graph.

        Returns:
            A weighted adjacency list calculated via gravity model.
        """
        self.graph_generator.generate_graph()
        self.path_lengths = self.graph_generator.get_shortest_paths()

        paths = {}

        migs = []

        max_migs = []

        mindist = 1  # 1km minimum distance in gravity model for improved short-distance asymptotic behavior
        dist_cutoff = 20  # beyond 20km effective distance not reached in 1 day.
        max_migration_dests = 100  # limit of DTK local migration

        for src, v in self.path_lengths:
            paths[src] = {}

            for dest, dist in v.items():
                if not dist or src == dest:
                    continue
                if dist < dist_cutoff:
                    mig_rate = self.coeff * self.graph_generator.graph.population[int(dest)]
                    mig_volume = self.graph_generator.graph.population[int(src)] * mig_rate
                    paths[src][dest] = mig_rate
                    migs.append(mig_rate)
                else:
                    warnings.warn('Check if dist_cutoff is too low for source node ' + str(src) + " distance is " + str(dist))

            d = paths[src]

            if not d:
                warnings.warn('No paths from source ' + str(src) + ' found! Check if node is isolated.')
                print("Node " + str(src) + " is isolate " + str(nx.is_isolate(self.graph_generator.graph, src)))
                continue

            nl = heapq.nlargest(max_migration_dests, d, key=lambda k: d[k])
            # print(len(d), nl, [int(d[k]) for k in nl])
            max_migs.append(d[nl[0]])

            paths[src] = dict([(k, d[k]) for k in nl])

        self.link_rates = paths

        return paths
