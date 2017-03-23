import sys, os, re
import logging
import pandas as pd
import numpy as np      # for finfo tiny
import copy
import shelve

# Plotting
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import gridspec

from calibtool import LL_calculators
from dtk.Typhoid.ReportTyphoidInsetChartAnalyzer import ReportTyphoidInsetChartAnalyzer

logger = logging.getLogger(__name__)

class SeasonalityAnalyzer(ReportTyphoidInsetChartAnalyzer):

    def __init__(self,
                    name,
                    reference_sheet,

                    basedir = 'Work',

                    max_sims_to_process = -1,
                    force_apply = False,
                    force_combine = False,

                    # ALL AGES
                    pop_scaling_year = 1975.997,
                    pop_scaling_pop = 3782716,

                    fig_format = 'png',
                    fig_dpi = 600,
                    verbose = False):

        super(SeasonalityAnalyzer, self).__init__( max_sims_to_process, pop_scaling_year, pop_scaling_pop, force_apply, force_combine, basedir, fig_format, fig_dpi, verbose)

        self.name = name
        self.reference_sheet = reference_sheet

        self.cache_data = {}


    def set_site(self, site):
        self.reference = site.reference_data[self.reference_sheet].set_index(['Year', 'Month', 'AgeBin'])

        year_bins = sorted(self.reference.index.get_level_values('Year').unique().tolist())
        self.ref_pop = site.reference_data['PopulationByAge'].groupby('Year')['Pop'].sum().loc[year_bins[0]:year_bins[-1]+2].sum()
        self.year_bins = ['[%d, %d)'%(min(year_bins), max(year_bins)+1)]
        self.reference = self.reference.groupby(level=['Month', 'AgeBin']).sum()
        self.reference['Year'] = self.year_bins[0]
        self.reference = self.reference.reset_index().set_index(['Year', 'AgeBin', 'Month'])
        self.age_bins = self.reference.index.get_level_values('AgeBin').unique()

        self.cache_data['reference'] = self.reference.reset_index().to_dict(orient='list')


    def filter(self, sim_metadata):
        return super(SeasonalityAnalyzer, self).filter(sim_metadata)

    def lower_value(self, agebin): # For age-bin sorting
        return [int(s) for s in re.findall(r'\b\d+\b', agebin)][0]

    def apply(self, parser):
        (sim, pop_scaling) = super(SeasonalityAnalyzer, self).apply(parser)
        if self.verbose:
            print 'Population scaling factor is', pop_scaling

        keep_cols = ['Year', 'Month', 'Statistical Population', 'Number of New Acute Infections']
        drop_cols = list( set(sim.columns.values) - set(keep_cols) )
        sim.drop(drop_cols, axis=1, inplace=True)

        sim_output = pd.DataFrame()
        for year_bin in self.year_bins:
            year_edges = [int(s) for s in re.findall(r'\b\d+\b', year_bin)]

            # Select years, assuming sequential
            sim_year = sim.query('Year >= @year_edges[0] & Year < @year_edges[1]').set_index('Year')

            simbin = sim_year[['Month', 'Number of New Acute Infections', 'Statistical Population']].groupby('Month').sum()
            simbin['Statistical Population'] /= 365. # Daily timesteps
            #simbin['YearBin'] = year_bin

            # Undo parent's pop scaling for beta-binomial likelihood
            simbin['Sim_Acute'] = simbin['Number of New Acute Infections']
            simbin['Sim_Acute_Unscaled'] = simbin['Sim_Acute'] / pop_scaling
            simbin.rename(columns={'Statistical Population':'Sim_Population'}, inplace=True)
            simbin['Sim_Population_Unscaled'] = simbin['Sim_Population'] / pop_scaling

            sim_output = pd.concat( [sim_output, simbin], axis=1 )

        merged = pd.merge(sim_output, self.reference, left_index=True, right_index=True)

        shelve_data = {
            'Data': merged,
            'Sim_Id': parser.sim_id,
            'Sample': parser.sim_data.get('__sample_index__'),
            #'Replicate': parser.sim_data.get('__replicate_index__'),
            'Pop_Scaling': pop_scaling
        }
        self.shelve_apply( parser.sim_id, shelve_data)

        if self.verbose:
            print "size (MB):", sys.getsizeof(shelve_data)/8.0/1024.0

    def combine(self, parsers):
        shelved_data = super(SeasonalityAnalyzer, self).combine(parsers)

        if shelved_data is not None:
            # Get data from shelve
            self.data = shelved_data['Data']
        else:

            # Not in shelve, need to combine and store in shelve
            selected = [ self.shelve[str(sim_id)]['Data'] for sim_id in self.sim_ids ]
            keys = [ (self.shelve[str(sim_id)]['Sample'], self.shelve[str(sim_id)]['Sim_Id'])
                for sim_id in self.sim_ids ]

            self.data = pd.concat( selected, axis=0,
                                keys=keys,
                                names=['Sample', 'Sim_Id'] )

            self.shelve_combine( { 'Data' : self.data } )

        self.data.reset_index('Month', inplace=True)
        self.data['Month'] = pd.Categorical(self.data['Month'].astype('category'), categories=['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'], ordered=True)
        self.data.set_index('Month', append=True, inplace=True)
        #self.data.sort_index(level='Month', sort_remaining=False, inplace=True)
        self.data.sort_index(level='Sample', inplace=True, sort_remaining=True)
        print self.data.index

        d = self.data.reset_index()
        self.cache_data['Sim'] = d.where((pd.notnull(d)), None).to_dict(orient='list')


    def compare_age(self, sample):
        # Computation takes mean of log across data points
        # ref_pop
        LL = 0
        return LL

        ''' Work in progress, should be dirichlet multinomial:
        print 'HI'
        print sample
        exit()

        LL = LL_calculators.beta_binomial(
            raw_nobs = sample['Ref_Population'].tolist(),           # raw_nobs
            sim_nobs = sample['Sim_Population_Unscaled'].tolist(),  # sim_nobs
            raw_data = sample['Ref_Cases'].tolist(),                # raw_data
            sim_data = sample['Sim_Cases_Unscaled'].tolist()        # sim_data
        )

        return LL
        '''


    def compare(self, sample):
        print sample
        LL = sample.reset_index().groupby(['Sim_Id']).apply(self.compare_age)
        return sum(LL.values)


    def finalize(self):
        super(SeasonalityAnalyzer, self).finalize() # Closes the shelve file

        writer = pd.ExcelWriter(os.path.join(self.workdir,'Results_%s.xlsx'%self.__class__.__name__))
        #self.result.to_frame().sort_index().to_excel(writer, sheet_name='Result')
        self.data.to_excel(writer, sheet_name=self.__class__.__name__, merge_cells=False)
        writer.save()

        ''' # WORK IN PROGRESS:
        self.result = self.data.groupby(level='Sample').apply(self.compare)
        #self.result.replace(-np.inf, -1e-6, inplace=True)
        self.cache_data['result'] = self.result.to_dict()


        f, axes = plt.subplots(1, 1, figsize=(12, 8), sharex=False)
        #sns.despine(left=True)

        d = self.data.reset_index()
        d_by_sample = self.data.reset_index().set_index('Sample')
        n_samples = len(d_by_sample.index.unique())
        self.result.name = 'LogLikelihood'
        merged = pd.merge(d_by_sample, self.result.to_frame(), left_index=True, right_index=True).reset_index()

        axes.plot( self.reference['Ref_Cases'].values*[1,1], [0,n_samples], 'r-') # , axes=axes[0,0]

        sim_cases_range = self.data.reset_index().groupby('Sample')['Sim_Cases'].agg({'Min':np.min, 'Max':np.max})
        for idx,s in sim_cases_range.iterrows():
            axes.plot( [s['Min'], s['Max']], [idx,idx], 'b-', linewidth=0.5 )
        axes.scatter(d['Sim_Cases'], d['Sample'], c='k', marker='|', alpha=1, linewidths=1)

        # TODO: Vectorize
        plt.autoscale()
        axes.set_ylim(ymin=0, ymax=n_samples)

        plt.savefig(os.path.join(self.workdir, 'SeasonalityAnalyzer.'+self.fig_format)); plt.close()
        '''


    def plot(self):
        super(SeasonalityAnalyzer, self).plot() # plt.show()

    def cache(self):
        return self.cache_data

    def uid(self):
        ''' A unique identifier of site-name and analyzer-name. '''
        return '_'.join([self.site.name, self.name])
