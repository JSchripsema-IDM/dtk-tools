import json
from typing import Union, Tuple, List
import numpy as np
import pandas as pd
from geopy.distance import distance
from dtk.tools.migration.LinkRatesModelGenerator import LinkRatesModelGenerator
import os


class StaticGravityModelRatesGenerator(LinkRatesModelGenerator):
    """
    GravityModel where the gravity parameters are static (pre-calculated).
    """

    def __init__(self, demographics_file_path: str, gravity_params: np.array,
                 exclude_nodes: Union[List, None]=None):
        """

        Args:
            demographics_file_path: Path to the demographics file to load.
            gravity_params: A list/array of gravity parameters used to calculated migration rate. Expects three
            positive values and one negative value.
            exclude_nodes: A list of nodes to exclude from link rate generation.
        """
        super().__init__()  # This Model has no graph

        if not os.path.isfile(demographics_file_path):
            raise ValueError("A demographics file is required.")

        self.demographics_file_path = demographics_file_path
        self.gravity_params = gravity_params

        if len(self.gravity_params) != 4:
            raise ValueError("You must provide all 4 gravity params")

        # migration rate is proportional to population in original node and population in destination node.
        if self.gravity_params[0] <= 0 or self.gravity_params[1] <= 0 or self.gravity_params[2] <= 0:
            raise ValueError("The first three values in gravity_params must be positive.")

        # migration rate is inversely proportional to distance.
        if self.gravity_params[-1] >= 0:
            raise ValueError("The last value in gravity_params must be negative. ")

        self.exclude_nodes = exclude_nodes

    @staticmethod
    def load_demographics_file(demo_file):
        with open(demo_file, 'r') as f:
            demo_dict = json.load(f)

        N = demo_dict['Metadata']['NodeCount']
        lat = np.ones(N)
        long = np.ones(N)
        grid_id = np.ones(N)
        node_id = np.ones(N)
        pop = np.ones(N)

        for i in range(N):
            node = demo_dict['Nodes'][i]
            lat[i] = node['NodeAttributes']['Latitude']
            long[i] = node['NodeAttributes']['Longitude']
            grid_id[i] = node['NodeAttributes']['FacilityName']
            node_id[i] = node['NodeID']
            pop[i] = node['NodeAttributes']['InitialPopulation']

        df = pd.DataFrame({
            'lat': lat,
            'long': long,
            'grid_id': grid_id,
            'node_id': node_id,
            'pop': pop
        })

        return df

    def compute_migration_probability(self, ph: int, pd: int, d: float) -> float:
        """
        Compute the probability of migration based on the gravity parameters, the population of one node and the population
        of a second node, and their distance from each other.

        Args:
            ph: Population of node 1.
            pd: Population of node 2.
            d:  The distance between the nodes.

        Returns:
            The probability of migration.
        """
        # If home/dest node has 0 pop, assume this node is the regional work node-- no local migration allowed
        if ph == 0 or pd == 0:
            return 0.
        else:
            num_trips = self.gravity_params[0] * ph ** self.gravity_params[1] * pd ** self.gravity_params[2] * d ** \
                        self.gravity_params[3]
            prob_trip = np.min([1., num_trips / ph])
            return prob_trip

    def compute_migration(self, df: pd.DataFrame, return_prob_sums: bool=False) -> Union[dict, Tuple[dict, np.ndarray]]:
        """
        Calculate the migration based on the demographics data and the gravity parameters.

        Args:
            df: Pandas data frame containing the lat, long, **grid_id**, **node_id**, and population.
            return_prob_sums: True to return the link rates and the total probability; False to return only the link rates. 

        Returns:
            If **return_prob_sums** is True, it returns a tuple containing the link rates dictionary and then a list of
            total migration probabilities for each node.
            If **return_prob_sums** is False, it returns the link rates dictionary.
        """
        migr = {}

        p_sum = np.zeros(len(df))
        jj = 0
        for i1, r1 in df.iterrows():
            migr[r1['node_id']] = {}

            for i2, r2 in df.iterrows():
                if r2['node_id'] == r1['node_id']:
                    pass
                elif self.exclude_nodes and (r1['node_id'] in self.exclude_nodes or
                                             r2['node_id'] in self.exclude_nodes):
                    migr[r1['node_id']][r2['node_id']] = 0.0
                else:
                    d = distance((r1['lat'], r1['long']), (r2['lat'], r2['long'])).km
                    migr[r1['node_id']][r2['node_id']] = self.compute_migration_probability(r1['pop'], r2['pop'],
                                                                                            d)

            p_sum[jj] = np.sum(list(migr[r1['node_id']].values()))
            jj += 1

        if return_prob_sums:
            return migr, p_sum
        else:
            return migr

    def generate(self, outf='grav_migr_rates.json') -> dict:
        df = self.load_demographics_file(self.demographics_file_path)

        if self.exclude_nodes:
            df = df[np.logical_not(np.in1d(df['node_id'], self.exclude_nodes))]

        migr_dict = self.compute_migration(df, return_prob_sums=False)

        # Save to file:
        with open(outf, 'w') as f:
            json.dump(migr_dict, f, indent=4)

        return migr_dict
