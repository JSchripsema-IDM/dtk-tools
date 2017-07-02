import unittest
import argparse
import json
import os.path as path
import os
import dtk.tools.serialization.combine_inset_charts as cmb

PLAIN_CHART = "InsetChart.json"
START_CHART = "InsetChart_start.json"
END_CHART = "InsetChart_end.json"
FULL_CHART = "InsetChart_full.json"
COMBINED_CHART = "combined_insetchart.json"

SERIALIZED_FOLDER = "serialized_output"
RELOADED_FOLDER = "reloaded_output"

class CombineInsetChartTests(unittest.TestCase):
    def setUp(self):
        local_parser = argparse.ArgumentParser()
        self.parser = cmb.define_arguments(local_parser)
        self.flags = []
        self.expected_new_files = []
        pass

    def tearDown(self):
        self.flags = []
        for potential_file in self.expected_new_files:
            if path.isfile(potential_file):
                os.unlink(potential_file)

    def set_serialized_flags(self, from_folder=True):
        self.flags.append('-s')
        if from_folder:
            self.flags.append(SERIALIZED_FOLDER)
        else:
            self.flags.append('.')

    def set_reloaded_flags(self, from_folder=True):
        self.flags.append('-r')
        if from_folder:
            self.flags.append(RELOADED_FOLDER)
        else:
            self.flags.append('.')

    def set_default_chartname_flags(self, plain_names=False):
        self.flags.append('--serializedchartname')
        if plain_names:
            self.flags.append(PLAIN_CHART)
        else:
            self.flags.append(START_CHART)

        self.flags.append('--reloadedchartname')
        if plain_names:
            self.flags.append(PLAIN_CHART)
        else:
            self.flags.append(END_CHART)

    def set_output_filename(self, filename):
        self.flags.append('-o')
        self.flags.append(filename)

    def get_args(self):
        return self.parser.parse_args(self.flags)

    def verify_expected_files(self, expect_created=True):
        for potential_file in self.expected_new_files:
            self.assertEqual(expect_created, path.isfile(potential_file))

    def combine_charts_all_remote_output_tofull(self, custom_filename, plain_names=False):
        combined_path = path.join('.', custom_filename)
        self.expected_new_files.append(combined_path)
        self.verify_expected_files(False)
        self.set_output_filename(custom_filename)
        self.set_default_chartname_flags(plain_names)
        self.set_reloaded_flags(from_folder=True)
        self.set_serialized_flags(from_folder=True)
        return self.get_args()

    def combine_charts_all_local_default_output(self):
        combined_path = path.join('.', COMBINED_CHART)
        self.expected_new_files.append(combined_path)
        self.verify_expected_files(False)
        self.set_serialized_flags(from_folder=False)
        self.set_reloaded_flags(from_folder=False)
        self.set_default_chartname_flags()
        return self.get_args()

    def verify_charts_combined(self, start_chart, end_chart, combined_chart):
        start_keys = sorted(start_chart["Channels"].keys())
        combined_keys = sorted(combined_chart["Channels"].keys())
        self.assertEqual(len(start_keys), len(combined_keys))
        for key in start_keys:
            self.assertTrue(key in combined_keys)
        start_channel_length = len(start_chart["Channels"]["Infected"]["Data"])
        end_channel_length = len(end_chart["Channels"]["Infected"]["Data"])
        combined_channel_length = len(combined_chart["Channels"]["Infected"]["Data"])
        self.assertEqual(combined_channel_length, start_channel_length + end_channel_length)

    def test_args_AllLocalDefaultOutput(self):
        args = self.combine_charts_all_local_default_output()
        self.assertEquals(args.serialized, '.')
        self.assertEquals(args.reload, '.')
        self.assertEquals(args.output, COMBINED_CHART)

    def test_combination_AllLocalDefaultOutput(self):
        args = self.combine_charts_all_local_default_output()
        cmb.combine_charts(args.serialized,
                           args.reload,
                           args.output,
                           serialized_chart_name=args.serializedchartname,
                           reloaded_chart_name=args.reloadedchartname)
        self.verify_expected_files(True)
        with open(self.expected_new_files[0]) as infile:
            combined_chart = json.load(infile)
        start_chart_path = path.join(SERIALIZED_FOLDER, START_CHART)
        end_chart_path = path.join(RELOADED_FOLDER, END_CHART)
        with open(start_chart_path) as infile:
            start_chart = json.load(infile)
        with open(end_chart_path) as infile:
            end_chart = json.load(infile)
        self.verify_charts_combined(start_chart, end_chart, combined_chart)


    def test_args_AllFolderCustomOutput(self):
        custom_filename = "funny_insetchart.json"
        args = self.combine_charts_all_remote_output_tofull(custom_filename)
        self.assertEquals(args.serialized, SERIALIZED_FOLDER)
        self.assertEqual(args.reload, RELOADED_FOLDER)
        self.assertEqual(args.output, custom_filename)

    def test_args_AllFolderPlainNamesCustomOutput(self):
        custom_filename = "funny_insetchart.json"
        args = self.combine_charts_all_remote_output_tofull(custom_filename, plain_names=True)
        self.assertEquals(args.serialized, SERIALIZED_FOLDER)
        self.assertEqual(args.reload, RELOADED_FOLDER)
        self.assertEqual(args.output, custom_filename)

    def test_combination_AllFolderCustomOutput(self):
        custom_filename = "funny_insetchart.json"
        args = self.combine_charts_all_remote_output_tofull(custom_filename)
        cmb.combine_charts(args.serialized,
                           args.reload,
                           args.output,
                           serialized_chart_name=args.serializedchartname,
                           reloaded_chart_name=args.reloadedchartname)
        self.verify_expected_files(True)

        serialized_chartname = path.join(SERIALIZED_FOLDER, START_CHART)
        reloaded_chartname = path.join(RELOADED_FOLDER, END_CHART)
        with open(self.expected_new_files[0]) as infile:
            combined_chart = json.load(infile)
        with open(serialized_chartname) as infile:
            start_chart = json.load(infile)
        with open(reloaded_chartname) as infile:
            end_chart = json.load(infile)
        self.verify_charts_combined(start_chart, end_chart, combined_chart)





