import copy
import json
import multiprocessing
import os
import subprocess
import sys
import time
from abc import ABCMeta, abstractmethod
from collections import Counter

import dill
import psutil
from dtk import helpers
from simtools import utils
from simtools.DataAccess.DataStore import DataStore, batch
from simtools.ModBuilder import SingleSimulationBuilder
from simtools.Monitor import SimulationMonitor
from simtools.OutputParser import SimulationOutputParser
from simtools.SetupParser import SetupParser
from simtools.SimulationCreator.BaseSimulationCreator import BaseSimulationCreator
from simtools.utils import init_logging

logger = init_logging('ExperimentManager')
overseer_check_lock = multiprocessing.Lock()

class BaseExperimentManager:
    __metaclass__ = ABCMeta
    creatorClass = BaseSimulationCreator
    parserClass=SimulationOutputParser
    location = None

    def __init__(self, model_file, experiment, setup=None):
        self.model_file = model_file
        self.experiment = experiment

        # If no setup is passed -> create it
        if setup is None:
            selected_block = experiment.selected_block if experiment.selected_block else 'LOCAL'
            setup_file = experiment.setup_overlay_file
            self.setup = SetupParser(selected_block=selected_block, setup_file=setup_file, fallback='LOCAL', force=True, working_directory = experiment.working_directory)
        else:
            self.setup = setup

        self.quiet = self.setup.has_option('quiet')
        self.blocking = self.setup.has_option('blocking')
        self.maxThreadSemaphore = multiprocessing.Semaphore(int(self.setup.get('max_threads')))

        self.analyzers = []
        self.parsers = {}
        if self.experiment and self.experiment.analyzers:
            for analyzer in experiment.analyzers:
                self.add_analyzer(dill.loads(analyzer.analyzer))

        self.assets_service = None
        self.exp_builder = None
        self.staged_bin_path = None
        self.config_builder = None
        self.commandline = None
        self.runner_created = False
        self.creators = []

    @abstractmethod
    def commission_simulations(self, states):
        pass

    @abstractmethod
    def create_suite(self, suite_name):
        pass

    @abstractmethod
    def kill_simulation(self, sim_id):
        pass

    @abstractmethod
    def hard_delete(self):
        pass

    @abstractmethod
    def check_input_files(self, input_files):
        pass

    @abstractmethod
    def create_experiment(self, experiment_name, experiment_id, suite_id=None):
        self.experiment = DataStore.create_experiment(
            exp_id=experiment_id,
            suite_id=suite_id,
            sim_root=self.setup.get('sim_root'),
            exe_name=self.commandline.Executable,
            exp_name=experiment_name,
            location=self.location,
            analyzers=[],
            sim_type=self.config_builder.get_param('Simulation_Type'),
            dtk_tools_revision=utils.get_tools_revision(),
            selected_block=self.setup.selected_block,
            setup_overlay_file=self.setup.setup_file,
            command_line=self.commandline.Commandline)

    def done_commissioning(self):
        self.experiment = DataStore.get_experiment(self.experiment.exp_id)
        for sim in self.experiment.simulations:
            if sim.status == 'Waiting' or not sim.status or sim.status == "Created":
                return False

        return True

    @staticmethod
    def check_overseer():
        """
        Ensure that the overseer thread is running.
        The thread pid is retrieved from the settings and then we test if it corresponds to a python thread.
        If not, just start it.
        """
        overseer_check_lock.acquire()
        try:
            setting = DataStore.get_setting('overseer_pid')

            if setting:
                overseer_pid = int(setting.value)
            else:
                overseer_pid = None

            if not overseer_pid or not psutil.pid_exists(overseer_pid) or 'python' not in psutil.Process(overseer_pid).name().lower():
                # Run the runner
                current_dir = os.path.dirname(os.path.realpath(__file__))
                runner_path = os.path.join(current_dir, '..', 'Overseer.py')
                import platform
                if platform.system() == 'Windows':
                    p = subprocess.Popen([sys.executable, runner_path], shell=False, creationflags=512)
                else:
                    p = subprocess.Popen([sys.executable, runner_path], shell=False)

                # Save the pid in the settings
                DataStore.save_setting(DataStore.create_setting(key='overseer_pid', value=str(p.pid)))
        finally:
            overseer_check_lock.release()

    def success_callback(self, simulation):
        """
        Called when the given simulation is done successfully
        """
        self.analyze_simulation(simulation)

    def analyze_simulation(self, simulation):
        # Add the simulation_id to the tags
        simulation.tags['sim_id'] = simulation.id

        # Called when a simulation finishes
        filtered_analyses = [a for a in self.analyzers if a.filter(simulation.tags)]
        if not filtered_analyses:
            # logger.debug('Simulation did not pass filter on any analyzer.')
            return

        self.maxThreadSemaphore.acquire()
        parser = self.get_output_parser(simulation.id, simulation.tags, filtered_analyses)
        parser.start()
        self.parsers[parser.sim_id] = parser

    def get_property(self, prop):
        return self.setup.get(prop)

    def get_setup(self):
        return dict(self.setup.items())

    def get_simulation_status(self):
        """
        Query the status of simulations in the currently managed experiment.
        For example: 'Running', 'Succeeded', 'Failed', 'Canceled', 'Unknown'
        """
        logger.debug("get_simulation_status for %s" % self.experiment.id)
        self.check_overseer()
        states, msgs = SimulationMonitor(self.experiment.exp_id).query()
        return states, msgs

    def get_output_parser(self, sim_id, sim_tags, filtered_analyses):
        return self.parserClass(self.experiment.get_path(),
                                sim_id,
                                sim_tags,
                                filtered_analyses,
                                self.maxThreadSemaphore)

    def run_simulations(self, config_builder, exp_name='test', exp_builder=SingleSimulationBuilder(), suite_id=None, analyzers=[]):
        """
        Create an experiment with simulations modified according to the specified experiment builder.
        Commission simulations and cache meta-data to local file.
        """
        # Check experiment name as early as possible
        if not utils.validate_exp_name(exp_name):
            exit()

        # Check input files existence
        if not self.validate_input_files(config_builder):
            exit()

        self.create_simulations(config_builder=config_builder, exp_name=exp_name, exp_builder=exp_builder,
                                analyzers=analyzers, suite_id=suite_id, verbose=not self.quiet)

        self.check_overseer()

        if self.blocking:
            self.wait_for_finished(verbose=not self.quiet)

    def find_missing_files(self, input_files, input_root):
        """
        Find the missing files
        """
        missing_files = {}
        for (filename, filepath) in input_files.iteritems():
            if isinstance(filepath, basestring):
                filepath = filepath.strip()
                # Skip empty files
                if len(filepath) == 0:
                    continue
                # Only keep un-existing files
                if not os.path.exists(os.path.join(input_root, filepath)):
                    missing_files[filename] = filepath
            elif isinstance(filepath, list):
                # Skip empty and only keep un-existing files
                missing_files[filename] = [f.strip() for f in filepath if len(f.strip()) > 0
                                           and not os.path.exists(os.path.join(input_root, f.strip()))]
                # Remove empty list
                if len(missing_files[filename]) == 0:
                    missing_files.pop(filename)

        return missing_files

    def validate_input_files(self, config_builder):
        """
        Check input files and make sure there exist
        Note: we by pass the 'Campaign_Filename'
        """
        # By-pass input file checking if using assets_service
        if self.assets_service:
            return True
        # If the config builder has no file paths -> bypass
        if not hasattr(config_builder, 'get_input_file_paths'):
            return True

        input_files = config_builder.get_input_file_paths()
        input_root, missing_files = self.check_input_files(input_files)

        # Py-passing 'Campaign_Filename' for now.
        if 'Campaign_Filename' in missing_files:
            logger.info("By-passing file '%s'..." % missing_files['Campaign_Filename'])
            missing_files.pop('Campaign_Filename')

        if len(missing_files) > 0:
            print 'Missing files list:'
            print 'input_root: %s' % input_root
            print json.dumps(missing_files, indent=2)
            var = raw_input("Above shows the missing input files, do you want to continue? [Y/N]:  ")
            if var.upper() == 'Y':
                print "Answer is '%s'. Continue..." % var.upper()
                return True
            else:
                print "Answer is '%s'. Exiting..." % var.upper()
                return False

        return True

    def create_simulations(self, config_builder, exp_name='test', exp_builder=SingleSimulationBuilder(), analyzers=[], suite_id=None, verbose=True):
        """
        Create an experiment with simulations modified according to the specified experiment builder.
        """
        self.config_builder = config_builder
        self.exp_builder = exp_builder

        # If the assets service is in use, do not stage the exe and just return whats in tbe bin_staging_path
        # If not, use the normal staging process
        if self.assets_service:
            self.staged_bin_path = self.setup.get('bin_staging_root')
        else:
            self.staged_bin_path = self.config_builder.stage_executable(self.model_file, self.get_setup())

        # Create the command line
        self.commandline = self.config_builder.get_commandline(self.staged_bin_path, self.get_setup())

        # Create the experiment if not present already
        if not self.experiment:
            self.create_experiment(experiment_name=exp_name, suite_id=suite_id)
        else:
            # Refresh the experiment
            self.experiment = DataStore.get_experiment(self.experiment.exp_id)

        # Add the analyzers
        for analyzer in analyzers:
            self.add_analyzer(analyzer)
            # Also add to the experiment
            self.experiment.analyzers.append(DataStore.create_analyzer(name=str(analyzer.__class__.__name__),
                                                                       analyzer=dill.dumps(analyzer)))

        # Separate the experiment builder generator into batches
        fn_batches = batch(list(self.exp_builder.mod_generator), n=int(self.setup.get('sims_per_thread',50)))
        for fn_batch in fn_batches:
            self.maxThreadSemaphore.acquire()
            c = self.creatorClass(config_builder=self.config_builder,
                                  experiment_builder=self.exp_builder,
                                  function_set=fn_batch,
                                  setup=self.setup,
                                  experiment=self.experiment,
                                  semaphore=self.maxThreadSemaphore)

            self.creators.append(c)
            c.start()

        # Wait for all commissioner to be done
        map(lambda c: c.join(), self.creators)

        # Save the experiment in the DB
        DataStore.save_experiment(self.experiment, verbose=verbose)

    def print_status(self,states, msgs, verbose=True):
        long_states = copy.deepcopy(states)
        for jobid, state in states.items():
            if 'Running' in state:
                steps_complete = [int(s) for s in msgs[jobid].split() if s.isdigit()]
                if len(steps_complete) == 2:
                    long_states[jobid] += " (" + str(100 * steps_complete[0] / steps_complete[1]) + "% complete)"

        logger.info("Job ('%s') states:" % self.experiment.exp_id)
        if len(long_states) < 20 and verbose:
            # We have less than 20 simulations, display the simulations details
            logger.info(json.dumps(long_states, sort_keys=True, indent=4))
        # Display the counter no matter the number of simulations
        logger.info(dict(Counter(states.values())))

    def delete_experiment(self, hard=False):
        """
        Delete experiment
        """
        if hard:
            self.hard_delete()
        else:
            self.soft_delete()

    def soft_delete(self):
        """
        Delete experiment in the DB
        """
        DataStore.delete_experiment(self.experiment)

    def wait_for_finished(self, verbose=False, init_sleep=0.1, sleep_time=5):
        getch = helpers.find_getch()
        self.check_overseer()
        while True:
            time.sleep(init_sleep)

            # Get the new status
            try:
                states, msgs = self.get_simulation_status()
            except:
                print "Exception occurred while retrieving status"
                return

            if self.status_finished(states):
                break
            else:
                if verbose:
                    self.print_status(states, msgs)

                for i in range(sleep_time):
                    if helpers.kbhit():
                        if getch() == '\r':
                            break
                        else:
                            return
                    else:
                        time.sleep(1)

        if verbose:
            self.print_status(states, msgs)

    def analyze_experiment(self):
        """
        Apply one or more analyzers to the outputs of simulations.
        A parser thread will be spawned for each simulation with filtered analyzers to run,
        following which the combined outputs of all threads are reduced and displayed or saved.
        The analyzer interface provides the following methods:
           * filter -- based on the simulation meta-data return a Boolean to execute this analyzer
           * apply -- parse simulation output files and emit a subset of data
           * combine -- reduce the data emitted by each parser
           * finalize -- plotting and saving output files
        """
        # If no analyzers -> quit
        if len(self.analyzers) == 0:
            return
        for simulation in self.experiment.simulations:
            # We already processed this simulation
            if self.parsers.has_key(simulation.id):
                continue

            self.analyze_simulation(simulation)

        # We are all done, finish analyzing
        for p in self.parsers.values():
            p.join()

        plotting_processes = []
        for a in self.analyzers:
            a.combine(self.parsers)

            a.finalize()

            # Plot in a separate process
            try:
                from multiprocessing import Process
                plotting_process = Process(target=a.plot)
                plotting_process.start()
                plotting_processes.append(plotting_process)
            except Exception as e:
                logger.error("Error in the plotting process for analyzer %s and experiment %s" % (a, self.experiment.id))
                logger.error(e)

        for p in plotting_processes:
            p.join()

    def add_analyzer(self, analyzer, working_dir=None):
        analyzer.exp_id = self.experiment.exp_id
        analyzer.exp_name = self.experiment.exp_name
        analyzer.working_dir = working_dir if working_dir else os.getcwd()
        # Add to the list
        self.analyzers.append(analyzer)

    def kill(self, args, unknownArgs):
        if args.simIds:
            self.cancel_simulations(args.simIds)
        else:
            self.cancel_experiment()

    def cancel_experiment(self):
        pass

    def cancel_simulations(self, sim_id_list):
        """
        Cancel all the simulations provided in id list.
        """
        for sim_id in sim_id_list:
            if type(sim_id) is str:
                # arguments come in as strings (as they should for COMPS)
                sim_id = int(sim_id) if sim_id.isdigit() else sim_id

            simulation = DataStore.get_simulation(sim_id)
            if simulation is None:
                continue

            state = simulation.status

            if not state:
                logger.warning('No job in experiment with ID = %s' % sim_id)
                continue

            if state not in ['Succeeded', 'Failed', 'Canceled', 'Unknown']:
                logger.info("Killing Job %s" % sim_id)
                print "Killing Job %s" % sim_id
                self.kill_simulation(sim_id)
            else:
                logger.warning("JobID %s is already in a '%s' state." % (str(sim_id), state))

    @staticmethod
    def status_succeeded(states):
        return all(v in ['Succeeded'] for v in states.itervalues())

    def succeeded(self):
        return self.status_succeeded(self.get_simulation_status()[0])

    @staticmethod
    def status_failed(states):
        return all(v in ['Failed'] for v in states.itervalues())

    @staticmethod
    def any_failed(states):
        return any(v in ['Failed'] for v in states.itervalues())

    @staticmethod
    def any_canceled(states):
        return any(v in ['Canceled'] for v in states.itervalues())

    def failed(self):
        return self.status_failed(self.get_simulation_status()[0])

    @staticmethod
    def status_finished(states):
        return all(v in ['Succeeded', 'Failed', 'Canceled'] for v in states.itervalues())

    def finished(self):
        return self.status_finished(self.get_simulation_status()[0])

