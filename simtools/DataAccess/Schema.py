import datetime
import inspect
import json
import os

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import PickleType
from sqlalchemy import String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from simtools.DataAccess import Base, engine

class Analyzer(Base):
    __tablename__ = "analyzers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    analyzer = Column(String)
    experiment_id = Column(String, ForeignKey('experiments.exp_id'))
    experiment = relationship("Experiment", back_populates="analyzers")


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(String, primary_key=True)
    status = Column(Enum('Waiting', 'Commissioned', 'Running', 'Succeeded', 'Failed',  'Canceled', 'CancelRequested',
                         "Retry", "CommissionRequested", "Provisioning", "Created"))
    message = Column(String)
    experiment = relationship("Experiment", back_populates="simulations")
    experiment_id = Column(String, ForeignKey('experiments.exp_id'))
    tags = Column(PickleType(pickler=json))
    date_created = Column(DateTime(timezone=True), default=datetime.datetime.now())
    pid = Column(String)

    def __repr__(self):
        return "Simulation %s (%s - %s)" % (self.id, self.status, self.message)

    def toJSON(self):
        return {self.id: self.tags}

    def get_path(self):
        if self.experiment.location == "LOCAL":
            return os.path.join(self.experiment.sim_root, '%s_%s' % (self.experiment.exp_name, self.experiment.exp_id), self.id)
        else:
            from simtools.OutputParser import CompsDTKOutputParser
            if not CompsDTKOutputParser.sim_dir_map or  not self.id in CompsDTKOutputParser.sim_dir_map:
                CompsDTKOutputParser.createSimDirectoryMap(exp_id=self.experiment.exp_id, save=True)
            return CompsDTKOutputParser.sim_dir_map[self.id]


class Experiment(Base):
    __tablename__ = "experiments"

    exp_id = Column(String, primary_key=True)
    suite_id = Column(String)
    dtk_tools_revision = Column(String)
    exe_name = Column(String)
    exp_name = Column(String)
    location = Column(String)
    selected_block = Column(String)
    setup_overlay_file = Column(String)
    sim_root = Column(String)
    sim_type = Column(String)
    command_line = Column(String)
    working_directory = Column(String, default=os.getcwd())
    date_created = Column(DateTime(timezone=True), default=datetime.datetime.now())
    endpoint = Column(String)
    experiment_runner_id = Column(Integer)

    simulations = relationship("Simulation", back_populates='experiment', cascade="all, delete-orphan", order_by="Simulation.date_created")
    analyzers = relationship("Analyzer", back_populates='experiment', cascade="all, delete-orphan")

    def __repr__(self):
        return "Experiment %s" % self.id

    @hybrid_property
    def id(self):
        return self.exp_name + "_" + self.exp_id

    def get_path(self):
        if self.location == "LOCAL":
            return os.path.join(self.sim_root, self.id)

    def contains_simulation(self, simid):
        for sim in self.simulations:
            if sim.id == simid:
                return True
        return False

    def is_done(self):
        for sim in self.simulations:
            if sim.status not in ('Succeeded', 'Failed','Canceled'):
                return False
        return True

    def toJSON(self):
        ret = {}
        for name in dir(self):
            value = getattr(self, name)
            # Weed out the internal parameters/methods
            if name.startswith('_') or name in ('metadata') or inspect.ismethod(value):
                continue

            # Special case for the simulations
            if name == 'simulations':
                ret['simulations'] = {}
                for sim in value:
                    ret['simulations'][sim.id] = sim.tags
                continue

            if name == 'analyzers':
                ret['analyzers'] = []
                for a in value:
                    ret['analyzers'].append(a.name)
                continue

            # By default just add to the dict
            ret[name] = value

        return ret

Base.metadata.create_all(engine)