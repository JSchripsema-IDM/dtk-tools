import os
import pandas as pd
import unittest

from dtk.utils.observations.AgeBin import AgeBin
from dtk.utils.observations.PopulationObs import PopulationObs
import dtk.utils.observations.utils as ingest_utils


class TestCalibrationIngest(unittest.TestCase):
    def setUp(self):
        self.data_directory = os.path.join(os.path.dirname(__file__), 'input', 'Excel', 'ingest')
        self.result = False

    def tearDown(self):
        if self.result:
            print(f"{self._testMethodName}: passed.\n")
        else:
            print(f"{self._testMethodName}: failed.\n")

    # parameter parsing

    def test_fail_if_parameters_have_missing_values(self):
        filenames = ['missing_parameter_values_dynamic.xlsm', 'missing_parameter_values_name.xlsm']
        for filename in filenames:
            filename = os.path.join(self.data_directory, filename)
            self.assertRaises(ingest_utils.IncompleteParameterSpecification,
                              ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    def test_fail_if_parameter_initial_beyond_min_max(self):
        filenames = ['parameter_below_min.xlsm', 'parameter_above_max.xlsm']
        for filename in filenames:
            filename = os.path.join(self.data_directory, filename)
            self.assertRaises(ingest_utils.ParameterOutOfRange,
                              ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    def test_fail_if_parameter_has_non_numeric_value(self):
        filenames = ['parameter_has_non_numeric_value.xlsm']
        for filename in filenames:
            filename = os.path.join(self.data_directory, filename)
            self.assertRaises(ingest_utils.ParameterOutOfRange,
                              ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    # analyzer parsing

    def test_fail_if_analyzers_have_missing_values(self):
        filenames = ['missing_analyzer_values_age_bins.xlsm',
                     'missing_analyzer_values_channel.xlsm',
                     'missing_analyzer_values_custom_age_bins.xlsm',
                     'missing_analyzer_values_distribution.xlsm',
                     'missing_analyzer_values_weight.xlsm'
                     ]
        for filename in filenames:
            filename = os.path.join(self.data_directory, filename)
            self.assertRaises(ingest_utils.IncompleteAnalyzerSpecification,
                              ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    def test_fail_if_analyzer_weight_is_non_numeric(self):
        filenames = ['analzyer_weight_has_non_numeric_value.xlsm']
        for filename in filenames:
            filename = os.path.join(self.data_directory, filename)
            self.assertRaises(ingest_utils.InvalidAnalyzerWeight,
                              ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    # reference data parsing

    def test_fail_if_reference_data_has_missing_values(self):
        filename = os.path.join(self.data_directory, 'missing_reference_values.xlsm')
        self.assertRaises(ingest_utils.IncompleteDataSpecification,
                          ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    # other

    def test_fail_if_not_parsing_an_xlsm_file(self):
        filename = os.path.join(self.data_directory, 'not_a_xlsm_file.csv')
        self.assertRaises(ingest_utils.UnsupportedFileFormat,
                          ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    # ck4, update this test with the latest ingest form
    def test_a_properly_filled_xlsm_sheet(self):
        from dtk.utils.observations.BetaDistribution import BetaDistribution

        filename = os.path.join(self.data_directory, 'properly_filled.xlsm')
        params, site_info, reference, analyzers, channels = ingest_utils.parse_ingest_data_from_xlsm(filename=filename)

        # check site info
        expected = {
            'site_name': 'Chile',
            'census_population': 17574003,
            'census_year': 2017,
            'census_age_bin': AgeBin(start=0, end=100),
            'node_map': {
                1: 'Atacama',
                2: 'Antofagasta',
                3: 'Coquimbo'
            }
        }

        self.assertTrue(isinstance(site_info, dict))
        self.assertEqual(site_info, expected)

        # check analyzers
        expected = [
            {
                'channel': 'Prevalence',
                'distribution': 'Beta',
                'provinciality': 'Provincial',
                'weight': 0.5,
                'age_bins': AgeBin.ALL,
                'scale_population': False
            },
            {
                'channel': 'Prevalence',
                'distribution': 'Beta',
                'provinciality': 'Non-provincial',
                'weight': 0.25,
                'age_bins': ['[15:50);[50:100)'],
                'scale_population': False
            },
            {
                'channel': 'Prevalence',
                'distribution': 'Beta',
                'provinciality': 'Non-provincial',
                'weight': 0.25,
                'age_bins': AgeBin.ALL,
                'scale_population': False
            }
            ]

        self.assertTrue(isinstance(analyzers, list))
        self.assertEqual(len(analyzers), len(expected))
        self.assertEqual(analyzers, expected)

        # check params
        expected = [
            {
                'Name': 'p2',
                'Dynamic': False,
                'Guess': 2000,
                'Min': 1200,
                'Max': 2400

            },
            {
                'Name': 'p1',
                'Dynamic': True,
                'Guess': 0.1,
                'Min': 0,
                'Max': 1,
                'MapTo': 'p1'

            },
        ]
        self.assertTrue(isinstance(params, list))
        self.assertEqual(len(params), len(expected))
        sorting_lambda = lambda x: x['Name']
        self.assertEqual(sorted(params, key=sorting_lambda), sorted(expected, key=sorting_lambda))

        # check reference

        self.assertTrue(isinstance(reference, PopulationObs))

        expected_stratifiers = ['Year', 'Gender', 'AgeBin', 'Province']
        self.assertEqual(sorted(reference.stratifiers), sorted(expected_stratifiers))

        # non-stratifier columns in the dataframe
        expected_channels = [PopulationObs.WEIGHT_CHANNEL, BetaDistribution.COUNT_CHANNEL, 'Prevalence']
        self.assertEqual(sorted(reference.channels), sorted(expected_channels))

        n_expected_rows = 4
        self.assertEqual(len(reference._dataframe.index), n_expected_rows)

        # data check
        data = [
            {'Year': 2005, 'Gender': 'Male', 'AgeBin': '[0:99)', 'Province': 'Washington', 'Prevalence': 0.25,
             PopulationObs.WEIGHT_CHANNEL: 2, BetaDistribution.COUNT_CHANNEL: 1},
            {'Year': 2005, 'Gender': 'Female', 'AgeBin': '[0:99)', 'Province': 'Washington', 'Prevalence': 0.2,
             PopulationObs.WEIGHT_CHANNEL: 4.4, BetaDistribution.COUNT_CHANNEL: 3},
            {'Year': 2010, 'Gender': 'Male', 'AgeBin': '[5:15)', 'Province': 'Washington', 'Prevalence': 0.3,
             PopulationObs.WEIGHT_CHANNEL: 1, BetaDistribution.COUNT_CHANNEL: 6},
            {'Year': 2010, 'Gender': 'Female', 'AgeBin': '[15:25)', 'Province': 'Oregon', 'Prevalence': 0.33,
             PopulationObs.WEIGHT_CHANNEL: 1, BetaDistribution.COUNT_CHANNEL: 7},
        ]
        df = pd.DataFrame(data)
        expected_reference = PopulationObs(dataframe=df, stratifiers=expected_stratifiers)
        reference, expected_reference = self.ensure_same_column_order(reference, expected_reference)
        self.assertTrue(reference.equals(expected_reference))
        self.result = True

    def ensure_same_column_order(self, dfw1, dfw2):
        self.assertEqual(sorted(dfw1._dataframe.columns), sorted(dfw2._dataframe.columns))
        reordered_columns = sorted(dfw1._dataframe.columns)
        dfw1._dataframe = dfw1._dataframe[reordered_columns]
        dfw2._dataframe = dfw2._dataframe[reordered_columns]
        return dfw1, dfw2

    # observational data - weight value parsing - HIV issue 62

    def test_fail_if_obs_data_missing_weight_column(self):
        filename = os.path.join(self.data_directory, 'obs_data_missing_weight_column.xlsm')
        self.assertRaises(ingest_utils.IncompleteDataSpecification,
                          ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    def test_obs_data_specified_and_default_weights_are_correctly_parsed(self):
        filename = os.path.join(self.data_directory, 'obs_data_correct_and_default_weight_column_values.xlsm')
        params, site_info, reference, analyzers, channels = ingest_utils.parse_ingest_data_from_xlsm(filename=filename)

        # now check reference data for correctness of obs weights
        expected = {
            'Prevalence': [1, 1, 2.2],
            'Incidence': [0.2, 1, 3]
        }
        for channel, expected_vals in expected.items():
            # considering data from sheets individually
            ref = reference.filter(keep_only=[channel, PopulationObs.WEIGHT_CHANNEL])
            actual = ref._dataframe[PopulationObs.WEIGHT_CHANNEL]
            self.assertTrue((actual == expected_vals).all())
        self.result = True

    # site info parsing - HIV issue 63

    def test_site_info_invalid_node_number(self):
        filename = os.path.join(self.data_directory, 'site_info_invalid_node_number.xlsm')
        self.assertRaises(ingest_utils.SiteNodeMappingException,
                          ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    def test_site_info_missing_node_number(self):
        filename = os.path.join(self.data_directory, 'site_info_missing_node_number.xlsm')
        self.assertRaises(ingest_utils.SiteNodeMappingException,
                          ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    def test_site_info_missing_node_name(self):
        filename = os.path.join(self.data_directory, 'site_info_missing_node_name.xlsm')
        self.assertRaises(ingest_utils.SiteNodeMappingException,
                          ingest_utils.parse_ingest_data_from_xlsm, filename=filename)
        self.result = True

    def test_site_info_valid_data_parsed(self):
        filename = os.path.join(self.data_directory, 'site_info_valid_data.xlsm')
        params, site_info, reference, analyzers, channels = ingest_utils.parse_ingest_data_from_xlsm(filename=filename)

        expected = {
            'site_name': 'Chile',
            'census_year': 2017,
            'census_population': 17574003,
            'census_age_bin': AgeBin(start=0, end=100),
            'node_map': {1: 'Atacama', 2: 'Antofagasta', 3: 'Coquimbo'}
        }
        for k, expected_value in expected.items():
            self.assertEqual(site_info[k], expected_value)
        self.result = True

    def test_missing_tuples(self):
        filename = os.path.join(self.data_directory, 'obs_data_correct_and_default_weight_column_values.xlsm')
        _, _, reference, _, _ = ingest_utils.parse_ingest_data_from_xlsm(filename=filename)
        self.assertFalse(reference.find_missing_tuples(reference, value_column_base="Prevalence"))

        filename = os.path.join(self.data_directory, 'obs_data_correct_and_default_weight_column_values.xlsm')
        _, _, reference, _, _ = ingest_utils.parse_ingest_data_from_xlsm(filename=filename)

        filename = os.path.join(self.data_directory, 'obs_data_missing_rows_and_default_weight_column_values.xlsm')
        _, _, reference_missing, _, _ = ingest_utils.parse_ingest_data_from_xlsm(filename=filename)

        self.assertEqual(len(reference.find_missing_tuples(reference_missing, value_column_base="Incidence")), 1)
        self.assertEqual(len(reference.find_missing_tuples(reference_missing, value_column_base="Prevalence")), 2)



if __name__ == '__main__':
    unittest.main()
