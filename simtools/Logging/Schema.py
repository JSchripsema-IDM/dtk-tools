import json
import os

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import PickleType
from sqlalchemy import String

from simtools.DataAccess import Base_logs, engine_logs


class LogRecord(Base_logs):
    __tablename__ = "Logs"
    created = Column(DateTime(timezone=True), primary_key=True)
    name = Column(String, primary_key=True)
    log_level = Column(Integer)
    log_level_name = Column(String)
    message = Column(String)
    args = Column(PickleType(pickler=json))
    module = Column(String)
    func_name = Column(String)
    line_no = Column(Integer)
    exception = Column(String)
    process = Column(Integer)
    thread = Column(String)
    thread_name = Column(String)
    cwd = Column(String, default=os.getcwd())

Base_logs.metadata.create_all(engine_logs)
