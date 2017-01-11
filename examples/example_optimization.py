# Execute directly: 'python example_optimization.py'
# or via the calibtool.py script: 'calibtool run example_optimization.py'

from scipy.special import gammaln
import math
import random

from calibtool.CalibManager import CalibManager
from calibtool.algo.OptimTool import OptimTool
from calibtool.analyzers.DTKCalibFactory import DTKCalibFactory
from calibtool.plotters.LikelihoodPlotter import LikelihoodPlotter
from calibtool.plotters.SiteDataPlotter import SiteDataPlotter
from calibtool.plotters.OptimToolPlotter import OptimToolPlotter

from dtk.utils.core.DTKConfigBuilder import DTKConfigBuilder
from simtools.SetupParser import SetupParser

cb = DTKConfigBuilder.from_defaults('MALARIA_SIM')

analyzer = DTKCalibFactory.get_analyzer(
    'ClinicalIncidenceByAgeCohortAnalyzer', weight=1)

sites = [DTKCalibFactory.get_site('Dielmo', analyzers=[analyzer]),
         DTKCalibFactory.get_site('Ndiop', analyzers=[analyzer])]
print 'Dielmo only for now'
sites = [sites[0]]

plotters = [    LikelihoodPlotter(combine_sites=True), 
                SiteDataPlotter(num_to_plot=10, combine_sites=True),
                OptimToolPlotter()] # OTP must be last because it calls gc.collect()

# Antigen_Switch_Rate (1e-10 to 1e-8, log)
# Falciparum_PfEMP1_Variants (900 to 1700, linear int)
# Falciparum_MSP_Variants (5 to 50, linear int)

# The following params can be changed by stopping 'calibool', making a modification, and then resuming.
# Things you can do:
# * Change the min and max, but changing the guess of an existing parameter has no effect
# * Make a dynamic parameter static and vise versa
# * Add and remove (needs testing) parameters
params = [
    {
        'Name': 'Clinical Fever Threshold High',
        'Dynamic': True,
        #'MapTo': 'Clinical_Fever_Threshold_High', # <-- DEMO: Custom mapping, see map_sample_to_model_input below
        'Guess': 0.6,
        'Min': 0.5,
        'Max': 2.5
    },
    {
        'Name': 'MSP1 Merozoite Kill Fraction',
        'Dynamic': False,   # <-- NOTE: this parameter is frozen at Guess
        'MapTo': 'MSP1_Merozoite_Kill_Fraction',
        'Guess': 0.65,
        'Min': 0.4,
        'Max': 0.7
    },
    {
        'Name': 'Falciparum PfEMP1 Variants',
        'Dynamic': True,
        'MapTo': 'Falciparum_PfEMP1_Variants',
        'Guess': 4000,
        'Min': 1, # 900 [0]
        'Max': 5000 # 1700 [1e5]
    },
    {
        'Name': 'Min Days Between Clinical Incidents',
        'Dynamic': False, # <-- NOTE: this parameter is frozen at Guess
        'MapTo': 'Min_Days_Between_Clinical_Incidents',
        'Guess': 25,
        'Min': 1,
        'Max': 50
    },
]

def constrain_sample( sample ):
    # Convert Falciparum MSP Variants to nearest integer
    if 'Min Days Between Clinical Incidents' in sample:
        sample['Min Days Between Clinical Incidents'] = int( round(sample['Min Days Between Clinical Incidents']) )

    '''
    # Can do much more here, e.g. for
    # Clinical Fever Threshold High <  MSP1 Merozoite Kill Fraction
    if 'Clinical Fever Threshold High' and 'MSP1 Merozoite Kill Fraction' in sample:
        sample['Clinical Fever Threshold High'] = \
            min( sample['Clinical Fever Threshold High'], sample['MSP1 Merozoite Kill Fraction'] )
    '''

    return sample

def map_sample_to_model_input(cb, sample):
    tags = {}

    # Can perform custom mapping, e.g. a trivial example
    if 'Clinical Fever Threshold High' in sample:
        value = sample.pop('Clinical Fever Threshold High')
        tags.update( cb.set_param('Clinical_Fever_Threshold_High', value) )

    for p in params:
        if 'MapTo' in p:
            if p['Name'] not in sample:
                print 'Warning: %s not in sample, perhaps resuming previous iteration' % p['Name']
                continue
            value = sample.pop( p['Name'] )
            tags.update( cb.set_param(p['Name'], value) )

    for name,value in sample.iteritems():
        print 'UNUSED PARAMETER:', name
    assert( len(sample) == 0 ) # All params used

    # Run for 10 years with a random random number seed
    tags.update( cb.set_param('Simulation_Duration', 10*365) )
    tags.update( cb.set_param('Run_Number', random.randint(0, 1e6)) )

    return tags

# Just for fun, let the numerical derivative baseline scale with the number of dimensions
volume_fraction = 0.05   # desired fraction of N-sphere area to unit cube area for numerical derivative (automatic radius scaling with N)
num_params = len( [p for p in params if p['Dynamic']] )
r = math.exp( 1/float(num_params)*( math.log(volume_fraction) + gammaln(num_params/2.+1) - num_params/2.*math.log(math.pi) ) )

optimtool = OptimTool(params, 
    constrain_sample,   # <-- WILL NOT BE SAVED IN ITERATION STATE
    mu_r = r,           # <-- radius for numerical derivatve.  CAREFUL not to go too small with integer parameters
    sigma_r = r/10.,    # <-- stdev of radius
    center_repeats = 2, # <-- Number of times to replicate the center (current guess).  Nice to compare intrinsic to extrinsic noise
    samples_per_iteration = 32 # <-- Samples per iteration, includes center repeats.  Actual number of sims run is this number times number of sites.
)

calib_manager = CalibManager(name='ExampleOptimization',    # <-- Please customize this name
                             setup = SetupParser(),
                             config_builder = cb,
                             map_sample_to_model_input_fn = map_sample_to_model_input,
                             sites = sites,
                             next_point = optimtool,
                             sim_runs_per_param_set = 1, # <-- Replicates
                             max_iterations = 5,         # <-- Iterations
                             plotters = plotters)

#run_calib_args = {'selected_block': "EXAMPLE"}
run_calib_args = {}

if __name__ == "__main__":
    run_calib_args.update(dict(location='LOCAL'))
    calib_manager.run_calibration(**run_calib_args)
