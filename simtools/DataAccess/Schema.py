import datetime
import inspect
import json
import os

from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import PickleType
from sqlalchemy import String
from sqlalchemy.orm import relationship

from simtools.DataAccess import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(String, primary_key=True)
    status = Column(Enum('Waiting', 'Commissioned', 'Running', 'Succeeded', 'Failed',  'Cancelled'))
    message = Column(String)
    experiment = relationship("Experiment", back_populates="simulations")
    experiment_id = Column(String, ForeignKey('experiments.exp_id'))
    tags = Column(PickleType(pickler=json))
    pid = Column(String)

    def __repr__(self):
        return "Simulation %s (%s - %s)" % (self.id, self.status, self.message)

    def toJSON(self):
        return {self.id: self.tags}

    def get_path(self,experiment):
        return os.path.join(experiment.sim_root, '%s_%s' % (experiment.exp_name, experiment.exp_id), self.id)


class Experiment(Base):
    __tablename__ = "experiments"

    exp_id = Column(String, primary_key=True)
    dtk_tools_revision = Column(String)
    exe_name = Column(String)
    exp_name = Column(String)
    location = Column(String)
    selected_block = Column(String)
    setup_overlay_file = Column(String)
    sim_root = Column(String)
    sim_type = Column(String)
    command_line = Column(String)
    date_created = Column(Date, default=datetime.datetime.now())

    simulations = relationship("Simulation", back_populates='experiment')

    def get_full_id(self):
        return "%s_%s" % (self.exp_name,self.exp_id)

    def get_path(self):
        return os.path.join(self.sim_root, self.get_full_id())

    def toJSON(self):
        ret = {}
        for name in dir(self):
            value = getattr(self, name)
            # Weed out the internal parameters/methods
            if name.startswith('_') or name in ('metadata',) or inspect.ismethod(value):
                continue

            # Special case for the simulations
            if name == 'simulations':
                ret['simulations'] = {}
                for sim in value:
                    ret['simulations'][sim.id] = sim.tags
                continue

            # By default just add to the dict
            ret[name] = value

        return ret