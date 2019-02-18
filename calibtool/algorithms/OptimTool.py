import logging
import math

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

from scipy.special import gammaln  # for calculation of mu_r
from calibtool.algorithms.NextPointAlgorithm import NextPointAlgorithm

logging.basicConfig(format='%(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimTool(NextPointAlgorithm):
    """
    OptimTool

    The basic idea of OptimTool is
    """
    def __init__(self, params, constrain_sample_fn=lambda s: s, mu_r=0.1, sigma_r=0.02, center_repeats=2,
                 samples_per_iteration=1e2, rsquared_thresh=0.5):

        super(OptimTool, self).__init__()
        self.args = locals()  # Store inputs in case set_state is called later and we want to override with new (user) args
        del self.args['self']
        self.need_resolve = False

        self.constrain_sample_fn = constrain_sample_fn

        self.regression = pd.DataFrame(
            columns=['Iteration', 'Parameter', 'Value'])  # Parameters: Rsquared, Regression_Parameters
        self.regression['Iteration'] = self.regression['Iteration'].astype(int)

        self.state = pd.DataFrame(columns=['Iteration', 'Parameter', 'Center', 'Min', 'Max', 'Dynamic'])
        self.state['Iteration'] = self.state['Iteration'].astype(int)

        self.params = params  # TODO: Check min <= center <= max
        self.mu_r = mu_r
        self.sigma_r = sigma_r
        self.center_repeats = center_repeats
        self.rsquared_thresh = rsquared_thresh
        self.samples_per_iteration = int(samples_per_iteration)

        self.Xmin = {p['Name']: p['Min'] for p in self.params}
        self.Xmax = {p['Name']: p['Max'] for p in self.params}
        self.Dynamic = {p['Name']: p['Dynamic'] for p in self.params}

        self.n_dimensions = 0
        self.data = pd.DataFrame()

        self.verify_param()

    def cleanup(self):
        pass

    def verify_param(self):
        # Checking Dynamic
        if len([p for p in self.params if p['Dynamic']]) == 0:
            warning_note = \
                """
                /!\\ WARNING /!\\ the OptimTool requires at least one of params with Dynamic set to True. Exiting...                  
                """
            print(warning_note)
            exit()

    def resolve_args(self, iteration):
        # Have args from user and from set_state.
        # Note this is called only right before commissioning a new iteration, likely from 'resume'

        # TODO: be more sensitive with params, user could have added or removed variables, need to adjust
        # TODO: Check min <= center <= max for params
        # TODO: could clean this up with a helper function
        self.params = self.args['params'] if 'params' in self.args else self.params  # Guess may move, but should be ignored
        self.mu_r = self.args['mu_r'] if 'mu_r' in self.args else self.mu_r
        self.sigma_r = self.args['sigma_r'] if 'sigma_r' in self.args else self.sigma_r
        self.center_repeats = self.args['center_repeats'] if 'center_repeats' in self.args else self.center_repeats
        self.rsquared_thresh = self.args['rsquared_thresh'] if 'rsquared_thresh' in self.args else self.rsquared_thresh
        self.samples_per_iteration = self.args[
            'samples_per_iteration'] if 'samples_per_iteration' in self.args else self.samples_per_iteration

        self.n_dimensions = len(self.params)
        self.Xmin = {p['Name']: p['Min'] for p in self.params}
        self.Xmax = {p['Name']: p['Max'] for p in self.params}
        self.Dynamic = {p['Name']: p['Dynamic'] for p in self.params}

        self.need_resolve = False

        """
        # TODO: Allow user to override current 'Center' value
        state_by_iter = self.state.set_index('Iteration')
        if iteration == 0:
            # Not sure this would happen, but just in case
            cur_val = {p['Name']:p['Guess'] for p in self.params}
        else:
            cur_val = {s['Parameter']:s['Center'] for (i,s) in state_by_iter.loc[iteration-1].iterrows()}

        iter_state = pd.DataFrame(columns=['Iteration', 'Parameter', 'Center', 'Min', 'Max', 'Dynamic'])
        for param in self.params:
            iter_state.loc[len(iter_state)] = [iteration, param['Name'], cur_val[param['Name']], param['Min'], param['Max'], param['Dynamic']]

        self.state = self.state.loc[:iteration-1]
        self.state.reset_index(inplace=True)
        self.state = pd.concat([self.state, iter_state], ignore_index=True)
        self.state['Iteration'] = self.state['Iteration'].astype(int)

        with pd.option_context("display.max_rows", 500, "display.max_columns", 500):
            print(self.state)
            raw_input('resolve_args')
        """

    def _get_X_center(self, iteration):
        state_by_iter = self.state.reset_index(drop=True).set_index(['Iteration', 'Parameter'])
        # assert( iteration in state_by_iter.index.get_level_values('Iteration') )
        return state_by_iter.loc[iteration]['Center']

    def add_samples(self, samples, iteration):
        samples_cpy = samples.copy()
        samples_cpy.index.name = '__sample_index__'
        samples_cpy['Iteration'] = iteration
        samples_cpy.reset_index(inplace=True)

        self.data = pd.concat([self.data, samples_cpy], ignore_index=True)
        self.data['__sample_index__'] = self.data['__sample_index__'].astype(int)

    def get_samples_for_iteration(self, iteration):
        # Update args
        if self.need_resolve:
            self.resolve_args(iteration)

        if iteration == 0:
            # Choose initial samples
            samples = self.choose_initial_samples()
        else:
            # Regress inputs and results from previous iteration
            # Move X_center, choose hypersphere, save in dataframe
            samples = self.choose_samples_via_gradient_ascent(iteration)

        samples.reset_index(drop=True, inplace=True)
        return self.generate_samples_from_df(samples)

    def clamp(self, X):

        # print('X.before:\n', X)

        # X should be a data frame
        for pname in X.columns:
            X[pname] = np.minimum(self.Xmax[pname], np.maximum(self.Xmin[pname], X[pname]))

        return X

    def set_results_for_iteration(self, iteration, results):
        results = results.total.tolist()
        logger.info('%s: Choosing samples at iteration %d:', self.__class__.__name__, iteration)
        logger.debug('Results:\n%s', results)

        data_by_iter = self.data.set_index('Iteration')
        if iteration + 1 in data_by_iter.index.unique():
            # Been here before, reset
            data_by_iter = data_by_iter.loc[:iteration]

            regression_by_iter = self.regression.set_index('Iteration')
            self.regression = regression_by_iter.loc[:iteration - 1].reset_index()

            state_by_iter = self.state.set_index('Iteration')
            self.state = state_by_iter.loc[:iteration].reset_index()

        # Store results ... even if changed
        data_by_iter.loc[iteration, 'Results'] = results
        self.data = data_by_iter.reset_index()

    def choose_initial_samples(self):
        self.data = pd.DataFrame(
            columns=['Iteration', '__sample_index__', 'Results', 'Fitted', *self.get_param_names()])
        self.data['Iteration'] = self.data['Iteration'].astype(int)
        self.data['__sample_index__'] = self.data['__sample_index__'].astype(int)

        self.n_dimensions = len(self.params)

        iteration = 0

        # Clear self.state in case of resuming iteration 0 from commission
        self.state = pd.DataFrame(columns=['Iteration', 'Parameter', 'Center', 'Min', 'Max', 'Dynamic'])
        self.state['Iteration'] = self.state['Iteration'].astype(int)

        for param in self.params:
            print (iteration, param['Name'], param['Guess'], param['Min'], param['Max'], param['Dynamic'])
            self.state.loc[len(self.state)] = [iteration, param['Name'], param['Guess'], param['Min'], param['Max'],
                                               param['Dynamic']]

        initial_samples = self.choose_and_clamp_hypersphere_samples_for_iteration(iteration)

        self.add_samples(initial_samples, iteration)

        return initial_samples

    def choose_samples_via_gradient_ascent(self, iteration):

        # assert(iteration >= 1)

        # DYNAMIC ON PREVIOUS ITERATION WHEN COMMISSIONED ...
        state_prev_iter = self.state.set_index('Iteration').loc[[iteration - 1]]
        dynamic_params = [r['Parameter'] for idx, r in state_prev_iter.iterrows() if r['Dynamic']]

        self.data.set_index('Iteration', inplace=True)
        latest_dynamic_samples = self.data.loc[iteration - 1, dynamic_params].values
        latest_results = self.data.loc[iteration - 1, 'Results'].values

        mod = sm.OLS(latest_results, sm.add_constant(latest_dynamic_samples))

        mod_fit = mod.fit()
        # print(mod_fit.summary())

        # Regression parameters for plotting / analysis
        self.regression = self.regression.query('Iteration < @iteration')
        r2_df = pd.DataFrame([[iteration - 1, 'Rsquared', mod_fit.rsquared]],
                             columns=['Iteration', 'Parameter', 'Value'])
        thresh_df = pd.DataFrame([[iteration - 1, 'Rsquared_Threshold', self.rsquared_thresh]],
                                 columns=['Iteration', 'Parameter', 'Value'])
        repeats_df = pd.DataFrame([[iteration - 1, 'Center_Repeats', self.center_repeats]],
                                  columns=['Iteration', 'Parameter', 'Value'])
        self.regression = pd.concat([self.regression, r2_df, thresh_df, repeats_df])
        for (p, v) in zip(['Constant'] + dynamic_params, mod_fit.params):  # mod.endog_names
            regression_param_df = pd.DataFrame([[iteration - 1, p, v]], columns=['Iteration', 'Parameter', 'Value'])
            self.regression = pd.concat([self.regression, regression_param_df])
        for (p, v) in zip(['P_Constant'] + ['P_' + s for s in dynamic_params], mod_fit.pvalues):  # mod.endog_names
            regression_param_df = pd.DataFrame([[iteration - 1, p, v]], columns=['Iteration', 'Parameter', 'Value'])
            self.regression = pd.concat([self.regression, regression_param_df])

        """
        #L1_wt : scalar : The fraction of the penalty given to the L1 penalty term. Must be between 0 and 1 (inclusive). If 0, the fit is ridge regression. If 1, the fit is the lasso.
        mod_fit = mod.fit_regularized(method='coord_descent', maxiter=10000, alpha=1.0, L1_wt=1.0, start_params=None, cnvrg_tol=1e-08, zero_tol=1e-08)
        print(mod_fit.summary())

        from sklearn import linear_model
        clf = linear_model.Lasso(alpha=1.0, fit_intercept=True, normalize=True, precompute=False, copy_X=True, max_iter=1000, tol=0.0001, warm_start=False, positive=False, random_state=None, selection='cyclic')
        clf.fit(latest_dynamic_samples, latest_results)

        print(clf.coef_)
        print(clf.intercept_)
        y = clf.predict(latest_dynamic_samples)
        print(zip(latest_results, y))
        print('R2:', clf.score(latest_dynamic_samples, latest_results))


        print('LassoCV')
        cvf = linear_model.LassoCV(eps=0.001, n_alphas=100, alphas=None, fit_intercept=True, normalize=True, precompute='auto', max_iter=1000, tol=0.0001, copy_X=True, cv=None, verbose=False, n_jobs=-1, positive=False, random_state=None, selection='cyclic')
        cvf.fit(latest_dynamic_samples, latest_results)

        print(cvf.coef_)
        print(cvf.intercept_)
        y = cvf.predict(latest_dynamic_samples)
        print(zip(latest_results, y))
        print('R2:', cvf.score(latest_dynamic_samples, latest_results))
        """

        self.fit_summary = mod_fit.summary().as_csv()

        self.data.loc[iteration - 1, 'Fitted'] = mod_fit.fittedvalues
        self.data.reset_index(inplace=True)

        # Choose X_center for this iteration based on previous
        old_center = self._get_X_center(iteration - 1)
        if mod_fit.rsquared > self.rsquared_thresh:
            # print('Good R^2 (%f), using params: '%mod_fit.rsquared, mod_fit.params)
            coef = mod_fit.params[1:]  # Drop constant
            den = np.sqrt(
                sum([(self.Xmax[pname] - self.Xmin[pname]) ** 2 * c ** 2 for c, pname in zip(coef, dynamic_params)]))

            old_center_of_dynamic_params = old_center[dynamic_params].values
            new_dynamic_center = [x + (self.Xmax[pname] - self.Xmin[pname]) ** 2 * c * self.mu_r / den for x, c, pname
                                  in zip(old_center_of_dynamic_params, coef, dynamic_params)]

        else:
            # print('Bad R^2 (%f)'%mod_fit.rsquared)
            max_idx = np.argmax(latest_results)
            'Stepping to argmax of %f at:' % latest_results[max_idx], latest_dynamic_samples[max_idx]
            new_dynamic_center = latest_dynamic_samples[max_idx].tolist()

        new_center_dict = old_center.to_dict()  # {k:v for k,v in zip(self.get_param_names(), old_center)}
        new_center_dict.update({k: v for k, v in zip(dynamic_params, new_dynamic_center)})

        # User may have added or removed params
        param_names = [p['Name'] for p in self.params]
        # Remove -
        new_center_df = {k: v for k, v in new_center_dict.items() if k in param_names}
        # Add -
        new_params = {p['Name']: p['Guess'] for p in self.params if p['Name'] not in new_center_dict}
        new_center_dict.update(new_params)

        # CLAMP
        new_center_df = pd.Series(new_center_dict, name=0).to_frame().transpose()
        new_center_df = self.clamp(new_center_df)

        # USER CONSTRAINT FN
        new_center_df = new_center_df.apply(self.constrain_sample_fn, axis=1)

        new_state = pd.DataFrame({
            'Iteration': [iteration] * self.n_dimensions,
            'Parameter': new_center_df.columns.values,
            'Center': new_center_df.as_matrix()[0],
            'Min': [self.Xmin[pname] for pname in new_center_df.columns.values],
            'Max': [self.Xmax[pname] for pname in new_center_df.columns.values],
            'Dynamic': [self.Dynamic[pname] for pname in new_center_df.columns.values]
        })

        self.state = self.state.query('Iteration < @iteration')
        self.state = pd.concat([self.state, new_state], ignore_index=True)

        samples = self.choose_and_clamp_hypersphere_samples_for_iteration(iteration)
        self.add_samples(samples, iteration)

        return samples

    def choose_and_clamp_hypersphere_samples_for_iteration(self, iteration):
        N = self.samples_per_iteration
        state_by_iter = self.state.set_index('Iteration')
        # Will vary parameters that are 'Dyanmic' on this iteration
        samples = self.sample_hypersphere(N, state_by_iter.loc[[iteration]])

        # Clamp and constrain
        samples = self.clamp(samples)
        samples = samples.apply(self.constrain_sample_fn, axis=1)

        return samples  # Order shouldn't matter now, so dropped [self.get_param_names()]

    def sample_hypersphere(self, N, state):
        # Pick samples on hypersphere - TODO: clean
        # assert(N > self.center_repeats)

        dynamic_state = state.query('Dynamic == True')

        deviations = []
        standard_normal = norm(loc=0, scale=1)
        radius_normal = norm(loc=self.mu_r, scale=self.sigma_r)
        for i in range(N - self.center_repeats):
            sn_rvs = standard_normal.rvs(size=len(dynamic_state))
            sn_nrm = np.linalg.norm(sn_rvs)
            radius = radius_normal.rvs()
            deviations.append([radius / sn_nrm * sn for sn in sn_rvs])

        X_center = state.reset_index(drop=True).set_index(['Parameter'])[['Center']]
        xc = X_center.transpose().reset_index(drop=True)
        xc.columns.name = ""

        samples = pd.concat([xc] * N).reset_index(drop=True)

        dt = np.transpose(deviations)

        dynamic_state_by_param = dynamic_state.set_index('Parameter')
        for i, pname in enumerate(dynamic_state['Parameter']):
            Xcen = dynamic_state_by_param.loc[pname, 'Center']
            Xrange = dynamic_state_by_param.loc[pname, 'Max'] - dynamic_state_by_param.loc[pname, 'Min']
            samples.loc[self.center_repeats:N, pname] = Xcen + dt[i] * Xrange

        return samples

    def end_condition(self):
        # print("end_condition")
        # Stopping Criterion: good rsqared with small norm?
        # Return True to stop, False to continue
        logger.info('Continuing iterations ...')
        return False

    def get_final_samples(self):
        """
        Resample Stage:
        """
        state_by_iteration = self.state.set_index('Iteration')
        last_iter = sorted(state_by_iteration.index.unique())[-1]

        X_Center = self._get_X_center(last_iter)
        xc = X_Center.to_frame().transpose().reset_index(drop=True)
        xc.columns.name = ""

        dtypes = {name: str(data.dtype) for name, data in xc.iteritems()}
        final_samples_NaN_to_Null = xc.where(~xc.isnull(), other=None)
        return {'final_samples': final_samples_NaN_to_Null.to_dict(orient='list'), 'final_samples_dtypes': dtypes}

    def prep_for_dict(self, df):
        # Needed for Windows compatibility
        # nulls = df.isnull()
        # if nulls.values.any():
        #    df[nulls] = None
        # return df.to_dict(orient='list')

        return df.where(~df.isnull(), other=None).to_dict(orient='list')

    def get_state(self):

        optimtool_state = dict(
            mu_r=self.mu_r,
            sigma_r=self.sigma_r,
            center_repeats=self.center_repeats,
            rsquared_thresh=self.rsquared_thresh,
            n_dimensions=self.n_dimensions,
            params=self.params,
            samples_per_iteration=self.samples_per_iteration,

            data=self.prep_for_dict(self.data),
            data_dtypes={name: str(data.dtype) for name, data in self.data.iteritems()},

            regression=self.prep_for_dict(self.regression),
            regression_dtypes={name: str(data.dtype) for name, data in self.regression.iteritems()},

            state=self.prep_for_dict(self.state),
            state_dtypes={name: str(data.dtype) for name, data in self.state.iteritems()}
        )
        return optimtool_state

    def set_state(self, state, iteration):
        self.mu_r = state['mu_r']
        self.sigma_r = state['sigma_r']
        self.center_repeats = state['center_repeats']
        self.rsquared_thresh = state['rsquared_thresh']
        self.n_dimensions = state['n_dimensions']
        self.params = state['params']  # NOTE: This line will override any updated user params passed to __init__
        self.samples_per_iteration = state['samples_per_iteration']

        data_dtypes = state['data_dtypes']
        self.data = pd.DataFrame.from_dict(state['data'], orient='columns')
        for c in self.data.columns:  # Argh
            self.data[c] = self.data[c].astype(data_dtypes[c])

        regression_dtypes = state['regression_dtypes']
        self.regression = pd.DataFrame.from_dict(state['regression'], orient='columns')
        for c in self.regression.columns:  # Argh
            self.regression[c] = self.regression[c].astype(regression_dtypes[c])

        state_dtypes = state['state_dtypes']
        self.state = pd.DataFrame.from_dict(state['state'], orient='columns')
        for c in self.state.columns:  # Argh
            self.state[c] = self.state[c].astype(state_dtypes[c])

        self.need_resolve = True

    def get_param_names(self):
        return [p['Name'] for p in self.params]

    @staticmethod
    def get_r(num_params, volume_fraction):
        r = math.exp(1 / float(num_params) * (
                    math.log(volume_fraction) - gammaln(num_params / 2. + 1) + num_params / 2. * math.log(math.pi)))
        return r
