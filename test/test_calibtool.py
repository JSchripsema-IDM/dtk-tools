import glob
import json
import os
import unittest
from argparse import Namespace
from subprocess import Popen, PIPE, STDOUT

import copy
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shutil
from configparser import ConfigParser
from scipy.stats import norm, uniform, multivariate_normal
from calibtool.IterationState import IterationState
from calibtool.Prior import MultiVariatePrior, SampleRange, SampleFunctionContainer
from calibtool.algorithms.IMIS import IMIS
from calibtool.commands import get_calib_manager
from simtools.DataAccess.DataStore import DataStore
from simtools.ExperimentManager.ExperimentManagerFactory import ExperimentManagerFactory
from simtools.Utilities.General import nostdout
from simtools.Utilities.Initialization import load_config_module
from simtools.Utilities.Experiments import validate_exp_name


class TestCommands(unittest.TestCase):
    def setUp(self):
        self.current_cwd = os.getcwd()
        self.calibration_dir = os.path.join(self.current_cwd, 'calibration')
        self.input_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'input')

        if os.path.exists(self.calibration_dir):
            shutil.rmtree(self.calibration_dir)

        os.mkdir(self.calibration_dir)
        os.chdir(self.calibration_dir)

        cp = ConfigParser()
        cp.add_section('LOCAL')
        cp.set('LOCAL', 'type', 'LOCAL')
        cp.set('LOCAL', 'input_root', os.path.join(self.input_path, 'calibration_input'))
        cp.write(open(os.path.join(self.calibration_dir, 'simtools.ini'), 'w'))

        shutil.copy(os.path.join(self.input_path,'dummy_calib.py'), 'calibration')

    def tearDown(self):
        # Change the dir back to normal
        os.chdir(self.current_cwd)

        # get all iterations
        for iteration_folder in glob.glob(os.path.join(self.calibration_dir,"test_dummy_calibration","iter*")):
            it = IterationState.from_file(os.path.join(iteration_folder,'IterationState.json'))
            exp_mgr = ExperimentManagerFactory.from_experiment(DataStore.get_experiment(it.experiment_id))
            exp_mgr.hard_delete()

        # Clear the dir
        shutil.rmtree(self.calibration_dir)


    def exec_calib(self, params):
        """
        params is a list like ['calibtool', 'run', 'dummy_calib.py']
        """
        os.chdir(self.calibration_dir)
        ctool = Popen(params, stdout=PIPE, stderr=STDOUT)
        ctool.communicate()

    def test_run_calibration(self):
        self.exec_calib(['calibtool', 'run', 'dummy_calib.py'])

        # Test if files are present
        calibpath = os.path.abspath('test_dummy_calibration')
        self.assertTrue(os.path.exists(calibpath))
        self.assertTrue(os.path.exists(os.path.join(calibpath, '_plots')))
        self.assertNotEqual(len(os.listdir(os.path.join(calibpath, '_plots'))), 0)
        self.assertTrue(os.path.exists(os.path.join(calibpath, 'iter0')))
        self.assertTrue(os.path.exists(os.path.join(calibpath, 'iter1')))
        self.assertTrue(os.path.exists(os.path.join(calibpath, 'CalibManager.json')))
        self.assertTrue(os.path.exists(os.path.join(calibpath, 'LL_all.csv')))

    def test_init_samples(self):
        mod = load_config_module('dummy_calib.py')

        # print (mod.next_point_kwargs)
        self.initial_samples = mod.next_point_kwargs['initial_samples']
        self.samples_per_iteration = mod.next_point_kwargs['samples_per_iteration']

        self.exec_calib(['calibtool', 'run', 'dummy_calib.py'])

        # Open the IterationState.json and save the values
        with open('test_dummy_calibration/iter0/IterationState.json', 'r') as fp:
            it = json.load(fp)
            self.assertEqual(self.initial_samples, len(it['parameters']['values']))

        with open('test_dummy_calibration/iter1/IterationState.json', 'r') as fp:
            it = json.load(fp)
            self.assertEqual(self.samples_per_iteration, len(it['parameters']['values']))

    def test_last_iteration(self):
        mod = load_config_module('dummy_calib.py')
        manager = mod.calib_manager
        self.max_iterations = manager.max_iterations

        self.exec_calib(['calibtool', 'run', 'dummy_calib.py'])

        # retrieve last iteration number
        with open('test_dummy_calibration/CalibManager.json', 'r') as fp:
            cm = json.load(fp)
            self.iteration = cm['iteration']

        it_list = glob.glob('test_dummy_calibration/iter*')

        # make sure numbers are match!
        self.assertEqual(self.max_iterations, len(it_list))
        self.assertEqual(self.max_iterations - 1, self.iteration)

        # make sure folder names are match!
        it_dirs = [os.path.basename(it) for it in it_list]
        it_flds = ['iter%s' % i for i in range(self.max_iterations)]
        self.assertListEqual(it_flds, it_dirs)

    def test_experiment_length(self):
        mod = load_config_module('dummy_calib.py')
        manager = mod.calib_manager

        self.assertTrue(validate_exp_name(manager.name))

    def test_missing_files(self):
        os.chdir(self.calibration_dir)
        mod = load_config_module('dummy_calib.py')
        manager = mod.calib_manager

        input_files = manager.config_builder.get_input_file_paths()
        input_files = {'Air_Migration_Filename': '   ', 'Land_Temperature_Filename': '',
                       'Family_Migration_Filename': '', 'Relative_Humidity_Filename': '', 'Load_Balance_Filename': '',
                       'Vector_Migration_Filename_Local': '', 'Air_Temperature_Filename': '',
                       'Vector_Migration_Filename_Regional': '', 'Demographics_Filenames': [],
                       'Test_Filenames': ['', ' ', ""],
                       "Demo_Filename": " ",
                       'Local_Migration_Filename': '', 'Regional_Migration_Filename': '',
                       'Sea_Migration_Filename': '', 'Rainfall_Filename': '', 'Campaign_Filename': 'campaign.json'}

        exp_manager = ExperimentManagerFactory.from_setup(manager.setup)
        input_root, missing_files = exp_manager.check_input_files(input_files)

        # Py-passing 'Campaign_Filename' for now.
        if 'Campaign_Filename' in missing_files:
            print("By-passing file '%s'..." % missing_files['Campaign_Filename'])
            missing_files.pop('Campaign_Filename')

        self.assertEqual(len(missing_files), 0)

        # check empty files
        empty_files = [f for f in missing_files if len(f.strip()) == 0]
        self.assertEqual(len(empty_files), 0)

    def test_validate_input_files(self):
        mod = load_config_module('dummy_calib.py')
        manager = mod.calib_manager

        exp_manager = ExperimentManagerFactory.from_setup(manager.config_builder)
        self.assertTrue(exp_manager.validate_input_files())

    def test_find_best_iteration_for_resume(self):
        mod = load_config_module('dummy_calib.py')
        manager = mod.calib_manager

        with open('test_dummy_calibration/CalibManager.json', 'r') as fp:
            calib_data = json.load(fp)

        # resume from latest iteration
        iteration = manager.find_best_iteration_for_resume(None, calib_data)
        self.assertEqual(iteration, 1)

        # given iteration for resume
        iteration = manager.find_best_iteration_for_resume(1, calib_data)
        self.assertEqual(iteration, 1)

        # given iteration for resume
        iteration = manager.find_best_iteration_for_resume(0, calib_data)
        self.assertEqual(iteration, 0)

        # given fake iteration for resume
        iteration = manager.find_best_iteration_for_resume(2, calib_data)
        self.assertEqual(iteration, 1)

    def test_resume_point_white_box(self):
        mod = load_config_module('dummy_calib.py')
        manager = mod.calib_manager

        with open(os.path.join(self.current_cwd,'test_dummy_calibration','CalibManager.json'), 'r') as fp:
            calib_data = json.load(fp)

        # scenario: resume from farthest point by default #

        # resume from latest iteration
        iteration = manager.find_best_iteration_for_resume(None, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)
        self.assertEqual(manager.iteration_state.resume_point, 3)  # next_point

        # resume from given iteration 1
        iteration = manager.find_best_iteration_for_resume(1, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)

        self.assertEqual(manager.iteration_state.resume_point, 3)  # next_point

        # resume from given iteration 0
        iteration = manager.find_best_iteration_for_resume(0, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)

        self.assertEqual(manager.iteration_state.resume_point, 3)  # next_point

        # scenario: resume from commission #
        manager.iter_step = 'commission'

        # resume from latest iteration
        iteration = manager.find_best_iteration_for_resume(None, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)
        self.assertEqual(manager.iteration_state.resume_point, 1)  # commission

        # resume from given iteration 1
        iteration = manager.find_best_iteration_for_resume(1, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)

        self.assertEqual(manager.iteration_state.resume_point, 1)  # commission

        # resume from given iteration 0
        iteration = manager.find_best_iteration_for_resume(0, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)

        self.assertEqual(manager.iteration_state.resume_point, 1)  # commission

        # scenario: resume from analyze #
        manager.iter_step = 'analyze'

        # resume from latest iteration
        iteration = manager.find_best_iteration_for_resume(None, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)
        self.assertEqual(manager.iteration_state.resume_point, 2)  # analyze

        # resume from given iteration 1
        iteration = manager.find_best_iteration_for_resume(1, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)

        self.assertEqual(manager.iteration_state.resume_point, 2)  # analyze

        # resume from given iteration 0
        iteration = manager.find_best_iteration_for_resume(0, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)

        self.assertEqual(manager.iteration_state.resume_point, 2)  # analyze

        # scenario: resume from next_point #
        manager.iter_step = 'next_point'

        # resume from latest iteration
        iteration = manager.find_best_iteration_for_resume(None, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)
        self.assertEqual(manager.iteration_state.resume_point, 3)  # next_point

        # resume from given iteration 1
        iteration = manager.find_best_iteration_for_resume(1, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)

        self.assertEqual(manager.iteration_state.resume_point, 3)  # next_point

        # resume from given iteration 0
        iteration = manager.find_best_iteration_for_resume(0, calib_data)
        with nostdout():
            manager.prepare_resume_point_for_iteration(iteration)

        self.assertEqual(manager.iteration_state.resume_point, 3)  # next_point

    def test_resume_point_black_box(self):
        self.exec_calib(['calibtool', 'run', 'dummy_calib.py'])
        self.run_info = [os.stat('test_dummy_calibration/iter0/IterationState.json').st_mtime,
                         os.stat('test_dummy_calibration/iter0/IterationState.json').st_size]

        self.exec_calib(['calibtool', 'resume', 'dummy_calib.py'])
        self.resume_info = [os.stat('test_dummy_calibration/iter0/IterationState.json').st_mtime,
                            os.stat('test_dummy_calibration/iter0/IterationState.json').st_size]

        self.assertEqual(self.run_info[0], self.resume_info[0])
        self.assertEqual(self.run_info[1], self.resume_info[1])

    def test_resume_point_black_box2(self):
        print('test_resume_point_black_box2')
        self.exec_calib(['calibtool', 'run', 'dummy_calib.py'])
        self.run_info = [os.stat('test_dummy_calibration/iter0/IterationState.json').st_mtime,
                         os.stat('test_dummy_calibration/iter0/IterationState.json').st_size,
                         os.stat('test_dummy_calibration/iter1/IterationState.json').st_mtime,
                         os.stat('test_dummy_calibration/iter1/IterationState.json').st_size]

        self.exec_calib(['calibtool', 'resume', 'dummy_calib.py', '--iter_step', 'commission'])
        self.resume_info = [os.stat('test_dummy_calibration/iter0/IterationState.json').st_mtime,
                            os.stat('test_dummy_calibration/iter0/IterationState.json').st_size,
                            os.stat('test_dummy_calibration/iter1/IterationState.json').st_mtime,
                            os.stat('test_dummy_calibration/iter1/IterationState.json').st_size]

        # print (self.run_info)
        # print (self.resume_info)
        self.assertEqual(self.run_info[0], self.resume_info[0])
        self.assertEqual(self.run_info[1], self.resume_info[1])
        self.assertNotEquals(self.run_info[2], self.resume_info[2])
        self.assertNotEquals(self.run_info[3], self.resume_info[3])

    def test_resume_point_black_box3(self):
        self.exec_calib(['calibtool', 'run', 'dummy_calib.py'])
        self.run_info = [os.stat('test_dummy_calibration/iter0/IterationState.json').st_mtime,
                         os.stat('test_dummy_calibration/iter0/IterationState.json').st_size,
                         os.stat('test_dummy_calibration/iter1/IterationState.json').st_mtime,
                         os.stat('test_dummy_calibration/iter1/IterationState.json').st_size]

        self.exec_calib(['calibtool', 'resume', 'dummy_calib.py', '--iteration', '0', '--iter_step', 'commission'])
        self.resume_info = [os.stat('test_dummy_calibration/iter0/IterationState.json').st_mtime,
                            os.stat('test_dummy_calibration/iter0/IterationState.json').st_size,
                            os.stat('test_dummy_calibration/iter1/IterationState.json').st_mtime,
                            os.stat('test_dummy_calibration/iter1/IterationState.json').st_size]

        # print (self.run_info)
        # print (self.resume_info)
        self.assertNotEquals(self.run_info[0], self.resume_info[0])
        self.assertLess(self.run_info[0], self.resume_info[0])
        self.assertNotEquals(self.run_info[2], self.resume_info[2])
        self.assertLess(self.run_info[2], self.resume_info[2])

    @unittest.skip("demonstrating skipping")
    def test_selected_block_hpc_white_box(self):
        args = Namespace(config_name='dummy_calib.py', iter_step=None, iteration=None, ini=None, node_group=None,
                         priority=None)

        unknownArgs = ['--HPC']  # will require COMPS login
        manager, calib_args = get_calib_manager(args, unknownArgs, force_metadata=False)  # True only for resume
        self.assertEqual(manager.setup.selected_block, 'HPC')

    def test_selected_block_white_box(self):
        args = Namespace(config_name='dummy_calib.py', iter_step=None, iteration=None, ini=None, node_group=None,
                         priority=None)

        unknownArgs = []
        manager, calib_args = get_calib_manager(args, unknownArgs, force_metadata=False)  # True only for resume
        self.assertEqual(manager.setup.selected_block, 'LOCAL')

        unknownArgs = ['--LOCAL']
        manager, calib_args = get_calib_manager(args, unknownArgs, force_metadata=False)  # True only for resume
        self.assertEqual(manager.setup.selected_block, 'LOCAL')

        unknownArgs = ['--AZU']
        manager, calib_args = get_calib_manager(args, unknownArgs, force_metadata=False)  # True only for resume
        self.assertEqual(manager.setup.selected_block, 'LOCAL')

    def test_selected_block_resume_white_box(self):
        # Make sure we have calibration before resume
        self.exec_calib(['calibtool', 'run', 'dummy_calib.py'])

        args = Namespace(config_name='dummy_calib.py', iter_step=None, iteration=1, ini=None, node_group=None,
                         priority=None)

        # Case: take location from iteration 1
        unknownArgs = []
        manager, calib_args = get_calib_manager(args, unknownArgs, force_metadata=True)  # True only for resume
        self.assertEqual(manager.setup.selected_block, 'LOCAL')

        # Case: use location passed in
        unknownArgs = ['LOCAL']
        manager, calib_args = get_calib_manager(args, unknownArgs, force_metadata=True)  # True only for resume
        self.assertEqual(manager.setup.selected_block, 'LOCAL')

        # Case: take default (LOCAL) for unknown location
        unknownArgs = ['AZU']
        manager, calib_args = get_calib_manager(args, unknownArgs, force_metadata=True)  # True only for resume
        self.assertEqual(manager.setup.selected_block, 'LOCAL')


    def test_reanalyze(self):
        ctool = Popen(['calibtool', 'run', 'dummy_calib.py'], stdout=PIPE, stderr=STDOUT)
        ctool.communicate()

        # Open the CalibManager.json and save the values
        with open('test_dummy_calibration/CalibManager.json', 'r') as fp:
            cm = json.load(fp)
            self.totals = cm['results']['total']

        # Now reanalyze
        ctool = Popen(['calibtool', 'reanalyze', 'dummy_calib.py'], stdout=PIPE, stderr=STDOUT)
        ctool.communicate()

        # After reanalyze compare the totals
        with open('test_dummy_calibration/CalibManager.json', 'r') as fp:
            cm = json.load(fp)
            for i in range(len(self.totals)):
                self.assertAlmostEqual(cm['results']['total'][i], self.totals[i])

    def test_cleanup(self):
        ctool = Popen(['calibtool', 'run', 'dummy_calib.py'], stdout=PIPE, stderr=STDOUT)
        ctool.communicate()

        # Get the sim paths
        simulation_dir = os.path.join(self.current_cwd, 'calibration', 'simulations')
        simulation_files = glob.glob(simulation_dir+'/*.json')
        simulation_paths = []

        for sfile in simulation_files:
            try:
                info = json.load(open(os.path.join(simulation_dir, sfile), 'rb'))
                simulation_paths.append(os.path.join(info['sim_root'], "%s_%s" % (info['exp_name'], info['exp_id'])))
            except ValueError: # JSON cannot be decoded, just move on
                continue

        # Cleanup
        ctool = Popen(['calibtool', 'cleanup', 'dummy_calib.py'], stdout=PIPE, stderr=STDOUT)
        ctool.communicate()

        # Make sure everything disappeared
        self.assertFalse(os.path.exists('test_dummy_calibration'))
        self.assertEqual(glob.glob('simulations/*.json'), [])
        for path in simulation_paths:
            self.assertFalse(os.path.exists(path))


