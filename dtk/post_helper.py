import os
import errno
import shutil
from copy import deepcopy
from datetime import datetime
from simtools.Utilities.General import timestamp_filename

current_directory = os.path.dirname(os.path.abspath(__file__))
root_directory = os.path.dirname(current_directory)
install_directory = os.path.join(root_directory, 'install')


def handle_master_ini():
    """
    Consider user's configuration file
    """
    from simtools.Utilities.ConfigObj import ConfigObj

    # Copy the default.ini into the simtools directory
    default_ini = os.path.join(install_directory, 'default.ini')
    default_config = ConfigObj(default_ini, write_empty_values=True)

    # Set some things in the default CP
    default_eradication = os.path.join(root_directory, 'examples', 'inputs', 'Eradication.exe')
    default_inputs = os.path.join(root_directory, 'examples', 'inputs')
    default_dlls = os.path.join(root_directory, 'examples', 'inputs', 'dlls')
    default_config['LOCAL']['exe_path'] = default_eradication
    default_config['LOCAL']['input_root'] = default_inputs
    default_config['LOCAL']['dll_root'] = default_dlls
    default_config['HPC']['input_root'] = default_inputs
    default_config["HPC"]["base_collection_id_input"] = ''

    master_simtools = os.path.join(root_directory, 'simtools', 'simtools.ini')
    default_config.write(open(master_simtools, 'wb'))


def handle_examples_ini(example_folder, subdirs=True):
    """
    Consider user's configuration file
    """
    from simtools.Utilities.ConfigObj import ConfigObj

    # Copy the default.ini into the right directory if not already present
    default_ini = os.path.join(install_directory, 'default.ini')
    default_config = ConfigObj(default_ini, write_empty_values=True)

    example_config = deepcopy(default_config)

    # Set some things in the default CP
    default_eradication = os.path.join(example_folder, 'inputs', 'Eradication.exe')
    default_inputs = os.path.join(example_folder, 'inputs')
    default_dlls = os.path.join(example_folder, 'inputs', 'dlls')

    example_config['LOCAL']['exe_path'] = default_eradication
    example_config['LOCAL']['input_root'] = default_inputs
    example_config['LOCAL']['dll_root'] = default_dlls
    example_config['HPC']['input_root'] = default_inputs
    example_config["HPC"]["base_collection_id_input"] = ''

    # Some specific examples modifications
    example_config['HPC']['exe_path'] = default_eradication
    example_config['HPC']['dll_root'] = default_dlls
    example_config['HPC']['base_collection_id_exe'] = ''
    example_config['HPC']['base_collection_id_dll'] = ''

    # Collect all the places we should write the simtools.ini
    dirs = []
    if subdirs:
        dirs = [os.path.join(example_folder, d) for d in os.listdir(example_folder)
                if os.path.isdir(os.path.join(example_folder, d)) and d not in ("inputs", "Templates", "notebooks")]
    dirs.append(example_folder)

    for example_dir in dirs:
        simtools = os.path.join(example_dir, "simtools.ini")
        example_config.write(open(simtools, 'wb'))


def handle_project_ini(project_folder):
    """
    Consider user's configuration file
    """
    from simtools.Utilities.ConfigObj import ConfigObj

    # Copy the default.ini into the right directory if not already present
    default_ini = os.path.join(install_directory, 'default.ini')
    default_config = ConfigObj(default_ini, write_empty_values=True)

    # Set some things in the default CP
    default_eradication = os.path.join(project_folder, 'Executables', 'Eradication.exe')
    default_inputs = os.path.join(project_folder, 'inputs')
    default_dlls = os.path.join(project_folder, 'dlls')

    # Some specific examples modifications
    example_config = deepcopy(default_config)
    example_config['HPC']['exe_path'] = default_eradication
    example_config['HPC']['dll_root'] = default_dlls
    example_config['HPC']['base_collection_id_exe'] = ''
    example_config['HPC']['base_collection_id_dll'] = ''

    simtools = os.path.join(project_folder, "simtools.ini")
    example_config.write(open(simtools, 'wb'))


def cleanup_locks():
    """
    Deletes the lock files if they exist
    """
    setupparser_lock = os.path.join(root_directory, 'simtools', '.setup_parser_init_lock')
    overseer_lock = os.path.join(root_directory, 'simtools', 'ExperimentManager', '.overseer_check_lock')
    if os.path.exists(setupparser_lock):
        try:
            os.remove(setupparser_lock)
        except:
            print("Could not delete file: %s" % setupparser_lock)

    if os.path.exists(overseer_lock):
        try:
            os.remove(overseer_lock)
        except:
            print("Could not delete file: %s" % overseer_lock)


def backup_db():
    """
    Backup existing db if it exists
    """
    db_path = os.path.join(root_directory, 'simtools', 'DataAccess', 'db.sqlite')
    if os.path.exists(db_path):
        # This lets us guarantee a consistent time to be used for timestamped backup files
        this_time = datetime.utcnow()

        dest_filename = timestamp_filename(filename=db_path, time=this_time)
        print("Creating a new local database. Backing up existing one to: %s" % dest_filename)
        shutil.move(db_path, dest_filename)


def start(output_dir, pj_name='New Project'):
    """
    Create a start-up project with boiler templates. Under construction...
    """
    # new folder
    subdir = os.path.join(output_dir, pj_name)

    # create your subdirectory
    os.mkdir(subdir)

    example_folder = os.path.join(root_directory, "examples")
    default_eradication = os.path.join(root_directory, 'examples', 'inputs', 'Eradication.exe')

    # make folders
    os.mkdir(os.path.join(subdir, 'Dlls'))
    os.mkdir(os.path.join(subdir, 'User-files'))
    os.mkdir(os.path.join(subdir, 'Inputs'))
    os.mkdir(os.path.join(subdir, 'Executables'))

    # copy example_sim.py
    copy(os.path.join(example_folder, "example_sim.py"), subdir)

    # copy eradication.exe
    copy(default_eradication, os.path.join(subdir, 'Executables'))

    # create a simtools.ini file
    handle_project_ini(project_folder=subdir)

    # # new file
    # filepath = os.path.join(subdir, 'test.txt')
    #
    # # create a file.
    # try:
    #     f = open(filepath, 'w')
    #     f.write('Demo project...')
    #     f.close()
    # except IOError:
    #     print("Wrong path provided")


def copy(src, dest):
    """
    Copy file/directory to another location
    """
    try:
        shutil.copytree(src, dest)
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else:
            print('Directory not copied. Error: %s' % e)
