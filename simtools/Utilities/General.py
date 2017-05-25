import cStringIO
import contextlib
import functools
import logging
import os
import sys

import time

logging_initialized = False
def init_logging(name):
    import logging.config
    global logging_initialized

    if not logging_initialized:
        current_dir = os.path.dirname(os.path.realpath(__file__))
        logging.config.fileConfig(os.path.join(current_dir, 'logging.ini'), disable_existing_loggers=False)
        logging_initialized = True
    return logging.getLogger(name)

try:
    logger = init_logging('Utils')
except:
    pass


def retrieve_item(itemid):
    """
    Return the object identified by id.
    Can be an experiment, a suite or a batch.
    If it is a suite, all experiments with this suite_id will be returned.
    """
    # First try to get an experiment
    from simtools.Utilities.Experiments import retrieve_experiment
    from simtools.DataAccess.DataStore import DataStore
    from simtools.Utilities.COMPSUtilities import exps_for_suite_id
    try:
        return retrieve_experiment(itemid)
    except: pass

    # This was not an experiment, maybe a batch ?
    batch = DataStore.get_batch_by_id(itemid)
    if batch: return batch

    batch = DataStore.get_batch_by_name(itemid)
    if batch: return batch

    # Still no item found -> test the suites
    exps = DataStore.get_experiments_by_suite(itemid)
    if exps: return exps

    # Still not -> last chance is a COMPS suite
    exps = exps_for_suite_id(itemid)
    if exps: return [retrieve_experiment(str(exp.id)) for exp in exps]

    # Didnt find anything sorry
    raise(Exception('Could not find any item corresponding to %s' % itemid))


def get_os():
    """
    Retrieve OS
    """
    msg = "simtools.Utilities.General.get_os() is deprecated. Use simtools.Utilities.General.LocalOS.name"
    logger.warning(msg)
    print msg

    from simtools.Utilities.LocalOS import LocalOS
    return LocalOS.name


def utc_to_local(utc_dt):
    import pytz
    from pytz import timezone

    local_tz = timezone('US/Pacific')
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt) # .normalize might be unnecessary


@contextlib.contextmanager
def nostdout(stdout = False, stderr=False):
    """
    Context used to suppress any print/logging from block of code

    Args:
        stdout: If False, hides. If True Shows. False by default
        stderr: If False, hides. If True Shows. False by default
    """
    # Save current state and disable output
    if not stdout:
        save_stdout = sys.stdout
        sys.stdout  = cStringIO.StringIO()
    if not stderr:
        save_stderr = sys.stderr
        sys.stderr = cStringIO.StringIO()

    # Deactivate logging
    previous_level = logging.root.manager.disable
    logging.disable(logging.ERROR)

    yield

    # Restore
    if not stdout:
        sys.stdout = save_stdout
    if not stderr:
        sys.stderr = save_stderr

    logging.disable(previous_level)


def retry_function(func, wait=1, max_retries=5):
    """
    Decorator allowing to retry the call to a function with some time in between.
    Usage: 
        @retry_function
        def my_func():
            pass
            
        @retry_function(max_retries=10, wait=2)
        def my_func():
            pass
            
    :param func: 
    :param time_between_tries: 
    :param max_retries: 
    :return: 
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        retExc = None
        for i in xrange(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception, e:
                retExc = e
                time.sleep(wait)
        raise retExc
    return wrapper


def caller_name(skip=2):
    """
    Get a name of a caller in the format module.class.method

    `skip` specifies how many levels of stack to skip while getting caller
    name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

    An empty string is returned if skipped levels exceed stack height
    """
    import inspect
    stack = inspect.stack()
    start = 0 + skip
    if len(stack) < start + 1:
      return ''
    parentframe = stack[start][0]

    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    if module:
        name.append(module.__name__)
    # detect classname
    if 'self' in parentframe.f_locals:
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append( codename ) # function or a method
    del parentframe
    return ".".join(name)


def remove_null_values(null_dict):
    ret = {}
    for key, value in null_dict.iteritems():
        if value:
            ret[key] = value
    return ret


def get_tools_revision():
    # Get the tools revision
    try:
        import subprocess
        file_dir = os.path.dirname(os.path.abspath(__file__))
        revision = subprocess.check_output(["git", "describe", "--tags"], cwd=file_dir).replace("\n", "")
    except:
        revision = "Unknown"

    return revision


def get_md5(filename):
    from matplotlib.finance import md5
    logger.info('Getting md5 for ' + filename)
    with open(filename) as file:
        md5calc = md5()
        while True:
            data = file.read(10240)  # value picked from example!
            if len(data) == 0:
                break
            md5calc.update(data)
    md5_value = md5calc.hexdigest()
    return md5_value


def is_remote_path(path):
    return path.startswith('\\\\')


class CommandlineGenerator(object):
    """
    A class to construct command line strings from executable, options, and params
    """

    def __init__(self, exe_path, options, params):
        self._exe_path = exe_path
        self._options = options
        self._params = params

    @property
    def Executable(self):
        return self._exe_path

    @property
    def Options(self):
        options = []
        for k, v in self._options.items():
            # Handles spaces
            value = '"%s"' % v if ' ' in v else v
            if k[-1] == ':':
                options.append(k + value)  # if the option ends in ':', don't insert a space
            else:
                options.extend([k, value])  # otherwise let join (below) add a space

        return ' '.join(options)

    @property
    def Params(self):
        return ' '.join(self._params)

    @property
    def Commandline(self):
        return ' '.join(filter(None, [self.Executable, self.Options, self.Params]))  # join ignores empty strings


def rmtree_f(dir):
    import shutil
    if os.path.exists(dir):
        shutil.rmtree(dir, onerror=rmtree_f_on_error)


def rmtree_f_on_error(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    import stat
    if not os.access(path, os.W_OK):
        # Is the error an access error ?
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise


def is_running(pid, name_part):
    """
    Determines if the given pid is running and is running the specified process (name).
    :param pid: The pid to check.
    :param name_part: a case-sensitive partial name by which the thread can be properly identified.
    :return: True/False
    """
    import psutil
    # ck4, This should be refactored to use a common module containing a dict of Process objects
    #      This way, we don't need to do the name() checking, just use the method process.is_running(),
    #      since this method checks for pid number being active AND pid start time.
    if not pid:
        logger.debug("is_running: no valid pid provided.")
        return False

    pid = int(pid)

    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        logger.debug("is_running: No such process with pid: %d" % pid)
        return False

    running = process.is_running()
    process_name = process.name()
    valid_name = name_part in process_name

    logger.debug("is_running: pid %s running? %s valid_name (%s)? %s. name: %s" %
                 (pid, running, name_part, valid_name, process_name))

    if is_running and valid_name:
        logger.debug("is_running: pid %s is running and process name is valid." % pid)
        return True

    return False
