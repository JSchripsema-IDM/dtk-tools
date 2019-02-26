import json
import os
import time
from datetime import datetime
import pandas as pd
from calibtool.ParameterSet import ParameterSet
from calibtool.utils import StatusPoint
from simtools.Analysis.AnalyzeManager import AnalyzeManager
from simtools.DataAccess.DataStore import DataStore
from simtools.ExperimentManager.ExperimentManagerFactory import ExperimentManagerFactory
from simtools.Utilities.Encoding import NumpyEncoder, json_numpy_obj_hook
from simtools.Utilities.Experiments import retrieve_experiment
from simtools.Utilities.General import init_logging
from simtools.Utilities import verbose_timedelta

logger = init_logging("Calibration")


class IterationState:
    """
    Holds the settings, parameters, simulation state, analysis results, etc.
    for one calibtool iteration.

    Allows for the resumption or extension of existing CalibManager instances
    from an arbitrary point in the iterative process.
    """

    def __init__(self, **kwargs):
        self.iteration = 0
        self.calibration_name = None
        self.suite_id = {}
        self.samples_for_this_iteration = {}
        self.next_point = {}
        self.simulations = {}
        self.analyzers = {}
        self.results = {}
        self.experiment_id = None
        self.exp_manager = None
        self.next_point_algo = None
        self.analyzer_list = []
        self.site_analyzer_names = {}
        self.config_builder = None
        self.exp_builder_func = None
        self.plotters = []
        self.all_results = None
        self.summary_table = None
        self.iteration_start = None
        self.calibration_start = None

        if 'calibration_start' in kwargs:
            cs = kwargs.pop('calibration_start') or datetime.now().replace(microsecond=0)
            if not isinstance(cs, datetime):
                self.calibration_start = datetime.strptime(cs, '%Y-%m-%d %H:%M:%S')
            else:
                self.calibration_start = cs

        if 'iteration_start' in kwargs:
            cs = kwargs.pop('iteration_start') or datetime.now().replace(microsecond=0)
            if not isinstance(cs, datetime):
                self.iteration_start = datetime.strptime(cs, '%Y-%m-%d %H:%M:%S')
            else:
                self.iteration_start = cs

        self._status = None
        self.update(**kwargs)
        if self._status is not None:
            self._status = StatusPoint[self._status]

        if not os.path.exists(self.iteration_directory):
            os.makedirs(self.iteration_directory)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status
        self.save()

    def update(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def restore_results(self, iteration):
        """
        Restore summary results from serialized state.
        """
        # Depending on the type of results (lists or dicts), handle differently how we treat the results
        # This should be refactor to take care of both cases at once
        if len(self.all_results) == 0:
            self.all_results = None
        elif isinstance(self.all_results, pd.DataFrame):
            self.all_results.set_index('sample', inplace=True)
            self.all_results = self.all_results[self.all_results.iteration <= iteration]
        elif isinstance(self.all_results, list):
            self.all_results = self.all_results[iteration]

    def resume(self, iter_step):
        # step 1: If we know we are running -> recreate the exp_manager
        if iter_step.value >= StatusPoint.running.value:
            self.exp_manager = ExperimentManagerFactory.from_experiment(retrieve_experiment(self.experiment_id))

        # step 2: restore next_point
        if iter_step not in (StatusPoint.plot, StatusPoint.next_point, StatusPoint.running) and self.iteration != 0:
            if iter_step == StatusPoint.commission or iter_step == StatusPoint.iteration_start:
                iteration_state = IterationState.restore_state(self.calibration_name, self.iteration - 1)
                self.next_point_algo.set_state(iteration_state.next_point, self.iteration - 1)
            elif iter_step == StatusPoint.analyze:
                iteration_state = IterationState.restore_state(self.calibration_name, self.iteration)
                self.next_point_algo.set_state(iteration_state.next_point, self.iteration)

                # For IMIS ONLY!
                self.next_point_algo.restore(IterationState.restore_state(self.calibration_name, self.iteration - 1))
        else:
            self.next_point_algo.set_state(self.next_point, self.iteration)

        # step 3: restore Calibration results
        if self.iteration > 0 and iter_step.value < StatusPoint.plot.value:
            # it will combine current results with previous results
            self.restore_results(self.iteration - 1)
        else:
            # it will use the current results and resume from next iteration
            self.restore_results(self.iteration)

        # step 4: prepare resume states
        if iter_step.value <= StatusPoint.commission.value:
            # need to run simulations
            self.simulations = {}

        if iter_step.value <= StatusPoint.analyze.value:
            # just need to calculate the results
            self.results = {}

        self._status = StatusPoint(iter_step.value - 1) if iter_step.value > 0 else None

    def run(self):
        # START_STEP
        if not self.status:
            self.starting_step()

        # COMMISSION STEP
        if self.status == StatusPoint.iteration_start:
            self.commission_step()

        # RUNNING
        if self.status == StatusPoint.commission:
            self.status = StatusPoint.running
            self.wait_for_finished()

        # ANALYZE STEP
        if self.status == StatusPoint.running:
            self.analyze_step()

        # PLOTTING STEP
        if self.status == StatusPoint.analyze:
            self.plotting_step()

        # Done with calibration? exit the loop
        if self.finished():
            return

        # NEXT STEP
        if self.status == StatusPoint.plot:
            self.next_point_step()

        self.status = StatusPoint.done

    def starting_step(self):
        self.status = StatusPoint.iteration_start

        # Restart the time for each iteration
        self.iteration_start = datetime.now().replace(microsecond=0)
        logger.info('---- Starting Iteration %d ----' % self.iteration)

    def commission_step(self):
        # Get the params from the next_point
        next_params = self.next_point_algo.get_samples_for_iteration(self.iteration)
        self.set_samples_for_iteration(next_params, self.next_point_algo)

        # Then commission
        self.commission_iteration(next_params)

        # Ready for commissioning
        self.status = StatusPoint.commission

        # Call the plot for post commission plots
        self.plot_iteration()

    def analyze_step(self):
        # Analyze the iteration
        self.analyze_iteration()

        # Ready for analyzing
        self.status = StatusPoint.analyze

    def plotting_step(self):
        # Ready for plotting
        self.status = StatusPoint.plot

        # Plot the iteration
        self.plot_iteration()

    def next_point_step(self):
        # Ready for next point
        self.status = StatusPoint.next_point

        self.next_point_algo.update_iteration(self.iteration)

    def commission_iteration(self, next_params):
        """
        Commission an experiment of simulations constructed from a list of combinations of
        random seeds, calibration sites, and the next sample points.
        Cache the relevant experiment and simulation information to the IterationState.
        """
        if self.simulations:
            logger.info('Reloading simulation data from cached iteration (%s) state.' % self.iteration)
            self.exp_manager = ExperimentManagerFactory.from_experiment(
                DataStore.get_experiment(self.experiment_id))
        else:
            self.exp_manager = ExperimentManagerFactory.init()

            # use passed in function to create exp_builder
            exp_builder = self.exp_builder_func(next_params)

            self.exp_manager.run_simulations(
                config_builder=self.config_builder,
                exp_name='%s_iter%d' % (self.calibration_name, self.iteration),
                exp_builder=exp_builder,
                suite_id=self.suite_id)

            self.simulations = self.exp_manager.experiment.toJSON()['simulations']
            self.experiment_id = self.exp_manager.experiment.exp_id
            self.save()

    def plot_iteration(self):
        # Run all the plotters
        for plotter in self.plotters:
            plotter.visualize(self)

    def analyze_iteration(self):
        """
        Analyze the output of completed simulations by using the relevant analyzers by site.
        Cache the results that are returned by those analyzers.
        """
        if self.results:
            logger.info('Reloading results from cached iteration state.')
            return self.results['total']

        if not self.exp_manager:
            self.exp_manager = ExperimentManagerFactory.from_experiment(self.experiment_id)
        
        analyzerManager = AnalyzeManager(exp_list=self.exp_manager.experiment,
                                         analyzers=self.analyzer_list,
                                         working_dir=self.iteration_directory,
                                         verbose=True,
                                         force_manager_working_directory=True)

        if not analyzerManager.analyze():
            print("Error encountered during analysis... Exiting")
            exit()

        # Ask the analyzers to cache themselves
        cached_analyses = {a.uid: a.cache() if callable(a.cache) else {} for a in analyzerManager.analyzers}
        logger.debug(cached_analyses)

        # Get the results from the analyzers and ask the next point how it wants to cache them
        results = pd.DataFrame({a.uid: a.results for a in analyzerManager.analyzers})
        cached_results = self.next_point_algo.get_results_to_cache(results)

        # Store the analyzers and results in the iteration state
        self.analyzers = cached_analyses
        self.results = cached_results

        # Set those results in the next point algorithm
        self.next_point_algo.set_results_for_iteration(self.iteration, results)

        # Update the summary table and all the results
        self.all_results, self.summary_table = self.next_point_algo.update_summary_table(self, self.all_results)
        logger.info(self.summary_table)

    def wait_for_finished(self, verbose=True, init_sleep=1.0, sleep_time=10):
        while True:
            time.sleep(init_sleep)
            self.exp_manager.refresh_experiment()

            # Output time info
            current_time = datetime.now()
            iteration_time_elapsed = current_time - self.iteration_start
            calibration_time_elapsed = current_time - self.calibration_start

            logger.info('\n\nCalibration: %s' % self.calibration_name)
            logger.info('Calibration started: %s' % self.calibration_start)
            logger.info('Current iteration: Iteration %s' % self.iteration)
            logger.info('Current Iteration Started: %s' % self.iteration_start)
            logger.info('Time since iteration started: %s' % verbose_timedelta(iteration_time_elapsed))
            logger.info('Time since calibration started: %s\n' % verbose_timedelta(calibration_time_elapsed))

            # Display the statuses
            if verbose:
                self.exp_manager.print_status()

            # If Calibration has been canceled -> exit
            if self.exp_manager.any_failed_or_cancelled():
                # Kill the remaining simulations
                print("\nOne or more simulations failed/cancelled. Calibration cannot continue. Exiting...")
                self.kill()
                exit()

            # Test if we are all done
            if self.exp_manager.experiment.is_done():
                break

            time.sleep(sleep_time)

        # Print the status one more time
        iteration_time_elapsed = current_time - self.iteration_start
        logger.info("Iteration %s done (took %s)" % (self.iteration, verbose_timedelta(iteration_time_elapsed)))

    def kill(self):
        """
        Kill the current calibration
        """
        self.exp_manager.cancel_experiment()

        logger.info("Waiting to complete cancellation...")
        self.exp_manager.wait_for_finished(verbose=False, sleep_time=1)

        # Print confirmation
        logger.info("Calibration %s successfully cancelled!" % self.calibration_name)

    @property
    def iteration_directory(self):
        return os.path.join(self.calibration_name, 'iter%d' % self.iteration)

    @property
    def iteration_file(self):
        return os.path.join(self.iteration_directory, "IterationState.json")

    @property
    def param_names(self):
        return self.next_point_algo.get_param_names()

    def finished(self):
        """ The next-point algorithm has reached its termination condition. """
        return self.next_point_algo.end_condition()

    @classmethod
    def from_file(cls, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls(**json.load(f, object_hook=json_numpy_obj_hook))

    def to_file(self):
        state = {
            'status': self.status.name,
            'samples_for_this_iteration': self.samples_for_this_iteration,
            'analyzers': self.analyzers,
            'iteration': self.iteration,
            'iteration_start': self.iteration_start,
            'results': self.results,
            'calibration_name': self.calibration_name,
            'experiment_id': self.experiment_id,
            'simulations': self.simulations,
            'next_point': self.next_point_algo.get_state(),
            'suite_id': self.suite_id
        }

        with open(self.iteration_file, 'w') as f:
            json.dump(state, f, indent=4, cls=NumpyEncoder)

    @classmethod
    def restore_state(cls, exp_name, iteration):
        """
        Restore IterationState
        """
        iter_directory = os.path.join(exp_name, 'iter%d' % iteration)
        iter_file = os.path.join(iter_directory, 'IterationState.json')
        return cls.from_file(iter_file)

    def set_samples_for_iteration(self, samples, next_point):
        if isinstance(samples, pd.DataFrame):
            dtypes = {name: str(data.dtype) for name, data in samples.iteritems()}
            self.samples_for_this_iteration_dtypes = dtypes
            samples_NaN_to_Null = samples.where(~samples.isnull(), other=None)
            self.samples_for_this_iteration = samples_NaN_to_Null.to_dict(orient='list')
        else:
            self.samples_for_this_iteration = samples

    def save(self):
        """
        Cache information about the IterationState that is needed to resume after an interruption.
        If resuming from an existing iteration, also copy to backup the initial cached state.
        """
        if not self.calibration_name: return
        self.to_file()

    def get_parameter_sets_with_likelihoods(self):
        likelihoods = self.results['total']  # an ordered list of likelihood floats
        param_dicts = self.samples_for_this_iteration  # an ordered list of input input parameters (user knobs)
        if len(likelihoods) != len(param_dicts):
            raise Exception('Inconsistent iteration data. \'total\' and \'samples_for_this_iteration\' '
                            'are not the same length')

        # find and attach the sim_id & run number for every parameter set replicate
        parameter_sets = []
        for sample_index in range(len(param_dicts)):
            param_dict = param_dicts[sample_index]
            likelihood = likelihoods[sample_index]

            replicates_dict = {sim_id: sim_dict for sim_id, sim_dict in self.simulations.items()
                               if sim_dict['__sample_index__'] == sample_index}
            if len(replicates_dict) == 0:
                raise Exception('There should be at least one simulation associated with sample_index: %s. '
                                'There are none.' % (sample_index, len(replicates_dict)))

            # Create a distinct ParameterSet object for each replicate
            for sim_id, replicate_dict in replicates_dict.items():
                run_number = replicate_dict['Run_Number']
                parameter_set = ParameterSet(param_dict=param_dict, likelihood=likelihood,
                                             iteration_number=self.iteration, sim_id=sim_id, run_number=run_number)
                parameter_sets.append(parameter_set)

        return parameter_sets
