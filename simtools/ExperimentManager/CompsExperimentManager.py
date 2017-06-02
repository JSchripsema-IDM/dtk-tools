import multiprocessing
import os
import re
from datetime import datetime

from COMPS.Data import Experiment, Configuration,Priority, Suite
from simtools.SetupParser import SetupParser
from simtools.DataAccess.Schema import Simulation
from simtools.ExperimentManager.BaseExperimentManager import BaseExperimentManager
from simtools.OutputParser import CompsDTKOutputParser
from simtools.SimulationCreator.COMPSSimulationCreator import COMPSSimulationCreator
from simtools.Utilities.COMPSUtilities import get_experiment_by_id, experiment_is_running, COMPS_login, \
    translate_COMPS_path
from simtools.Utilities.General import init_logging
logger = init_logging("COMPSExperimentManager")


class CompsExperimentManager(BaseExperimentManager):
    """
    Extends the LocalExperimentManager to manage DTK simulations through COMPSAccess wrappers
    e.g. creation of Simulation, Experiment, Suite objects
    """
    location = 'HPC'
    parserClass = CompsDTKOutputParser

    def __init__(self, experiment, config_builder):
        BaseExperimentManager.__init__(self, experiment, config_builder)
        self.comps_sims_to_batch = int(SetupParser.get('sims_per_thread'))
        self.sims_to_create = []
        self.commissioners = []
        self.assets_service = SetupParser.getboolean('use_comps_asset_svc')
        self.endpoint = SetupParser.get('server_endpoint')
        self.compress_assets = SetupParser.getboolean('compress_assets')
        COMPS_login(self.endpoint)
        self.creator_semaphore = None
        self.runner_thread = None

        # If we pass an experiment, retrieve it from COMPS
        if self.experiment:
            id = self.experiment.exp_id
            self.comps_experiment = get_experiment_by_id(id)

    def get_simulation_creator(self, function_set, max_sims_per_batch, callback, return_list):
        # Creator semaphore limits the number of thread accessing the database at the same time
        if not self.creator_semaphore:
            self.creator_semaphore = multiprocessing.Semaphore(4)


        return COMPSSimulationCreator(config_builder=self.config_builder,
                                      initial_tags=self.exp_builder.tags,
                                      function_set=function_set,
                                      max_sims_per_batch=max_sims_per_batch,
                                      experiment=self.experiment,
                                      callback=callback,
                                      return_list=return_list,
                                      save_semaphore=self.creator_semaphore)

    def analyze_experiment(self):
        if not self.assets_service:
            self.parserClass.createSimDirectoryMap(self.experiment.exp_id, self.experiment.suite_id)
        if self.compress_assets:
            from simtools.Utilities.General import nostdout
            with nostdout():
                self.parserClass.enableCompression()

        super(CompsExperimentManager, self).analyze_experiment()

    @staticmethod
    def create_suite(suite_name):
        suite = Suite(suite_name)
        suite.save()

        return str(suite.id)

    def create_experiment(self, experiment_name,experiment_id=None, suite_id=None):
        # Also create the experiment in COMPS to get the ID
        COMPS_login(SetupParser.get('server_endpoint'))

        config = Configuration(
            environment_name=SetupParser.get('environment'),
            simulation_input_args=self.commandline.Options,
            working_directory_root=os.path.join(SetupParser.get('sim_root'), experiment_name + '_' + re.sub('[ :.-]', '_', str(datetime.now()))),
            executable_path=self.commandline.Executable,
            node_group_name=SetupParser.get('node_group'), # ck4 THIS might be overridden... Overseer needs to know about the overrides to set this properly
            maximum_number_of_retries=int(SetupParser.get('num_retries')),
            priority=Priority[SetupParser.get('priority')],
            min_cores=self.config_builder.get_param('Num_Cores', 1),
            max_cores=self.config_builder.get_param('Num_Cores', 1),
            exclusive=self.config_builder.get_param('Exclusive', False),
            asset_collection_id=self.assets.collection_id
        )

        e = Experiment(name=experiment_name,
                       configuration=config,
                       suite_id=suite_id)
        e.save()

        # Create experiment in the base class
        super(CompsExperimentManager, self).create_experiment(experiment_name,  str(e.id), suite_id)

        # Set some extra stuff
        self.experiment.endpoint = self.endpoint

        # add AssetCollection tags - ids of individual exe, dll, input collections for later referencing
        asset_tags = {}
        for asset_type, asset in self.assets.collections.iteritems():
            asset_tags[asset_type + '_collection_id'] = str(asset.collection_id)
        e.merge_tags(asset_tags)

    def create_simulation(self):
        files = self.config_builder.dump_files_to_string()

        # Create the tags and append the environment to the tag
        tags = self.exp_builder.metadata
        tags['environment'] = SetupParser.get('environment')
        tags.update(self.exp_builder.tags if hasattr(self.exp_builder, 'tags') else {})

        # Add the simulation to the batch
        self.sims_to_create.append({'name': self.config_builder.get_param('Config_Name'), 'files':files, 'tags':tags})

    def commission_simulations(self, states):
        """
        Launches an experiment and its associated simulations in COMPS
        :param states: a multiprocessing.Queue() object for simulations to use for updating their status
        :return: The number of simulations commissioned.
        """
        import threading
        from simtools.SimulationRunner.COMPSRunner import COMPSSimulationRunner
        if not self.runner_thread or not self.runner_thread.is_alive():
            logger.debug("Commissioning simulations for COMPS experiment: %s" % self.experiment.id)
            self.runner_thread = threading.Thread(target=COMPSSimulationRunner, args=(self.experiment, states, self.success_callback))
            self.runner_thread.daemon = True
            self.runner_thread.start()
            return len(self.experiment.simulations)
        else:
            return 0

    def cancel_experiment(self):
        super(CompsExperimentManager, self).cancel_experiment()
        COMPS_login(self.endpoint)
        if self.comps_experiment and experiment_is_running(self.comps_experiment):
            self.comps_experiment.cancel()

    def hard_delete(self):
        """
        Delete local cache data for experiment and marks the server entity for deletion.
        """
        # Perform soft delete cleanup.
        self.soft_delete()

        # Mark experiment for deletion in COMPS.
        COMPS_login(self.endpoint)
        self.comps_experiment.delete()

    def kill_simulation(self, simulation):
        COMPS_login(self.endpoint)
        s = Simulation.get(simulation.id)
        s.cancel()


