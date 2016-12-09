import logging

import pandas as pd

from calibtool import LL_calculators
from calibtool.analyzers.BaseComparisonAnalyzer import BaseComparisonAnalyzer
from calibtool.analyzers.Helpers import summary_channel_to_pandas, convert_to_counts, \
                                        age_from_birth_cohort, season_from_time, aggregate_on_index

logger = logging.getLogger(__name__)


class PrevalenceByAgeSeasonAnalyzer(BaseComparisonAnalyzer):

    filenames = ['output/MalariaSummaryReport_Monthly_Report.json']

    population_channel = 'Average Population by Age Bin'

    def __init__(self, site, weight=1, compare_fn=LL_calculators.dirichlet_multinomial_pandas, **kwargs):
        super(PrevalenceByAgeSeasonAnalyzer, self).__init__(site, weight, compare_fn)
        self.reference = site.get_reference_data('density_by_age_and_season')

        # Get channels to extract from 'Channel' level of reference MultiIndex
        ref_ix = self.reference.index
        channels_ix = ref_ix.names.index('Channel')
        self.channels = ref_ix.levels[channels_ix].values

        self.seasons = kwargs.get('seasons')

    def apply(self, parser):
        """
        Extract data from output simulation data and accumulate in same bins as reference.
        """

        # Load data from simulation
        data = parser.raw_data[self.filenames[0]]

        # Population by age and time series (to convert parasite prevalence to counts)
        population = summary_channel_to_pandas(data, self.population_channel)

        # Coerce channel data into format for comparison with reference
        channel_data_dict = {}
        for channel in self.channels:

            # Prevalence by density, age, and time series
            channel_data = summary_channel_to_pandas(data, channel)

            # Calculate counts from prevalence and population
            channel_counts = convert_to_counts(channel_data, population)

            # Reset multi-index and perform transformations on index columns
            df = channel_counts.reset_index()
            df = age_from_birth_cohort(df)  # calculate age from time for birth cohort
            df = season_from_time(df, seasons=self.seasons)  # calculate month from time

            # Re-bin according to reference and return single-channel Series
            rebinned = aggregate_on_index(df, self.reference[channel].index, keep=[channel])
            channel_data_dict[channel] = rebinned[channel].rename('counts')

        sim_data = pd.concat(channel_data_dict.values(), keys=channel_data_dict.keys(), names=['Channel'])
        sim_data.sample = parser.sim_data.get('__sample_index__')
        sim_data.sim_id = parser.sim_id

        return sim_data

    def combine(self, parsers):
        """
        Combine the simulation data into a single table for all analyzed simulations.
        """

        selected = [p.selected_data[id(self)] for p in parsers.values() if id(self) in p.selected_data]

        # Stack selected_data from each parser, adding unique (sim_id) and shared (sample) levels to MultiIndex
        # TODO: convert output of apply() to one-column DataFrame to re-use code with other analyzers?
        combine_levels = ['sim_id', 'sample']
        combined = pd.concat(selected, axis=0,
                             keys=[(d.sim_id, d.sample) for d in selected],
                             names=combine_levels)

        # Unstack sim_id/sample to columns MultiIndex and store average sim_ids with same sample index
        combined = combined.unstack(combine_levels)
        self.data = combined.groupby(level='sample', axis=1).mean()
        logger.debug(self.data)

    def compare(self, sample):
        """
        Assess the result per sample, in this case the likelihood
        comparison between simulation and reference data.
        """

        df = pd.concat([sample.rename('sim'), self.reference.rename('ref')], axis=1).dropna()
        return self.compare_fn(df)

    def finalize(self):
        """
        Calculate the output result for each sample.
        """
        self.result = self.data.apply(self.compare)
        logger.debug(self.result)

    def cache(self):
        """
        Return a cache of the minimal data required for plotting sample comparisons
        to reference comparisons. Append the reference column to the simulation sample-point data.
        """
        # TODO: JSON serializable form for CalibManager.IterationState cache?
        return pd.concat([self.data, self.reference.rename('ref')], axis=1).dropna()
