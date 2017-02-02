import logging

import pandas as pd

from calibtool import LL_calculators
from calibtool.analyzers.Helpers import accumulate_agebins_cohort
from calibtool.analyzers.BaseComparisonAnalyzer import BaseComparisonAnalyzer

logger = logging.getLogger(__name__)


class ClinicalIncidenceByAgeCohortAnalyzer(BaseComparisonAnalyzer):

    filenames = ['output/MalariaSummaryReport_Annual_Report.json']

    x = 'age_bins'
    y = 'Annual Clinical Incidence by Age Bin'

    data_group_names = ['sample', 'sim_id', 'channel']

    def __init__(self, site, weight=1, compare_fn=lambda s: True):
        super(ClinicalIncidenceByAgeCohortAnalyzer, self).__init__(site, weight, compare_fn)
        self.reference = site.get_reference_data('annual_clinical_incidence_by_age')

    def apply(self, parser):
        """
        Extract data from output data and accumulate in same bins as reference.

        TODO: if we want to plot with the original analyzer age bins,
              we will also need to emit a separate table of parsed data:
              data['Annual Clinical Incidence by Age Bin'], data['Age Bins']
        """

        data = parser.raw_data[self.filenames[0]]
        ref_age_bins = self.reference['age_bins']

        person_years, counts = accumulate_agebins_cohort(
            data['DataByTimeAndAgeBins']['Annual Clinical Incidence by Age Bin'],
            data['DataByTimeAndAgeBins']['Average Population by Age Bin'],
            data['Metadata']['Age Bins'], ref_age_bins)

        channel_data = pd.DataFrame({'Person Years': person_years,
                                     'Clinical Incidents': counts},
                                    index=ref_age_bins)

        channel_data.index.name = 'age_bins'
        channel_data.sample = parser.sim_data.get('__sample_index__')
        channel_data.sim_id = parser.sim_id

        return channel_data

    def combine(self, parsers):
        """
        Combine the simulation data into a single table for all analyzed simulations.
        """

        selected = [p.selected_data[id(self)] for p in parsers.values() if id(self) in p.selected_data]
        combined = pd.concat(selected, axis=1,
                             keys=[(d.sample, d.sim_id) for d in selected],
                             names=self.data_group_names)
        stacked = combined.stack(['sample', 'sim_id'])
        self.data = stacked.groupby(level=['sample', 'age_bins']).mean()
        logger.debug(self.data)

    def compare(self, sample):
        """
        Assess the result per sample, in this case the likelihood
        comparison between simulation and reference data.
        """

        sample['n_obs'] = self.reference['n_obs']
        sample['rates'] = self.reference['Annual Clinical Incidence by Age Bin']
        sample['n_counts'] = (sample.n_obs * sample.rates).astype('int')
        sample = sample[sample['Person Years'] > 0]

        # TODO: use self.compare_fn here?
        return LL_calculators.gamma_poisson(
            sample.n_obs.tolist(),
            sample['Person Years'].tolist(),
            sample.n_counts.tolist(),
            sample['Clinical Incidents'].tolist())

    def finalize(self):
        """
        Calculate the output result for each sample.
        """
        self.result = self.data.groupby(level='sample').apply(self.compare)
        logger.debug(self.result)

    def cache(self):
        """
        Return a cache of the minimal data required for plotting sample comparisons
        to reference comparisons.
        """

        cache = self.data.copy()
        cache = cache[cache['Person Years'] > 0]
        cache['Annual Clinical Incidence by Age Bin'] = cache['Clinical Incidents'] / cache['Person Years']
        cache = cache[['Annual Clinical Incidence by Age Bin']].reset_index(level='age_bins')
        cache.age_bins = cache.age_bins.astype(int)  # numpy.int64 serialization problem with utils.NumpyEncoder
        sample_dicts = [df.to_dict(orient='list') for idx, df in cache.groupby(level='sample', sort=True)]
        logger.debug(sample_dicts)

        return {'sims': sample_dicts, 'reference': self.reference, 'axis_names': [self.x, self.y]}