class TestMultiVariatePrior(unittest.TestCase):

    def test_sample_range(self):
        linear_range = SampleRange('linear', 0.4, 0.7)
        log_range = SampleRange('log', 0.4, 0.7)
        linearint_range = SampleRange('linear_int', 1, 6)

        self.assertRaises(lambda: SampleRange('linear', 0.4, 0.1))  # bad: min > max
        self.assertRaises(lambda: SampleRange('log', -0.4, 0.1))  # bad: log(negative)

    def test_container_sampling(self):
        container = SampleFunctionContainer(uniform(loc=-5, scale=10))
        equal_spaced = container.get_even_spaced_samples(11)
        np.testing.assert_almost_equal(equal_spaced, np.arange(-5, 6), decimal=2)

    def test_discrete_pdf(self):
        container_continuous = SampleFunctionContainer.from_tuple('linear', 1, 6)
        continuous_pdfs = container_continuous.pdf([3.2, 0.6, -3, 6.1, 7])
        np.testing.assert_equal(continuous_pdfs, [0.2, 0, 0, 0, 0])

        container_discrete = SampleFunctionContainer.from_tuple('linear_int', 1, 5)
        discrete_pdfs = container_discrete.pdf([3.2, 0.6, -3, 5.1, 7])
        np.testing.assert_equal(discrete_pdfs, [0.2, 0.2, 0, 0.2, 0])

        container_wo_range = SampleFunctionContainer(container_discrete.function)
        rangeless_pdfs = container_wo_range.pdf([3.2, 0.6, -3, 5.1, 7])
        np.testing.assert_equal(rangeless_pdfs, [0.2, 0, 0, 0.2, 0.2])

    def test_two_normals(self):
        two_normals = MultiVariatePrior(name='two_normals',
                                        functions=((norm(loc=0, scale=1)), (norm(loc=-10, scale=1))))

        xx = two_normals.rvs(size=1000)
        np.testing.assert_almost_equal(xx.mean(axis=0), np.array([0, -10]), decimal=1)
        np.testing.assert_almost_equal(xx.std(axis=0), np.array([1, 1]), decimal=1)

        xx = two_normals.rvs(size=1)
        self.assertEqual(xx.shape, (2,))

        self.assertEqual(two_normals.params, range(2))

    def test_normal_by_uniform(self):
        normal_by_uniform = MultiVariatePrior(name='normal_by_uniform',
                                              functions=((norm(loc=0, scale=1)), (uniform(loc=-10, scale=5))))

        xx = normal_by_uniform.rvs(size=1000)
        np.testing.assert_almost_equal(xx.mean(axis=0), np.array([0, -7.5]), decimal=1)
        np.testing.assert_almost_equal(xx.std(axis=0), np.array([1, 5 / np.sqrt(12)]), decimal=1)

    def test_uniform_pdf(self):
        uniform_prior = MultiVariatePrior.by_param(a=uniform(loc=0, scale=2))
        test = np.array([-1, 0, 1, 1.5, 2, 2.5])
        output = uniform_prior.pdf(test).tolist()
        self.assertListEqual(output, [0, 0.5, 0.5, 0.5, 0.5, 0])

    def test_two_uniform_pdf(self):
        uniform_prior = MultiVariatePrior.by_param(a=uniform(loc=0, scale=2),
                                                   b=uniform(loc=0, scale=2))
        test = np.array([[-1, 0], [0, 1], [1.5, 2], [-1, 2.5]])
        output = uniform_prior.pdf(test).tolist()
        self.assertListEqual(output, [0, 0.25, 0.25, 0])

    def test_ranges(self):
        prior = MultiVariatePrior.by_range(
            MSP1_Merozoite_Kill_Fraction=('linear', 0.4, 0.7),
            Max_Individual_Infections=('linear_int', 3, 8),
            Base_Gametocyte_Production_Rate=('log', 0.001, 0.5))

        df_rvs = prior.to_dataframe(prior.rvs(1000))
        df_rvs['Log10_Base_Gametocyte_Production_Rate'] = np.log10(df_rvs.Base_Gametocyte_Production_Rate)

        df_lhs = prior.to_dataframe(prior.lhs(1000))
        df_lhs['Log10_Base_Gametocyte_Production_Rate'] = np.log10(df_lhs.Base_Gametocyte_Production_Rate)

        np.testing.assert_almost_equal(df_rvs[['MSP1_Merozoite_Kill_Fraction',
                                               'Max_Individual_Infections',
                                               'Log10_Base_Gametocyte_Production_Rate']].mean(axis=0),
                                       np.array([0.55, 5.5, -1.65]), decimal=1)

        np.testing.assert_almost_equal(df_lhs[['MSP1_Merozoite_Kill_Fraction',
                                               'Max_Individual_Infections',
                                               'Log10_Base_Gametocyte_Production_Rate']].mean(axis=0),
                                       np.array([0.55, 5.5, -1.65]), decimal=1)

    def test_ranges_pdf(self):
        prior = MultiVariatePrior.by_range(
            MSP1_Merozoite_Kill_Fraction=('linear', 0.4, 0.7),
            Max_Individual_Infections=('linear_int', 3, 8),
            Base_Gametocyte_Production_Rate=('log', 0.001, 0.5))

        test_ok = np.array([[0.5, 6, 0.3], [0, 1, 0.9], [1.5, 2, 12.5], [-1, 2.5, 63]])
        test_list = [[-1, 0, 0.3], [0, 1, 0.9], [1.5, 2, 12.5], [-1, 3, 63]]
        prior.pdf(test_ok)
        prior.pdf(test_list)

        # Forgiving of 1-d input
        test_point_list = [1, 2, 3]
        test_point_array = np.array([1, 2, 3])
        prior.pdf(test_point_list)
        prior.pdf(test_point_array)

        transformed = prior.to_dict([2.5, 3.2, 0.4])
        self.assertTrue(isinstance(transformed['Max_Individual_Infections'], int))

        test_wrong_shape = np.array([[-1, 0], [0, 1], [1.5, 2], [-1, 2.5]])
        test_empty = []
        self.assertRaises(lambda: prior.pdf(test_wrong_shape))  # bad: wrong shape
        self.assertRaises(lambda: prior.pdf(test_empty))  # bad: empty array


