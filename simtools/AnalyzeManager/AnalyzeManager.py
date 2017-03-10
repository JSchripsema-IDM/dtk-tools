
import os
from simtools.ExperimentManager.ExperimentManagerFactory import ExperimentManagerFactory
from simtools.SetupParser import SetupParser
import multiprocessing
from simtools.Utilities.General import get_os, init_logging, nostdout

logger = init_logging('AnalyzeManager')
current_dir = os.path.dirname(os.path.realpath(__file__))


class AnalyzeManager:

    def __init__(self, exp_list, analyzers, setup=None):
        if not setup:
            setup = SetupParser()
        self.exp_list = exp_list if isinstance(exp_list, list) else [exp_list]
        self.analyzers = analyzers if isinstance(analyzers, list) else [analyzers]
        self.maxThreadSemaphore = multiprocessing.Semaphore(int(setup.get('max_threads', 16)))

        self.parsers = []
        self.initialize(self.exp_list)

    def initialize(self, exp_list):
        for exp in exp_list:
            self.generate_sim_parser(exp)

    def generate_sim_parser(self, exp):
        exp_manager = ExperimentManagerFactory.from_experiment(exp)

        if exp_manager.location == 'HPC':
            if not exp_manager.assets_service:
                exp_manager.parserClass.createSimDirectoryMap(exp_manager.experiment.exp_id, exp_manager.experiment.suite_id)

            if exp_manager.compress_assets:
                with nostdout():
                    exp_manager.parserClass.enableCompression()

        for simulation in exp_manager.experiment.simulations:
            # Add the simulation_id to the tags
            simulation.tags['sim_id'] = simulation.id

            # Called when a simulation finishes
            filtered_analyses = [a for a in self.analyzers if a.filter(simulation.tags)]
            if filtered_analyses:
                parser = exp_manager.get_output_parser(simulation.get_path(), simulation.id, simulation.tags, filtered_analyses)
                self.parsers.append(parser)

    def analyze_simulation(self, simulation, manager):
        # Add the simulation_id to the tags
        simulation.tags['sim_id'] = simulation.id

        # Called when a simulation finishes
        filtered_analyses = [a for a in self.analyzers if a.filter(simulation.tags)]
        if not filtered_analyses:
            logger.debug('Simulation %s did not pass filter on any analyzer.' % simulation.id)
            return

        self.maxThreadSemaphore.acquire()
        parser = manager.get_output_parser(simulation.get_path(), simulation.id, simulation.tags, filtered_analyses)
        parser.start()

    def analyze(self):
        # If no analyzers -> quit
        if len(self.analyzers) == 0:
            return

        for parser in self.parsers:
            self.maxThreadSemaphore.acquire()
            parser.start()

        # We are all done, finish analyzing
        for p in self.parsers:
            p.join()

        plotting_processes = []
        from multiprocessing import Process
        for a in self.analyzers:
            a.combine({parser.sim_id: parser for parser in self.parsers})
            a.finalize()
            # Plot in another process
            try:
                # If on mac just plot and continue
                if get_os() == 'mac':
                    a.plot()
                    continue
                plotting_process = Process(target=a.plot)
                plotting_process.start()
                plotting_processes.append(plotting_process)
            except Exception as e:
                logger.error("Error in the plotting process for analyzer %s" % a)
                logger.error("Experiments list %s" % self.exp_list)
                logger.error(e)

        for p in plotting_processes:
            p.join()

        import matplotlib.pyplot as plt  # avoid OS X conflict with Tkinter COMPS authentication
        plt.show()
