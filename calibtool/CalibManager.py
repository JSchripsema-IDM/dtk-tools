import json
import os
import re
import shutil
from datetime import datetime

import pandas as pd

from calibtool.IterationState import IterationState
from calibtool.utils import StatusPoint
from simtools.DataAccess.DataStore import DataStore
from simtools.ExperimentManager.ExperimentManagerFactory import ExperimentManagerFactory
from simtools.ModBuilder import ModBuilder, ModFn
from simtools.SetupParser import SetupParser
from simtools.Utilities.COMPSUtilities import COMPS_login
from simtools.Utilities.Encoding import NumpyEncoder
from simtools.Utilities.Experiments import validate_exp_name, retrieve_experiment
from simtools.Utilities.General import init_logging
from simtools.Utilities import verbose_timedelta

logger = init_logging("Calibration")


class SampleIndexWrapper(object):
    """
    Wrapper for a SimConfigBuilder-modifying function to add metadata
    on sample-point index when called in a iteration over sample points
    """
    __name__ = "SampleIndex"

    def __init__(self, map_sample_to_model_input_fn):
        self.map_sample_to_model_input_fn = map_sample_to_model_input_fn

    def __call__(self, cb, idx, *args, **kwargs):
        params_dict = self.map_sample_to_model_input_fn(cb, *args, **kwargs)
        params_dict.update(cb.set_param('__sample_index__', idx))
        return params_dict