class NextPointTestWrapper(object):
    """
    A simple wrapper for running iterative loops without all the CalibManager overhead.
    """

    def __init__(self, algo, likelihood_fn):
        self.algo = algo
        self.likelihood_fn = likelihood_fn

    def run(self, max_iterations=100):
        for iteration in range(max_iterations):
            next_samples = self.algo.get_next_samples()
            next_likelihoods = self.likelihood_fn(next_samples)
            self.algo.update_results(next_likelihoods)
            self.algo.update_state(iteration)
            if self.algo.end_condition():
                break
        return self.algo.get_final_samples()

    def save_figure(self, fig, name):
        try:
            os.makedirs('tmp')
        except:
            pass  # directory already exists
        fig.savefig(os.path.join('tmp', '%s.png' % name))


class TestIMIS(unittest.TestCase):
    def test_multivariate(self):
        likelihood_fn = lambda x: multivariate_normal(mean=[1, 1], cov=[[1, 0.6], [0.6, 1]]).pdf(x)
        prior_fn = multivariate_normal(mean=[0, 0], cov=3 * np.identity(2))

        x, y = np.mgrid[-5:5:0.01, -5:5:0.01]
        pos = np.empty(x.shape + (2,))
        pos[:, :, 0] = x
        pos[:, :, 1] = y
        true_posterior = likelihood_fn(pos) * prior_fn.pdf(pos)

        imis = IMIS(prior_fn, initial_samples=5000, samples_per_iteration=500)
        tester = NextPointTestWrapper(imis, likelihood_fn)
        resample = tester.run()

        fig_name = 'test_multivariate'
        fig, (ax1, ax2) = plt.subplots(1, 2, num=fig_name, figsize=(11, 5))
        ax1.hist(imis.weights, bins=50, alpha=0.3)
        ax1.hist(resample['weights'], bins=50, alpha=0.3, color='firebrick')
        ax1.set_title('Weights')
        ax2.hexbin(*zip(*resample['samples']), gridsize=50, cmap='Blues', mincnt=0.01)
        ax2.contour(x, y, true_posterior, cmap='Reds')
        ax2.set(xlim=[-2, 3], ylim=[-2, 3], title='Resamples')
        fig.set_tight_layout(True)
        tester.save_figure(fig, fig_name)

    def test_univariate(self):
        likelihood_fn = lambda xx: 2 * np.exp(-np.sin(3 * xx) * np.sin(xx ** 2) - 0.1 * xx ** 2)
        prior_fn = multivariate_normal(mean=[0], cov=[5 ** 2])

        xx = np.arange(-5, 5, 0.01)
        true_posterior = np.multiply(likelihood_fn(xx), prior_fn.pdf(xx))

        imis = IMIS(prior_fn, initial_samples=5000, samples_per_iteration=500)
        tester = NextPointTestWrapper(imis, likelihood_fn)
        resample = tester.run()

        fig_name = 'test_univariate'
        fig = plt.figure(fig_name, figsize=(10, 5))
        plt.plot(xx, prior_fn.pdf(xx), 'navy', label='Prior')
        plt.plot(xx, true_posterior, 'r', label='Posterior')
        plt.hist(resample['samples'], bins=100, alpha=0.3, label='Resamples', normed=True)
        plt.xlim([-5, 5])
        plt.legend()
        fig.set_tight_layout(True)
        tester.save_figure(fig, fig_name)


