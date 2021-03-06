import logging
import pandas as pd
import os, sys
import numpy as np
from scipy.stats import beta
from scipy.special import gammaln

from dtk.utils.observations.DataFrameWrapper import DataFrameWrapper
from dtk.utils.observations.PopulationObs import PopulationObs
from analyzers.PostProcessAnalyzer import PostProcessAnalyzer

# Plotting
# import matplotlib.pyplot as plt
# from matplotlib import collections as mc

logger = logging.getLogger(__name__)

class ProvincialPrevalenceAnalyzer(PostProcessAnalyzer):

    reference_key = 'ProvincialPrevalence'
    sim_reference_key = 'Sim_ProvincialPrevalence'
    log_float_tiny = np.log( np.finfo(float).tiny )

    def __init__(self, site, weight, **kwargs):
        super(ProvincialPrevalenceAnalyzer, self).__init__(**kwargs)

        self.filenames += [ os.path.join('output', 'post_process', 'ProvincialPrevalence.csv') ]

        self.name = self.__class__.__name__
        self.weight = weight
        self.setup = {}

        self.site = site
        self.reference = self.site.reference_data
        self.alpha_channel, self.beta_channel = self.reference.add_beta_parameters(channel=self.reference_key)
        self.reference = self.reference.filter(keep_only=[self.reference_key, self.alpha_channel, self.beta_channel])

    def filter(self, sim_metadata):
        ret = super(ProvincialPrevalenceAnalyzer, self).filter(sim_metadata)
        if ret and 'StatusQuo_Baseline' not in sim_metadata['Scenario']:
            self.sim_ids.remove(sim_metadata['sim_id'])
            print("Skipping", sim_metadata['sim_id'])
            return False

        return ret


    def apply(self, parser):
        ret = super(ProvincialPrevalenceAnalyzer, self).apply(parser)

        sim = parser.raw_data[self.filenames[-1]] \
            .set_index('Node') \
            .rename(self.node_map) \
            .reset_index() \
            .rename(columns={'Result':self.sim_reference_key, 'Node':'Province'})

        stratifiers = ['Year', 'Province', 'Gender', 'AgeBin']
        sim_dfw = DataFrameWrapper(dataframe=sim, stratifiers=stratifiers)
        merged = self.reference.merge(sim_dfw, index=stratifiers,
                                      keep_only=[self.reference_key, self.sim_reference_key, self.alpha_channel, self.beta_channel])

        merged_years = merged.get_years()
        reference_years = self.reference.get_years()

        if reference_years != merged_years:
            raise Exception("[%s] Failed to find all data years (%s) in simulation output (%s)." % (self.name, reference_years, merged_years))

        # If analyzing simulation not generated by itertool, __sample_index__ will not be in tags
        # Instead, use Run_Number
        sample = parser.sim_data.get('__sample_index__')
        if sample is None:
            sample = parser.sim_data.get('Run_Number')

        merged = merged._dataframe
        merged.index.name = 'Index'

        shelve_data = {
            'Data': merged,
            'Sim_Id': parser.sim_id,
            'Sample': sample
        }
        self.shelve_apply( parser.sim_id, shelve_data)

        if self.debug:
            print("size (MB):", sys.getsizeof(shelve_data)/8.0/1024.0)

    def compare_year_gender(self, sample):
        # Note: Might be called extra times by pandas on apply for purposes of "optimization"
        # http://stackoverflow.com/questions/21635915/why-does-pandas-apply-calculate-twice

        a = sample[self.alpha_channel]
        b = sample[self.beta_channel]
        x = sample[self.sim_reference_key]

        # This is what we're calculating:
        # BETA(output_i | alpha=alpha(Data), beta = beta(Data) )
        betaln = np.multiply((a-1), np.log(x)) \
            + np.multiply((b-1), np.log(1-x)) \
            - (gammaln(a)+gammaln(b)-gammaln(a+b))
        #
        # # Replace -inf with log(machine tiny)
        betaln[ np.isinf(betaln) ] = self.log_float_tiny

        # Scaling

        x_mode = np.divide((a - 1), (a + b - 2))
        largest_possible_log_of_beta = beta.pdf(x_mode, a, b)
        scale_max = 15
        beta_ratio = np.divide (scale_max, largest_possible_log_of_beta)

        betaln = np.multiply (betaln, beta_ratio)

        # betaln = max(betaln, self.log_float_tiny)

        return betaln

    def compare(self, sample):
        LL = sample.reset_index().groupby(['Year', 'Province', 'Gender']).apply(self.compare_year_gender)
        return (sum(LL.values)*self.weight)

    def combine(self, parsers):
        shelved_data = super(ProvincialPrevalenceAnalyzer, self).combine(parsers)

        if shelved_data is not None:
            if self.verbose:
                print('Combine from cache')
            self.data = shelved_data['Data']
            return

        selected = [ self.shelve[str(sim_id)]['Data'] for sim_id in self.sim_ids ]
        keys = [ (self.shelve[str(sim_id)]['Sample'], self.shelve[str(sim_id)]['Sim_Id'])
            for sim_id in self.sim_ids ]

        self.data = pd.concat( selected, axis=0,
                            keys=keys,
                            names=['Sample', 'Sim_Id'] )

        self.data.reset_index(level='Index', drop=True, inplace=True)

        try:
            self.shelve_combine({'Data':self.data})
        except:
            print("shelve_combine didn't work, sorry")

    def cache(self):
        pass

    def uid(self):
        print('UID')
        ''' A unique identifier of site-name and analyzer-name. '''
        return '_'.join([self.site.name, self.name])

    def finalize(self):
        fn = 'Results_%s.csv'%self.__class__.__name__
        out_dir = os.path.join(self.working_dir, self.basedir, self.exp_id)
        print('--> Writing %s to %s'%(fn, out_dir))
        ProvincialPrevalenceAnalyzer.mkdir_p(out_dir)
        results_filename = os.path.join(out_dir, fn)
        self.data.to_csv(results_filename)

        self.result = self.data.reset_index().groupby(['Sample']).apply(self.compare)

        # Close the shelve file, among other little things.  Can take a long time:
        super(ProvincialPrevalenceAnalyzer, self).finalize()
