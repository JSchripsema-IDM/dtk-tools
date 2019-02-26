import multiprocessing
import os
import sys
# Add the tools to the path
from multiprocessing import Manager

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.abspath(os.path.join(dir_path,'..')))
import threading
import time
import traceback
from collections import OrderedDict
from datetime import datetime

from simtools.DataAccess.DataStore import DataStore
from simtools.ExperimentManager.ExperimentManagerFactory import ExperimentManagerFactory
from simtools.SetupParser import SetupParser
from simtools.Utilities.General import init_logging

logger = init_logging('Overseer')


def LogCleaner():
    # Get the last time a cleanup happened
    last_cleanup = DataStore.get_setting('last_log_cleanup')
    if not last_cleanup or (datetime.today() - datetime.strptime(last_cleanup.value.split(' ')[0],'%Y-%m-%d')).days > 1:
        # Do the cleanup
        from simtools.DataAccess.LoggingDataStore import LoggingDataStore
        LoggingDataStore.log_cleanup()
        DataStore.save_setting(DataStore.create_setting(key='last_log_cleanup', value=datetime.today()))


if __name__ == "__main__":

    logger.debug('Start Overseer pid: %d' % os.getpid())
    
    # we technically don't care about full consistency of SetupParser with the original dtk command, as experiments
    # have all been created. We can grab 'generic' max_local_sims / max_threads
    SetupParser.init() # default block
    max_local_sims = int(SetupParser.get('max_local_sims'))

    # Create the queue
    local_queue = multiprocessing.Queue(max_local_sims)

    managers = OrderedDict()

    # Queue to be shared among all runners in order to update the individual simulation states in the DB
    manager = Manager()

    # Take this opportunity to cleanup the logs
    lc = threading.Thread(target=LogCleaner)
    lc.start()

    count = 0

    while True:
        # Retrieve the active LOCAL experiments
        active_experiments = DataStore.get_active_experiments()
        logger.debug('Waiting loop pass number %d, pid %d' % (count, os.getpid()))
        logger.debug('Active experiments')
        logger.debug(active_experiments)
        logger.debug('Managers')
        logger.debug(managers.keys())

        # Create all the managers
        for experiment in active_experiments:

            logger.debug("Looking for manager for experiment %s" % experiment.id)
            if experiment.id not in managers:
                logger.debug('Creating manager for experiment id: %s' % experiment.id)
                manager = None
                try:
                    sys.path.append(experiment.working_directory)
                    manager = ExperimentManagerFactory.from_experiment(experiment)
                except RuntimeError as r:
                    # IF the exception tells us the experiment has not been found -> delete it from the DB
                    if str(r) == "404 NotFound - Failed to retrieve experiment for given id":
                        DataStore.delete_experiment(experiment)
                        continue
                except Exception as e:
                    logger.debug('Exception in creation manager for experiment %s' % experiment.id)
                    logger.debug(e)
                    logger.debug(traceback.format_exc())
                    continue

                if manager:
                    if manager.location == "LOCAL": manager.local_queue = local_queue
                    managers[experiment.id] = manager

            else:
                # Refresh the experiment
                logger.debug("Found manager for experiment %s" % experiment.id)
                managers[experiment.id].experiment = experiment

        # Check every one of them
        logger.debug("Checking experiment managers. There are %d of them. pid: %d" % (len(managers), os.getpid()))
        managers_to_delete = []
        for exp_id, manager in managers.items():
            # Refresh the experiment first
            manager.refresh_experiment()

            # Manager experiment is gone, we dont need it anymore
            if not manager.experiment:
                managers_to_delete.append(exp_id)
            elif manager.finished():
                logger.debug('Manager for experiment id: %s is done' % exp_id)
                managers_to_delete.append(exp_id)
            else:
                logger.debug('Commission simulations as needed for experiment id: %s' % exp_id)
                n_commissioned_sims = manager.commission_simulations()
                logger.debug('Experiment done (re)commissioning %d simulation(s)' % n_commissioned_sims)

        # Delete the managers that needs to be deleted
        for exp_id in managers_to_delete:
            del managers[exp_id]

        # No more active managers -> Exit if our analyzer threads are done
        # Do not use len() to not block anything
        if not managers: break

        time.sleep(10)
        count += 1

logger.debug('No more work to do, Overseer pid: %d exiting...' % os.getpid())
