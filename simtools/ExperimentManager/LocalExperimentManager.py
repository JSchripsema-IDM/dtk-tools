from simtools.Utilities.General import init_logging
logger = init_logging("LocalExperimentManager")

import os
import re
import shutil
import signal
import threading
from datetime import datetime

from simtools.ExperimentManager.BaseExperimentManager import BaseExperimentManager
from simtools.OutputParser import SimulationOutputParser
from simtools.SimulationCreator.LocalSimulationCreator import LocalSimulationCreator
from simtools.SimulationRunner.LocalRunner import LocalSimulationRunner


class LocalExperimentManager(BaseExperimentManager):
    """
    Manages the creation, submission, status, parsing, and analysis
    of local experiments, i.e. collections of related simulations
    """
    location = 'LOCAL'
    parserClass = SimulationOutputParser

    def __init__(self, model_file, experiment, setup=None):
        self.simulations_commissioned = 0
        BaseExperimentManager.__init__(self, model_file, experiment, setup)

    def commission_simulations(self, states):
        """
         Commissions all simulations that need to be commissioned.
        :param states: a multiprocessing.Queue for simulations to use to update their status.
        :return: a list of Simulation objects that were commissioned.
        """
        to_commission = self.needs_commissioning()
        logger.debug("Commissioning %d simulation(s)." % len(to_commission))
        for simulation in to_commission:
            logger.debug("Commissioning simulation: %s, its status was: %s" % (simulation.id, simulation.status))
            t1 = threading.Thread(target=LocalSimulationRunner, args=(simulation, self.experiment, states, self.success_callback))
            t1.daemon = True
            t1.start()
        return to_commission

    def needs_commissioning(self):
        """
        Determines which simulations need to be (re)started.
        :return: A list of Simulation objects
        """
        simulations = []
        for sim in self.experiment.simulations:
            if sim.status == 'Waiting' or (sim.status == 'Running' and not LocalSimulationRunner.is_running(sim.pid)):
                logger.debug("Detected sim in need of commissioning. sim id: %s sim status: %s sim pid: %s is_running? %s" %
                             (sim.id, sim.status, sim.pid, LocalSimulationRunner.is_running(sim.pid)))
                simulations.append(sim)
        return simulations

    def check_input_files(self, input_files):
        """
        Check file exist and return the missing files as dict
        """
        input_root = self.setup.get('input_root')
        return input_root, self.find_missing_files(input_files, input_root)

    def create_experiment(self, experiment_name, experiment_id=re.sub('[ :.-]', '_', str(datetime.now())),suite_id=None):
        logger.info("Creating exp_id = " + experiment_id)

        # Create the experiment in the base class
        super(LocalExperimentManager,self).create_experiment(experiment_name, experiment_id, suite_id)

        # Get the path and create it if needed
        experiment_path = self.experiment.get_path()
        if not os.path.exists(experiment_path):
            os.makedirs(experiment_path)

    @staticmethod
    def create_suite(suite_name):
        suite_id = suite_name + '_' + re.sub('[ :.-]', '_', str(datetime.now()))
        logger.info("Creating suite_id = " + suite_id)
        return suite_id

    def hard_delete(self):
        """
        Delete experiment and output data.
        """
        # Perform soft delete cleanup.
        self.soft_delete()

        # Delete local simulation data.
        shutil.rmtree(self.experiment.get_path())

    def cancel_experiment(self):
        super(LocalExperimentManager, self).cancel_experiment()
        sim_list = [sim for sim in self.experiment.simulations if sim.status in ["Waiting","Running"]]
        self.cancel_simulations(sim_list)

    def kill_simulation(self, simulation):
        # No need of trying to kill simulation already done
        if simulation.status in ('Succeeded', 'Failed', 'Canceled'):
            return

        # It was running -> Kill it if pid is there
        if simulation.pid:
            try:
                os.kill(int(simulation.pid), signal.SIGTERM)
            except Exception as e:
                print e

    def get_simulation_creator(self, function_set, max_sims_per_batch, callback, return_list):
        return LocalSimulationCreator(config_builder=self.config_builder,
                                      initial_tags=self.exp_builder.tags,
                                      function_set=function_set,
                                      max_sims_per_batch=max_sims_per_batch,
                                      experiment=self.experiment,
                                      setup=self.setup,
                                      callback=callback,
                                      return_list=return_list)