class CalibManager(object):
    """
    Manages the creation, execution, and resumption of multi-iteration a calibration suite.
    Each iteration spawns a new ExperimentManager to configure and commission either local
    or HPC simulations for a set of random seeds, sample points, and site configurations.
    """

    def __init__(self,  config_builder, map_sample_to_model_input_fn,
                 sites, next_point, name='calib_test',  sim_runs_per_param_set=1, max_iterations=5, plotters=None):

        self.name = name
        self.config_builder = config_builder
        self.map_sample_to_model_input_fn = SampleIndexWrapper(map_sample_to_model_input_fn)
        self.sites = sites
        self.next_point = next_point
        self.sim_runs_per_param_set = sim_runs_per_param_set
        self.max_iterations = max_iterations
        self.plotters = plotters or []
        self.suites = []
        self.all_results = None
        self.summary_table = None
        self.calibration_start = None
        self.latest_iteration = 0
        self.current_iteration = None
        self._location = None
        self.resume = False
        self.experiment_builder_function = None  # if not overridden in the set method, use internally-generated func

    @classmethod
    def open_for_reading(cls, calibration_directory):
        return cls(config_builder=None, map_sample_to_model_input_fn=None, sites=None, next_point=None,
                   name=calibration_directory)

    @property
    def location(self):
        return SetupParser.get('type') if self._location is None else self._location

    @location.setter
    def location(self, value):
        self._location = value

    @property
    def suite_id(self):
        # Generate the suite ID if not present
        if not self.suites or self.suites[-1]['type'] != self.location:
            exp_manager = ExperimentManagerFactory._factory(self.location)
            suite_id = exp_manager.create_suite(self.name)
            self.suites.append({'id': suite_id, 'type': self.location})
            self.cache_calibration()

        return self.suites[-1]['id']

    @property
    def iteration(self):
        return self.current_iteration.iteration if self.current_iteration else 0

    def run_calibration(self):
        """
        Create and run a complete multi-iteration calibration suite.
        """
        # Check experiment name as early as possible
        if not validate_exp_name(self.name):
            exit()

        self.location = SetupParser.get('type')

        self.create_calibration(self.location)

        self.run_iterations()

    def run_iterations(self, iteration=0):
        """
        Run iterations in a loop
        """
        self.calibration_start = datetime.now().replace(microsecond=0)

        # normal run
        for i in range(iteration, self.max_iterations):
            self.current_iteration = self.create_iteration_state(i)
            self.current_iteration.run()
            self.post_iteration()
        self.finalize_calibration()

        # Print the calibration finish time
        current_time = datetime.now()
        calibration_time_elapsed = current_time - self.calibration_start
        logger.info("Calibration done (took %s)" % verbose_timedelta(calibration_time_elapsed))

    def post_iteration(self):
        self.all_results = self.current_iteration.all_results
        self.summary_table = self.current_iteration.summary_table
        self.cache_calibration(iteration=self.iteration+1)

    def set_experiment_builder_function(self, exp_builder_function):
        """
        Set the experiment builder to a predefined one, such that exp_builder_func will return it
        Args:
            exp_builder_function: an experiment builder object

        Returns: no return

        """
        self.experiment_builder_function = exp_builder_function

    def exp_builder_func(self, next_params, n_replicates=None):
        if self.experiment_builder_function is not None:
            builder = self.experiment_builder_function
        else:
            if not n_replicates:
                n_replicates = self.sim_runs_per_param_set

            builder = ModBuilder.from_combos(
                    [ModFn(self.config_builder.__class__.set_param, 'Run_Number', i+1) for i in range(n_replicates)],
                    [ModFn(site.setup_fn) for site in self.sites],
                    [ModFn(self.map_sample_to_model_input_fn, index, samples.copy() if n_replicates > 1 else samples) for index, samples in  enumerate(next_params)]
            )
        return builder

    def create_iteration_state(self, iteration):
        if self.resume:
            self.resume = False
            self.current_iteration.calibration_start = self.calibration_start
            return self.current_iteration

        return IterationState(iteration=iteration,
                              calibration_name=self.name,
                              location=self.location,
                              suite_id=self.suite_id,
                              next_point_algo=self.next_point,
                              exp_builder_func=self.exp_builder_func,
                              site_analyzer_names=self.site_analyzer_names(),
                              analyzer_list=self.analyzer_list,
                              config_builder=self.config_builder,
                              plotters=self.plotters,
                              all_results=self.all_results,
                              calibration_start=self.calibration_start)

    def create_calibration(self, location):
        """
        Create the working directory for a new calibration.
        Cache the relevant suite-level information to allow re-initializing this instance.
        """
        if os.path.exists(self.name):
            logger.info("Calibration with name %s already exists in current directory" % self.name)
            var = ""
            while var not in ('R', 'B', 'C', 'P', 'A'):
                var = input('Do you want to [R]esume, [B]ackup + run, [C]leanup + run, Re-[P]lot, [A]bort:  ')
                var = var.upper()

            # Abort
            if var == 'A':
                exit()
            elif var == 'B':
                tstamp = re.sub('[ :.-]', '_', str(datetime.now()))
                shutil.move(self.name, "%s_backup_%s" % (self.name, tstamp))
                self.create_calibration(location)
            elif var == "C":
                self.cleanup()
                self.create_calibration(location)
            elif var == "R":
                self.resume_calibration()
                exit()  # avoid calling self.run_iterations(**kwargs)
            elif var == "P":
                self.replot_calibration(iteration=None)
                exit()  # avoid calling self.run_iterations(**kwargs)
        else:
            os.mkdir(self.name)
            self.cache_calibration()

    def finalize_calibration(self):
        """
        Get the final samples from the next point algorithm.
        """
        final_samples = self.next_point.get_final_samples()
        print("\nFinal samples")
        for k, v in final_samples['final_samples'].items():
            print("{}: {}".format(k, v))

        self.cache_calibration(**final_samples)

        # remove any leftover experiments
        self.cleanup_orphan_experiments()

    def cache_calibration(self, **kwargs):
        """
        Cache information about the CalibManager that is needed to resume after an interruption.
        N.B. This is not currently the complete state, some of which relies on nested and frozen functions.
        As such, the 'resume' logic relies on the existence of the original configuration script.
        """
        state = {'name': self.name,
                 'location': self.location,
                 'suites': self.suites,
                 'iteration': self.iteration,
                 'param_names': self.param_names(),
                 'sites': self.site_analyzer_names(),
                 'results': self.serialize_results(),
                 'setup_overlay_file': SetupParser.setup_file,
                 'selected_block': SetupParser.selected_block,
                 'calibration_start': self.calibration_start}
        state.update(kwargs)
        json.dump(state, open(os.path.join(self.name, 'CalibManager.json'), 'w'), indent=4, cls=NumpyEncoder)

    def backup_calibration(self):
        """
        Backup CalibManager.json for resume action
        """
        calibration_path = os.path.join(self.name, 'CalibManager.json')
        if os.path.exists(calibration_path):
            backup_id = 'backup_' + re.sub('[ :.-]', '_', str(datetime.now().replace(microsecond=0)))
            shutil.copy(calibration_path, os.path.join(self.name, 'CalibManager_%s.json' % backup_id))

    def serialize_results(self):
        if self.all_results is None:
            return []

        if not isinstance(self.all_results, pd.DataFrame):
            return self.all_results

        self.all_results.index.name = 'sample'
        data = self.all_results.reset_index()

        data.iteration = data.iteration.astype(int)
        data['sample'] = data['sample'].astype(int)

        return data.to_dict(orient='list')

    def resume_calibration(self, iteration=None, iter_step=None):
        self.resume = True

        # load and validate calibration
        self.load_calibration(iteration, iter_step)

        # resume from a given iteration
        self.run_iterations(self.iteration)

    def load_calibration(self, iteration=None, iter_step=None):
        # step 1: load calibration
        if not os.path.isdir(self.name):
            raise Exception('Unable to find existing calibration in directory: %s' % self.name)

        calib_data = self.read_calib_data()
        if calib_data is None or not calib_data:
            raise Exception('Metadata is empty in %s/CalibManager.json' % self.name)

        # step 2: load basic info
        self.location = calib_data.get('location')
        self.latest_iteration = int(calib_data.get('iteration', 0))
        self.suites = calib_data['suites']

        # step 3: validate inputs
        self.current_iteration, resume_point = self.retrieve_iteration(iteration, iter_step)

        # step 4: load all_results
        results = calib_data.get('results')
        if isinstance(results, dict):
            self.all_results = pd.DataFrame.from_dict(results, orient='columns')
        elif isinstance(results, list):
            self.all_results = results

        # step 5: update required objects for resume
        self.current_iteration.update(**self.required_components)

        # Resume the iteration
        self.current_iteration.resume(resume_point)

    def retrieve_iteration(self, iteration=None, iter_step=None):
        if iteration is None:
            resume_iteration = self.latest_iteration
        else:
            resume_iteration = iteration

        # validate input iteration
        if self.latest_iteration < resume_iteration:
            raise Exception(
                "The iteration '%s' is beyond the maximum iteration '%s'" % (resume_iteration, self.latest_iteration))

        # validate input iter_step
        it = IterationState.restore_state(self.name, resume_iteration)

        latest_step = StatusPoint[it.status]
        if iter_step is None:
            iter_step = latest_step.name

        given_step = StatusPoint[iter_step]
        if given_step == StatusPoint.analyze:
            given_step = StatusPoint.running
            
        if given_step.value > latest_step.value:
            raise Exception("The iter_step '%s' is beyond the latest step '%s'" % (given_step.name, latest_step.name))

        # move forward if status is done
        if given_step == StatusPoint.done:
            iter_step = StatusPoint.next_point.name

        # finally check user input location and experiment location and provide options for resume
        self.check_location(it)

        return it, StatusPoint[iter_step]

    def check_location(self, iteration_state):
        """
        - Handle the case: process got interrupted but it still runs on remote
        - Handle location change case: may resume from commission instead
        """
        # Step 1: Checking possible location changes
        exp_id = iteration_state.experiment_id

        if not exp_id and iteration_state.status == StatusPoint.iteration_start.name:
            return

        exp = retrieve_experiment(exp_id)

        if not exp:
            var = input("Cannot restore Experiment 'exp_id: %s'. Force to resume from commission... Continue ? [Y/N]" % exp_id if exp_id else 'None')
            # force to resume from commission
            if var.upper() == 'Y':
                iteration_state.resume_point = StatusPoint.commission
            else:
                logger.info("Answer is '%s'. Exiting...", var.upper())
                exit()

        # If location has been changed, will double check user for a special case before proceed...
        if self.location != exp.location:
            location = SetupParser.get('type')
            var = input("Location has been changed from '%s' to '%s'. Resume will start from commission instead, do you want to continue? [Y/N]:  " % (
                exp.location, location))
            if var.upper() == 'Y':
                self.current_iteration.resume_point = StatusPoint.commission
            else:
                logger.info("Answer is '%s'. Exiting...", var.upper())
                exit()

    def load_experiment_from_iteration(self, iteration=None):
        """
        Load experiment for a given or the latest iteration
        """
        if iteration is None:
            # restore the existing calibration data
            calib_data = self.read_calib_data()

            # Get the last iteration
            latest_iteration = calib_data.get('iteration', None)
        else:
            latest_iteration = iteration

        try:
            # Restore IterationState
            it = IterationState.from_file(os.path.join(self.name, 'iter%d' % latest_iteration, 'IterationState.json'))

            # Get experiment by id
            return DataStore.get_experiment(it.experiment_id)
        except:
            return None

    def kill(self):
        """
        Kill the current calibration
        """
        exp = self.load_experiment_from_iteration()
        if not exp: return

        # Cancel simulations for all active managers
        try:
            exp_manager = ExperimentManagerFactory.from_experiment(exp)
            exp_manager.cancel_experiment()
        except RuntimeError:
            logger.info("Could not delete the associated experiment...")
            return

        logger.info("Waiting to complete cancellation...")
        exp_manager.wait_for_finished(verbose=False, sleep_time=1)

        # Print confirmation
        logger.info("Calibration %s successfully cancelled!" % self.name)

    def cleanup(self):
        """
        Cleanup the current calibration
        - Delete the result directory
        - If LOCAL -> also delete the simulations
        """
        try:
            calib_data = self.read_calib_data()
        except Exception:
            logger.info('Calib data cannot be read -> skip')
            calib_data = None

        if calib_data:
            with SetupParser.TemporaryBlock(calib_data['selected_block']):
                # Retrieve suite ids and iter_count
                suites = calib_data.get('suites')
                iter_count = calib_data.get('iteration')

                # Kill
                self.kill()

                # Delete the simulations too
                logger.info('Cleaning up calibration %s' % self.name)
                for i in range(0, iter_count + 1):
                    # Get the iteration cache
                    iteration_cache = os.path.join(self.name, 'iter%d' % i, 'IterationState.json')

                    if not os.path.exists(iteration_cache):
                        break
                    # Retrieve the iteration state
                    it = IterationState.from_file(iteration_cache)

                    # Create the associated experiment manager and ask for deletion
                    try:
                        exp_mgr = ExperimentManagerFactory.from_experiment(DataStore.get_experiment(it.experiment_id))
                        exp_mgr.hard_delete()
                    except: continue

                # Delete all HPC suites (the local suites are only carried by experiments)
                for suite in suites:
                    if suite['type'] == "HPC":
                        logger.info('Delete COMPS suite %s' % suite['id'])
                        COMPS_login(SetupParser.get('server_endpoint'))
                        from simtools.Utilities.COMPSUtilities import delete_suite
                        delete_suite(suite['id'])

        # Then delete the whole directory
        calib_dir = os.path.abspath(self.name)
        if os.path.exists(calib_dir):
            try:
                shutil.rmtree(calib_dir)
            except OSError:
                logger.error("Failed to delete %s" % calib_dir)
                logger.error("Try deleting the folder manually before retrying the calibration.")

    def read_calib_data(self, force=False):
        try:
            return json.load(open(os.path.join(self.name, 'CalibManager.json'), 'rb'))
        except IOError:
            if not force:
                raise Exception('Unable to find metadata in %s/CalibManager.json' % self.name)
            else:
                return None

    def read_iteration_data(self, iteration):
        iteration_cache = os.path.join(self.name, 'iter%d' % iteration, 'IterationState.json')
        return IterationState.from_file(iteration_cache)

    def get_experiment_from_iteration(self, iteration=None, force_metadata=False):
        """
        Retrieve experiment for a given iteration
        """
        exp = None

        # Only check iteration for resume cases
        if force_metadata:
            iteration = self.adjust_iteration(iteration)
            it = self.read_iteration_data(iteration)
            exp = DataStore.get_experiment(it.experiment_id)

        return exp

    def adjust_iteration(self, iteration=None, calib_data=None):
        """
        Validate iteration against latest_iteration
        return adjusted iteration
        """
        # If calib_data is None or Empty, load data
        if calib_data is None or not calib_data:
            calib_data = self.read_calib_data()

        # Get latest iteration #
        latest_iteration = calib_data.get('iteration', None)

        # Handle special case
        if latest_iteration is None:
            return 0

        # If no iteration passed in, take latest_iteration as instead
        if iteration is None:
            iteration = latest_iteration

        # Adjust input iteration
        if latest_iteration < iteration:
            iteration = latest_iteration

        return iteration

    def cleanup_orphan_experiments(self):
        """
            - Display all orphan experiments for this calibration
            - Hard delete all orphans
        """
        exp_orphan_list = self.list_orphan_experiments()
        for experiment in exp_orphan_list:
            ExperimentManagerFactory.from_experiment(experiment).hard_delete()

        if len(exp_orphan_list) > 0:
            orphan_str_list = ['- %s - %s' % (exp.exp_id, exp.exp_name) for exp in exp_orphan_list]
            logger.info('\nOrphan Experiment List:')
            logger.info('\n'.join(orphan_str_list))
            logger.info('\n')
            logger.info('Note: the detected orphan experiment(s) have been deleted.')

    def list_orphan_experiments(self):
        """
        Get orphan experiment list for this calibration
        """
        suite_ids, exp_ids = self.get_experiments()
        exp_orphan_list = DataStore.list_leftover(suite_ids, exp_ids)
        return exp_orphan_list

    def get_experiments(self):
        """
        Retrieve suite_ids and their associated exp_ids
        """
        # restore the existing calibration data
        calib_data = self.read_calib_data()
        latest_iteration = calib_data.get('iteration')

        exp_ids = []
        for i in range(0, latest_iteration + 1):
            iter_dir = os.path.join(self.name, 'iter%d' % i)
            iter_path = os.path.join(iter_dir, 'IterationState.json')
            if not os.path.exists(iter_path):
                continue

            iter_data = json.load(open(iter_path, 'rb'))
            exp_id = iter_data.get('experiment_id', None)
            if exp_id:
                exp_ids.append(exp_id)

        return [suite['id'] for suite in calib_data['suites']], exp_ids

    @property
    def calibration_path(self):
        return os.path.join(self.name, 'CalibManager.json')

    @property
    def analyzer_list(self):
        analyzer_list = []
        for site in self.sites:
            for analyzer in site.analyzers:
                analyzer.result = []
                analyzer_list.append(analyzer)

        return analyzer_list

    @property
    def required_components(self):
        # update required objects for resume, reanalyze and replot
        kwargs = {
                    'exp_builder_func': self.exp_builder_func,
                    'next_point_algo': self.next_point,
                    'config_builder': self.config_builder,
                    'analyzer_list': self.analyzer_list,
                    'plotters': self.plotters,
                    'all_results': self.all_results,
                    'calibration_start': self.calibration_start,
                    'site_analyzer_names': self.site_analyzer_names()
                }
        return kwargs

    def iteration_directory(self):
        return os.path.join(self.name, 'iter%d' % self.iteration)

    def state_for_iteration(self, iteration):
        iter_directory = os.path.join(self.name, 'iter%d' % iteration)
        return IterationState.from_file(os.path.join(iter_directory, 'IterationState.json'))

    def param_names(self):
        return self.next_point.get_param_names()

    def site_analyzer_names(self):
        return {site.name: [a.uid for a in site.analyzers] for site in self.sites}

    def get_last_iteration(self):
        """
        Determines the last (most recent) completed iteration number.
        Returns: the last completed iteration number as an int
        """
        calib_data = self.read_calib_data()
        last_iteration_number = int(calib_data.get('iteration', None))
        iteration = self.state_for_iteration(iteration=last_iteration_number)
        if last_iteration_number is None:
            raise KeyError('Could not determine what the most recent iteration is.')
        if iteration.status != StatusPoint.done:
            last_iteration_number -= 1
        return last_iteration_number

    def get_parameter_sets_with_likelihoods(self):
        """
        Returns: a list of ParameterSet objects.
        """
        last_iteration = self.get_last_iteration()
        parameter_sets = []
        for iteration_number in range(last_iteration+1):
            iteration = self.state_for_iteration(iteration=iteration_number)
            iteration_param_sets = iteration.get_parameter_sets_with_likelihoods()
            parameter_sets += iteration_param_sets
        return parameter_sets