class TestIterationState(unittest.TestCase):
    init_state = dict(parameters={}, next_point={}, simulations={},
                      analyzers={}, results=[], iteration=0, experiment_id=None, resume_point=0)

    def setUp(self):
        # self.state = IterationState()
        self.input_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'input')

    def example_settings(self):
        self.state.parameters = dict(values=[[0, 1], [2, 3], [4, 5]], names=['p1', 'p2'])
        prior = MultiVariatePrior.by_param(a=uniform(loc=0, scale=2))
        self.state.next_point = IMIS(prior).get_state()
        self.state.simulations = {
            'sims': {'id1': {'p1': 1, 'p2': 2},
                     'id2': {'p1': 3, 'p2': 4}}}
        self.state.analyzers = {'a1': [{'x': [1, 2], 'y': [3, 4]},
                                       {'x': [1, 2], 'y': [5, 6]}]}
        self.state.results = [{'a1': -13, 'total': -13},
                              {'a1': -11, 'total': -11}]

    def test_init(self):
        self.assertDictEqual(self.state.__dict__,
                             self.init_state)


    def test_serialization(self):
        self.example_settings()
        self.state.to_file('tmp.json')
        new_state = IterationState.from_file('tmp.json')
        old_state = copy.deepcopy(self.state)
        next_point_new = new_state.__dict__.pop('next_point')
        next_point_old = old_state.__dict__.pop('next_point')
        self.assertDictEqual(new_state.__dict__, old_state.__dict__)
        np.testing.assert_array_equal(next_point_new['latest_samples'],
                                      next_point_old['latest_samples'])
        os.remove('tmp.json')

    def test_get_parameter_sets_with_likelihoods(self):
        # load up our sample IterationState object
        iteration_directory = os.path.join(self.input_path, 'sample_iteration', 'iter2')
        iteration_json = os.path.join(iteration_directory, 'IterationState.json')
        iteration_state = IterationState.from_file(filepath=iteration_json)

        # get ParameterSet objects
        parameter_sets = iteration_state.get_parameter_sets_with_likelihoods()

        # verify that the obtained info is correct
        sample_parameter_set = [ps for ps in parameter_sets if ps.sim_id == '48e32ba8-5618-e911-a2bd-c4346bcb1555'][0]
        expected_parameter_dict = {
            'Base Infectivity': 0.0004387700180648397,
            'Circumcision Reduced Acquire': 0.6,
            'Sexual Debut Age Female Weibull Scale': 16.68597913701478,
            'Sexual Debut Age Female Weibull Heterogeneity': 0.05371882934122224,
            'Sexual Debut Age Male Weibull Scale': 15.550981690258908,
            'Sexual Debut Age Male Weibull Heterogeneity': 0.042083429572395026,
            'Male To Female Young': 1.2264968386594102,
            'Male To Female Old': 2.953121144250777,
            'Risk Assortivity': 0.5667730313054367,
            'Homa_Bay: LOW Risk': 0.6980632670179557,
            'Kisii: LOW Risk': 0.910059663153128,
            'Kisumu: LOW Risk': 0.7655090954659004,
            'Migori: LOW Risk': 0.9271959619763279,
            'Nyamira: LOW Risk': 0.9312071932371089,
            'Siaya: LOW Risk': 0.693635538851748
        }

        self.assertEqual(len(parameter_sets), 90)  # 30 parameter sets, 3 replicates
        self.assertEqual(sample_parameter_set.iteration_number, 2)
        self.assertEqual(sample_parameter_set.run_number, 54624)
        self.assertEqual(sample_parameter_set.likelihood, -504.03496646688296)
        self.assertEqual(sample_parameter_set.sim_id, '48e32ba8-5618-e911-a2bd-c4346bcb1555')
        self.assertEqual(sample_parameter_set.param_dict, expected_parameter_dict)



class TestNumpyDecoder(unittest.TestCase):
    """
    This was discovered in caching CalibAnalyzer array with np.int64
    age_bins, which is not well handled by the utils.NumpyEncoder class.
    """

    def tearDown(self):
        os.remove('int32.json')

    def test_int32_conversion(self, asint32=True):
        df = pd.DataFrame({'x': [1, 2], 'y': [2.8, 4.2]})
        if asint32:
            df.x = df.x.astype(int)  # now np.int64 is np.int32
        a = {'ana': [df.to_dict(orient='list')]}
        state = IterationState(analyzers=a)
        state.to_file('int32.json')

    def test_int64_exception(self):
        with self.assertRaises(RuntimeError) as err:
            self.test_int32_conversion(False)


class TestCalibManager(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()
