"""
Maybe add xlsx reading, from a defined, similar format to csv

Currently, all files read via .from_directory() are merged into ONE dataframe.
"""

import os
import pandas as pd

from dtk.utils.observations.Condition import Condition
from simtools.Utilities.General import caller_name


class DataFrameWrapper:

    class UnsupportedFileType(Exception): pass
    class MissingRequiredData(Exception): pass
    class InconsistentStratification(Exception): pass

    CSV = 'csv'

    def __init__(self, filename=None, dataframe=None, stratifiers=None):
        stratifiers = stratifiers or []
        if not ((filename is None) ^ (dataframe is None)):
            raise ValueError('filename or dataframe must be provided')
        if dataframe is not None:
            self._dataframe = dataframe.copy()
        else:
            _, file_type = os.path.splitext(filename)
            file_type = file_type.replace('.', '')
            if file_type == self.CSV:
                self._dataframe = pd.read_csv(filename)
            else:
                raise self.UnsupportedFileType('Unsupported file type for reading: %s' % file_type)
        self._dataframe.reset_index(drop=True, inplace=True)

        # use provided stratifier list
        if not isinstance(stratifiers, list):
            stratifiers = [stratifiers]
        missing_stratifiers = [s for s in stratifiers if s not in self._dataframe.columns]
        if len(missing_stratifiers) > 0:
            raise self.MissingRequiredData('Specified stratifier(s): %s not in dataframe.' % missing_stratifiers)

        self.stratifiers = sorted(set(stratifiers))
        self.data_channels = sorted(set(self._dataframe.columns) - set(self.stratifiers))

    @property
    def channels(self):
        """
        Channels are non-stratifier columns
        :return:
        """
        return sorted(list(set(self._dataframe.columns) - set(self.stratifiers)))

    def filter(self, conditions=None, keep_only=None):
        """
        Selects rows from the internal dataframe that satisfy all provided conditions. The stratifiers
        of the result will exclude current-object stratifiers that contain NaN in the resulting rows.

        :param conditions: an iterator (e.g. list) of tuples/triplets specifying (in order) stratifier, operator, value.
                e.g. ['min_age', operator.ge, 25] (to select rows where 'min_age' is >= 25)
        :param keep_only: If not None, then is a list of data channels to keep (in addition to stratifiers)
                after filtering. Rows with any NaN values will be dropped after trimming to these channels.
        
        :return: an object of the same type as the object this method is called on with only selected rows remaining.
        """
        # conditions: e.g. [ ['min_age', operator.ge, 20]  ]
        if not conditions:
            conditions = []
        conditions = [Condition(*condition) for condition in conditions]

        filtered_df = self._dataframe
        for condition in conditions:
            filtered_df = filtered_df.loc[condition.apply(filtered_df)]

        if keep_only:
            if not isinstance(keep_only, list):
                keep_only = [keep_only]
            kept_channels = list(set(self.stratifiers + keep_only))
            kept_non_stratifiers = list(set(kept_channels) - set(self.stratifiers))
            self.verify_required_items(needed=kept_channels)
            filtered_df = filtered_df[kept_channels].dropna(subset=kept_non_stratifiers)

        # detect and drop any NaN-containing (extraneous) columns/stratifiers now that NaN containing
        # rows have been removed
        filtered_df = filtered_df.dropna(axis='columns')
        trimmed_stratifiers = set(self.stratifiers) - set(filtered_df.columns)
        stratifiers_remaining = list(set(self.stratifiers) - trimmed_stratifiers)

        return type(self)(dataframe=filtered_df, stratifiers=stratifiers_remaining)

    def merge(self, other_dfw, index, keep_only=None):
        """
        Attempts to merge two DataFrameWrapper objects into one using the provided index list as a multi-index.
        
        :param other_dfw: the DataFrameWrapper object to merge with.
        :param index: a list of columns to merge on. All are required in both DataFrameWrapper objects.
        :param keep_only: a list of columns. Triggers removal of result rows where NaN appears in any of these specified
            columns. Result will contain these columns AND those from provided index.
        
        :return: A newly created, merged object of the exact type of self and the stratifiers equal to the provided
            index.
        """
        if not isinstance(other_dfw, DataFrameWrapper):
            raise Exception('Can only merge DataFrameWrapper objects, not: %s' % type(other_dfw))

        # we technically need the 'keep_only' items, too, but that is more complicated due to the merge
        self.verify_required_items(needed=index)
        other_dfw.verify_required_items(needed=index)
        
        this_df = self._dataframe.set_index(index)
        other_df = other_dfw._dataframe.set_index(index)
        merged_df = pd.merge(this_df, other_df, left_index=True, right_index=True)
        merged_df.reset_index(inplace=True)
        return type(self)(dataframe=merged_df, stratifiers=index).filter(keep_only=keep_only)

    def verify_required_items(self, needed, available=None):
        """
        Standard method for checking if necessary items/channels are available and printing a meaningful error if not
        :param needed: channels to look for
        :param available: channel list to look in
        :return: Nothing
        """
        if available is None:
            available = self._dataframe.columns

        missing_items = [item for item in needed if item not in available]
        if len(missing_items) > 0:
            raise self.MissingRequiredData('Missing required item(s): %s for operation: %s' %
                                           (missing_items, caller_name(skip=3)))

    def equals(self, other_dfw):
        equal_dataframe = self._dataframe.equals(other_dfw._dataframe)
        equal_stratifiers = sorted(self.stratifiers) == sorted(other_dfw.stratifiers)
        return equal_dataframe and equal_stratifiers

    def __str__(self):
        return str(self._dataframe)

    @classmethod
    def from_directory(cls, directory, file_type=None, stratifiers=None):
        import glob
        import os

        if not file_type:
            file_type = cls.CSV

        if stratifiers and not isinstance(stratifiers, list):
            stratifiers = [stratifiers]
        provided_stratifiers = stratifiers

        obs_filenames = glob.glob(os.path.join(directory, '*.%s' % file_type))
        individual_objects = [cls(filename=obs_filename) for obs_filename in obs_filenames]
        combined_df = pd.DataFrame([])
        stratifiers = set()
        for obj in individual_objects:
            combined_df = combined_df.append(obj._dataframe, sort=True)
            stratifiers = stratifiers.union(obj.stratifiers)
            # stratifiers = stratifiers or obj.stratifiers
            # if set(obj.stratifiers) != set(stratifiers):
            #     raise cls.InconsistentStratification('All files of type: %s in directory: %s must have identical '
            #                                          'stratifiers specified.\n%s\nvs.\n%s' % (file_type, directory, obj.stratifiers, stratifiers))

        stratifiers = provided_stratifiers if provided_stratifiers else stratifiers
        new_obj = cls(dataframe=combined_df, stratifiers=list(stratifiers))
        return new_obj
