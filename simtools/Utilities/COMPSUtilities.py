from COMPS.Data import Experiment
from COMPS.Data import QueryCriteria
from COMPS.Data import Simulation
from COMPS.Data import Suite


def sims_from_experiment(e):
    return e.get_simulations(QueryCriteria().select('Id,SimulationState').select_children('HPCJobs'))


def sims_from_experiment_id(exp_id):
    return Simulation.get(query_criteria=QueryCriteria().select('Id,SimulationState').where('ExperimentId=%s' % exp_id))


def sims_from_suite_id(suite_id):
    exps = Experiment.get(query_criteria=QueryCriteria().where('SuiteId=%s' % suite_id))
    sims = []
    for e in exps:
        sims += sims_from_experiment(e)
    return sims


def workdirs_from_simulations(sims):
    return {str(sim.id): sim.hpc_jobs[-1].working_directory for sim in sims}


def workdirs_from_experiment_id(exp_id):
    e = Experiment.get(exp_id)
    sims = sims_from_experiment(e)
    return workdirs_from_simulations(sims)


def workdirs_from_suite_id(suite_id):
    # print('Simulation working directories for SuiteId = %s' % suite_id)
    s = Suite.get(suite_id)
    exps = s.get_experiments(QueryCriteria().select('Id'))
    sims = []
    for e in exps:
        sims.extend(sims_from_experiment(e))
    return workdirs_from_simulations(sims)