import json
import logging
import os
import copy
import pandas as pd
from calibtool.utils import ResumePoint
from simtools.utils import NumpyEncoder, json_numpy_obj_hook

logger = logging.getLogger(__name__)


class IterationState(object):
    '''
    Holds the settings, parameters, simulation state, analysis results, etc.
    for one calibtool iteration.

    Allows for the resumption or extension of existing CalibManager instances
    from an arbitrary point in the iterative process.
    '''

    def __init__(self, **kwargs):
        self.iteration = 0
        self.resume_point = ResumePoint.iteration_start
        self.reset_state()
        for k, v in kwargs.items():
            setattr(self, k, v)

    def reset_state(self):
        self.samples_for_this_iteration = {}
        self.next_point = {}
        self.simulations = {}
        self.experiment_id = None
        self.analyzers = {}
        self.results = {}

    def reset_to_step(self, iter_step=None):
        last_state_by_step = [('commission', ('samples_for_this_iteration')),
                              ('analyze', ('simulations',)),
                              ('next_point', ('results', 'analyzers'))]

        for step, states in reversed(last_state_by_step):
            if step == iter_step:  # remove cached states back to desired resumption point
                break
            logger.info('Clearing IterationState attribute(s): %s', states)
            for state in states:
                attr = getattr(self, state)
                if isinstance(attr, list):
                    attr[:] = []  # clear() only for dict before Python 3.3
                else:
                    attr.clear()

    def increment_iteration(self):
        self.iteration += 1
        self.reset_state()

    @classmethod
    def from_file(cls, filepath):
        with open(filepath, 'r') as f:
            return cls(**json.load(f, object_hook=json_numpy_obj_hook))

    def to_file(self, filepath):
        # remove resume_point from output
        it_dict = copy.deepcopy(self.__dict__)
        it_dict.pop('resume_point')

        with open(filepath, 'w') as f:
            json.dump(it_dict, f, indent=4, cls=NumpyEncoder)

    def summary_table(self):
        '''
        Returns a summary table of the form:
          [result1 result2 results_total param1 param2 iteration simIds]
          index = sample
        '''

        results_df = pd.DataFrame.from_dict(self.results, orient='columns')
        results_df.index.name = 'sample'

        params_df = pd.DataFrame.from_dict(self.samples_for_this_iteration, orient='columns')

        for c in params_df.columns: # Argh
            params_df[c] = params_df[c].astype( self.samples_for_this_iteration_dtypes[c])

        sims_df = pd.DataFrame.from_dict(self.simulations, orient='index')
        grouped = sims_df.groupby('__sample_index__', sort=True)
        simIds = tuple(group.index.values for sample, group in grouped)

        df = pd.concat((results_df , params_df), axis=1)
        df['iteration'] = self.iteration

        return df

    @classmethod
    def restore_state(cls, exp_name, iteration):
        """
        Restore IterationState
        """
        iter_directory = os.path.join(exp_name, 'iter%d' % iteration)
        iter_file = os.path.join(iter_directory, 'IterationState.json')
        return cls.from_file(iter_file)
