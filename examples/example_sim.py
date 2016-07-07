from dtk.utils.core.DTKConfigBuilder import DTKConfigBuilder
from dtk.vector.study_sites import configure_site
from simtools.ExperimentManager import ExperimentManagerFactory
from simtools.SetupParser import SetupParser

cb = DTKConfigBuilder.from_defaults('VECTOR_SIM')
configure_site(cb, 'Namawala')

run_sim_args =  {'config_builder': cb,
                 'exp_name': 'ExampleSim'}


if __name__ == "__main__":
    sm = ExperimentManagerFactory.from_setup(SetupParser())
    sm.run_simulations(**run_sim_args)