import datetime
import json

from simtools.DataAccess import session_scope, logger
from simtools.DataAccess.Schema import Experiment, Simulation
from simtools.utils import remove_null_values
from sqlalchemy.orm import joinedload


class ExperimentDataStore:
    @classmethod
    def create_experiment(cls, **kwargs):
        if 'date_created' not in kwargs:
            kwargs['date_created'] = datetime.datetime.now()
        return Experiment(**kwargs)

    @classmethod
    def get_experiment(cls, exp_id):
        with session_scope() as session:
            # Get the experiment
            # Also load the associated simulations eagerly
            experiment = session.query(Experiment).options(
                joinedload('simulations').joinedload('experiment').joinedload('analyzers')) \
                .filter(Experiment.exp_id == exp_id).one_or_none()

            # Detach the object from the session
            session.expunge_all()

        return experiment

    @classmethod
    def batch_save_experiments(cls, batch):
        with session_scope() as session:
            for exp in batch:
                cls.save_experiment(exp, False, session)

    @classmethod
    def save_experiment(cls, experiment, verbose=True, session=None):
        if verbose:
            # Dont display the null values
            logger.info('Saving meta-data for experiment:')
            from simtools.DataAccess.DataStore import dumper
            logger.info(json.dumps(remove_null_values(experiment.toJSON()), indent=3, default=dumper, sort_keys=True))

        with session_scope(session) as session:
            session.merge(experiment)

    @classmethod
    def get_most_recent_experiment(cls, id_or_name):
        id_or_name = '' if not id_or_name else id_or_name
        with session_scope() as session:
            experiment = session.query(Experiment) \
                .filter(Experiment.id.like('%%%s%%' % id_or_name)) \
                .options(joinedload('simulations').joinedload('experiment').joinedload('analyzers')) \
                .order_by(Experiment.date_created.desc()).first()

            session.expunge_all()
        return experiment

    @classmethod
    def get_active_experiments(cls, location=None):
        with session_scope() as session:
            experiments = session.query(Experiment).distinct(Experiment.exp_id) \
                .join(Experiment.simulations) \
                .options(joinedload('simulations').joinedload('experiment').joinedload('analyzers')) \
                .filter(~Simulation.status.in_(('Succeeded', 'Failed', 'Canceled')))
            if location:
                experiments = experiments.filter(Experiment.location == location)

            experiments = experiments.all()
            session.expunge_all()

        return experiments

    @classmethod
    def get_experiments(cls, id_or_name, current_dir=None):
        id_or_name = '' if not id_or_name else id_or_name
        with session_scope() as session:
            experiments = session.query(Experiment).filter(Experiment.id.like('%%%s%%' % id_or_name))
            if current_dir:
                experiments = experiments.filter(Experiment.working_directory == current_dir)
            session.expunge_all()

        return experiments

    @classmethod
    def delete_experiment(cls, experiment):
        with session_scope() as session:
            session.delete(session.query(Experiment).filter(Experiment.id == experiment.id).one())

    @classmethod
    def delete_experiments_by_suite(cls, suite_ids, verbose=False):
        """
        Delete those experiments which are associated with suite_ids
        suite_ids: list of suite ids
        """
        with session_scope() as session:
            # Issue: related tables are not deleted
            # num = session.query(Experiment).filter(Experiment.suite_id.in_(suite_ids)).delete(synchronize_session='fetch')

            # New approach: it will delete related simulations
            exps = session.query(Experiment).filter(Experiment.suite_id.in_(suite_ids))
            num = 0
            for exp in exps:
                session.delete(exp)
                num += 1
            if verbose:
                print '%s experiment(s) deleted.' % num

    @classmethod
    def get_experiments_by_suite(cls, suite_ids):
        """
        Get the experiments which are associated with suite_id
        suite_ids: list of suite ids
        """
        exp_list = None
        with session_scope() as session:
            exp_list = session.query(Experiment).filter(Experiment.suite_id.in_(suite_ids)).all()
            session.expunge_all()

        return exp_list

    @classmethod
    def delete_experiments(cls, exp_list, verbose=False):
        """
        Delete experiments given from input
        exp_list: list of experiments
        """
        exp_ids = [exp.exp_id for exp in exp_list]
        with session_scope() as session:
            # Issue: related tables are not deleted
            # num = session.query(Experiment).filter(Experiment.exp_id.in_(exp_ids)).delete(synchronize_session='fetch')

            # New approach: it will delete related simulations
            exps = session.query(Experiment).filter(Experiment.exp_id.in_(exp_ids))
            num = 0
            for exp in exps:
                session.delete(exp)
                num += 1
            if verbose:
                print '%s experiment(s) deleted.' % num

    @classmethod
    def get_recent_experiment_by_filter(cls, num=20, is_all=False, name=None, location=None):
        with session_scope() as session:
            experiment = session.query(Experiment) \
                .options(joinedload('simulations')) \
                .order_by(Experiment.date_created.desc())

            if name:
                experiment = experiment.filter(Experiment.exp_name.like('%%%s%%' % name))

            if location:
                experiment = experiment.filter(Experiment.location == location)

            if is_all:
                experiment = experiment.all()
            else:
                experiment = experiment.limit(num).all()

            session.expunge_all()
        return experiment


