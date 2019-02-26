import pickle
from abc import abstractmethod, ABCMeta
from multiprocessing import Process

from simtools.DataAccess.DataStore import DataStore
from simtools.SetupParser import SetupParser


class BaseSimulationCreator(Process):
    """
    Simulation creator base class.
    """
    __metaclass__ = ABCMeta

    def __init__(self, config_builder, initial_tags,  work_queue, experiment, cache):
        super(BaseSimulationCreator, self).__init__()
        self.config_builder = config_builder
        self.experiment = experiment
        self.initial_tags = initial_tags
        self.work_queue = work_queue
        self.cache = cache
        self.created_simulations = []
        self.setup_parser_singleton = SetupParser.singleton

    def run(self):
        SetupParser.init(singleton=self.setup_parser_singleton)
        try:
            self.process()
        except Exception as e:
            print("Exception during commission")
            import traceback
            traceback.print_exc()
            exit()

    def process(self):
        self.pre_creation()

        for batch in iter(self.work_queue.get, None):
            if not batch:
                break

            for mod_fn_list in batch:
                cb = pickle.loads(pickle.dumps(self.config_builder, protocol=pickle.HIGHEST_PROTOCOL))

                # modify next simulation according to experiment builder
                # also retrieve the returned metadata
                tags = self.initial_tags.copy() if self.initial_tags else {}

                for func in mod_fn_list:
                    md = func(cb)
                    tags.update(md)

                # Prepare the assets assets
                cb.assets.prepare(cb)

                # Create the simulation
                s = self.create_simulation(cb)

                # Append the environment to the tag and add the default experiment tags if any
                self.set_tags_to_simulation(s, tags, cb)

                # Add the files
                self.add_files_to_simulation(s, cb)

                # Add to the created simulations array
                self.created_simulations.append(s)

            self.process_batch()
            self.post_creation()

    def process_batch(self):
        self.save_batch()

        # Now that the save is done, we have the ids ready -> create the simulations
        for sim in self.created_simulations:
            self.cache.append(DataStore.create_simulation(id=str(sim.id), tags=sim.tags, experiment_id=self.experiment.exp_id))

        self.created_simulations = []

    @abstractmethod
    def create_simulation(self, cb):
        pass

    @abstractmethod
    def pre_creation(self):
        pass

    @abstractmethod
    def save_batch(self):
        pass

    def post_creation(self):
        pass

    @abstractmethod
    def add_files_to_simulation(self, s, cb):
        pass

    @abstractmethod
    def set_tags_to_simulation(self, s, tags, cb):
        pass
