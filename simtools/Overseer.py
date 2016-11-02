import gc

import logging
import multiprocessing
import threading
import time
from Queue import Queue
from collections import OrderedDict

import sys
from simtools.DataAccess.DataStore import DataStore
from simtools.DataAccess.LoggingDataStore import LoggingDataStore
from simtools.ExperimentManager.ExperimentManagerFactory import ExperimentManagerFactory
from simtools.SetupParser import SetupParser
from simtools.utils import init_logging

logger = init_logging('Overseer')

def SimulationStateUpdater(states):
    while True:
        logger.debug("Simulation update function")
        logger.debug(states)
        if states:
            try:
                batch = []
                for id,sim in states.iteritems():
                    if sim.status not in (
                    'Waiting', 'Commissioned', 'Running', 'Succeeded', 'Failed', 'Canceled', 'CancelRequested',
                    "Retry", "CommissionRequested", "Provisioning", "Created"):
                        logger.warn(
                            "Failed to retrieve correct status for simulation %s. Status returned: %s" % (sim.id,sim.status))
                        continue
                    batch.append({'sid':id, 'status':sim.status, 'message':sim.message,'pid':sim.pid})

                DataStore.batch_simulations_update(batch)
                states.clear()
            except Exception as e:
                logger.error("Exception in the status updater")
                logger.error(e)


if __name__ == "__main__":
    logger.debug('Start Overseer')
    # Retrieve the threads number
    sp = SetupParser()
    max_local_sims = int(sp.get('max_local_sims'))
    max_analysis_threads = int(sp.get('max_threads'))

    # Create the queues and semaphore
    local_queue = Queue(max_local_sims)
    analysis_semaphore = threading.Semaphore(max_analysis_threads)

    update_states = {}
    managers = OrderedDict()

    # Take this opportunity to cleanup the logs
    # t2 = multiprocessing.Process(target=LoggingDataStore.cleanup)
    # t2.start()

    # will hold the analyze threads
    analysis_threads = []

    while True:
        # Retrieve the active LOCAL experiments
        active_experiments = DataStore.get_active_experiments()
        logger.debug('Waiting loop...')
        logger.debug('Active experiments')
        logger.debug(active_experiments)
        logger.debug('Managers')
        logger.debug(managers.keys())

        # Update the states
        SimulationStateUpdater(update_states)

        # Create all the managers
        for experiment in active_experiments:
            if not managers.has_key(experiment.id):
                logger.debug('Creation of manager for experiment id: %s' % experiment.id)
                try:
                    sys.path.append(experiment.working_directory)
                    manager = ExperimentManagerFactory.from_experiment(experiment)
                except Exception as e:
                    logger.error('Exception in creation manager for experiment %s' % experiment.id)
                    logger.error(e)
                    exit()
                managers[experiment.id] = manager
                manager.maxThreadSemaphore = analysis_semaphore
                if manager.location == "LOCAL": manager.local_queue = local_queue

        # Check every one of them
        for manager in managers.values():
            # If the runners have not been created -> create them
            if not manager.runner_created:
                logger.debug('Commission simulations for experiment id: %s' % manager.experiment.id)
                manager.commission_simulations(update_states, lock)
                logger.debug('Experiment done commissioning ? %s' % manager.runner_created)
                continue

            # If the manager is done -> analyze
            if manager.finished():
                logging.debug('Manager for experiment id: %s is done' % manager.experiment.id)
                # Analyze
                athread = threading.Thread(target=manager.analyze_experiment)
                athread.start()
                analysis_threads.append(athread)

                # After analysis delete the manager from the list
                del managers[manager.experiment.id]
                gc.collect()

        # Cleanup the analyze thread list
        for ap in analysis_threads:
            if not ap.is_alive(): analysis_threads.remove(ap)
        logger.debug("Analysis thread: %s" % analysis_threads)

        # No more active managers  -> Exit if our analzers threads are done
        # Do not use len() to not block anything
        if managers == OrderedDict() and analysis_threads == []: break

        time.sleep(10)

logger.debug('No more work to do, exiting...')
