import ctypes
import json
import operator
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from distutils.version import LooseVersion
from enum import Enum
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pkg_resources

from simtools.Utilities.General import timestamp_filename
from simtools.Utilities.LocalOS import LocalOS
from dtk import __version__ as DTK_VERSION

current_directory = os.path.dirname(os.path.abspath(__file__))
install_directory = os.path.join(current_directory, 'install')

# Force writing a new simtools
force_new_simtools = False

# Force a new database ?
force_new_db = False

# This lets us guarantee a consistent time to be used for timestamped backup files
this_time = datetime.utcnow()

# Get the installed packages on the system
installed_packages = {package.project_name: package.version for package in pkg_resources.working_set}

# Load the list of requirements
requirements = json.load(open('requirements.json', 'r'), object_pairs_hook=OrderedDict)

# Prepare the operators
operators = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq}

# get right pip command
PIP_COMMAND = LocalOS.get_pip_command()


class PackageStatus(Enum):
    MISSING = 0
    VALID = 1
    WRONGVERSION = 2


def download_wheel(wheel):
    # Prepare the urls
    url = "https://institutefordiseasemodeling.github.io/PythonDependencies/{}".format(wheel)
    wheel_path = os.path.join(install_directory, wheel)
    chunks = []

    try:
        resp = urlopen(Request(url))
        chunks.append(resp.read())
    except HTTPError:
        # We could not directly download the wheel, either it is not there or it is in chunks
        # First try if it is in chunks
        part = 0
        for part in range(100):
            try:
                resp = urlopen(Request("{}.{:09d}".format(url, part)))
            except HTTPError:
                break
            chunks.append(resp.read())
        # If we are still part 0, and no chunks, the wheel was not found
        if not chunks and part == 0:
            raise Exception("The wheel file {} could not be found at {}...".format(wheel, url))

    # We have our chunks, write to disk
    if os.path.exists(wheel_path): os.remove(wheel_path)
    with open(wheel_path, "wb") as fp:
        fp.write(b''.join(chunks))

    return wheel_path


def install_package(package, version=None, wheel=None, upgrade=False):
    # A wheel is present => easy just install it
    if wheel:
        install_str = download_wheel(wheel)
    else:
        # No wheel, we need to construct the string for pip
        install_str = package
        if version:
            install_str += "=={}".format(version)

    # Handle the upgrade by forcing the reinstall
    install_args = [PIP_COMMAND, 'install', install_str]
    if upgrade:
        install_args.append('-I')
    subprocess.call(install_args)


def test_package(package, version, test):
    """
    Test if a package is present and with the correct version installed.
    :param package: Package name
    :param version: Needed version
    :param test: can be >= == or <=
    :param extra: used to store extra info
    :return: PackageStatus (MISSING, VALID, WRONGVERSION)
    """
    # The package is not present -> Missing
    if package not in installed_packages:
        return PackageStatus.MISSING

    # The package is in the installed packages
    # The package has no particular version requirement -> all good
    if not version:
        return PackageStatus.VALID

    # The version is required, test if correct
    operator = operators[test]
    if not operator(LooseVersion(installed_packages[package]), LooseVersion(version)):
        return PackageStatus.WRONGVERSION

    # If we made it here, we have the correct package/version
    return PackageStatus.VALID


def get_requirements_by_os():
    """
    Update requirements based on OS
    """
    reqs = OrderedDict()

    for name, val in requirements.items():
        # If no platform specified or the os is in the platforms, add it
        if not val or 'platform' not in val or LocalOS.name in val['platform']:
            # OS: Mac or Linux. No wheel needed except catalyst and pyCOMPS
            if LocalOS.name in (LocalOS.MAC, LocalOS.LINUX) and val and 'wheel' in val:
                if name not in ('pyCOMPS', 'catalyst'):
                    val.pop('wheel')

            # OS: Linux. No version for some packages
            if LocalOS.name == LocalOS.LINUX and name in ('numpy', 'scipy') and val:
                if 'version' in val: val.pop('version')
                if 'test' in val: val.pop('test')

            reqs[name] = val

    return reqs


def install_linux_pre_requisites():
    """
    Install pre-requisites for Linux
    """
    # Doing pre-requisites installation
    from subprocess import check_call, STDOUT

    linux_pre_requisites = {
       "CentOS": {
             "requirements": ["yum-utils",
                              "gcc"
                              ],
             "install_command": "yum"
       },
       "Ubuntu": {
           "requirements": ["python3-pip",
                            "python3-setuptools",
                            "build-essential",
                            "python3-dev",
                            "libfreetype6-dev",
                            "liblapack-dev",
                            "python3-scipy",
                            "python3-tk"
                            ],
           "install_command": "apt-get"
       }
    }

    linux_dist = LocalOS.Distribution
    pre_requisites = []
    if linux_dist in linux_pre_requisites:
        pre_requisites = linux_pre_requisites[linux_dist]["requirements"]
        install_command = linux_pre_requisites[linux_dist]["install_command"]

    if len(pre_requisites) == 0:
        return      # do nothing!

    supports_install_command = False
    try:
        check_call('{} -h'.format(install_command), shell=True)
        supports_install_command = True
    except OSError:
        print("Not able to automatically install packages via {}".format(install_command))
        print("Please make sure the following dependencies are installed on your system:")
        print(pre_requisites)
    except:
        print("Unexpected error checking for {}:".format(install_command), sys.exc_info()[0])
        raise

    if supports_install_command:
        for req in pre_requisites:
            print("Checking/Installing %s" % req)
            check_call([install_command, 'install', '-y', req], stdout=open(os.devnull, 'wb'), stderr=STDOUT)



def install_packages(reqs):
    """
    Install required packages
    """
    if LocalOS.name == LocalOS.LINUX:
        # Doing the apt-get install pre-requisites
        install_linux_pre_requisites()

    # Go through the requirements
    accept_all = False
    deny_all = False
    for name, val in reqs.items():
        print("\n--- {} ---".format(name))

        val = val or {}
        version = val.get('version', None)
        test = val.get('test', '>=')
        wheel = val.get('wheel', None)
        result = test_package(name, version, test)

        # Valid package -> just display info
        if result == PackageStatus.VALID:
            print("Package {} installed and with correct version.".format(name))

        # Missing -> install
        elif result == PackageStatus.MISSING:
            print("Package {} is missing. Installing...".format(name))
            install_package(name, version, wheel)

        # Wrong version -> Prompt user
        elif result == PackageStatus.WRONGVERSION:
            current_v = installed_packages[name]
            print("Package {} is installed with version {}, but we recommend {}.".format(name, current_v, version))
            if deny_all:
                user_input = 'N'
            elif accept_all:
                user_input = 'Y'
            else:
                user_input = None

            while user_input not in ('Y', 'N', 'A', 'L'):
                user_input = input('Would you like to install the recommended version over your system version? [Y]es/[N]o/Yes to [A]ll/No to a[L]l : ').upper()
            if user_input == 'Y' or user_input == 'A':
                install_package(name, version, wheel, upgrade=True)
            else:
                print("Keeping system package {} (v. {})".format(name, current_v))

            if user_input == 'A':
                accept_all = True
            if user_input == 'L':
                deny_all = True

        print("---")

    # Add the develop by default
    # Find a way to empty the arguments and only have develop
    sys.argv = [sys.argv[0], 'develop']

    from setuptools import setup, find_packages

    setup(name='dtk-tools',
          version=DTK_VERSION,
          description='Facilitating submission and analysis of simulations',
          url='https://github.com/InstituteforDiseaseModeling/dtk-tools',
          author='Edward Wenger,'
                 'Benoit Raybaud,'
                 'Daniel Klein,'
                 'Jaline Gerardin,'
                 'Milen Nikolov,'
                 'Aaron Roney,'
                 'Zhaowei Du,'
                 'Prashanth Selvaraj,'
                 'Clark Kirkman IV',
          author_email='ewenger@intven.com,'
                       'braybaud@intven.com,'
                       'dklein@idmod.org,'
                       'jgerardin@intven.com,'
                       'mnikolov@intven.com,'
                       'aroney@intven.com,'
                       'zdu@intven.com,'
                       'pselvaraj@intven.com,'
                       'ckirkman@intven.com',
          packages=find_packages(),
          install_requires=[],
          entry_points={
              'console_scripts': ['calibtool = calibtool.commands:main', 'dtk = dtk.commands:main']
          },
          package_data={'': ['simtools/simtools.ini',
                             'dtk/tools/demographics/generator/WB_crude_birthrate_by_year_and_country.csv']},
          zip_safe=False)


def handle_init():
    """
    Consider user's configuration file
    """
    from simtools.Utilities.ConfigObj import ConfigObj
    # Copy the default.ini into the right directory if not already present
    current_simtools = os.path.join(current_directory, 'simtools', 'simtools.ini')
    default_ini = os.path.join(install_directory, 'default.ini')
    default_config = ConfigObj(default_ini, write_empty_values=True)

    # Set some things in the default CP
    default_eradication = os.path.join(current_directory, 'examples', 'inputs', 'Eradication.exe')
    default_inputs = os.path.join(current_directory, 'examples', 'inputs')
    default_dlls = os.path.join(current_directory, 'examples', 'inputs', 'dlls')
    default_config['LOCAL']['exe_path'] = default_eradication
    default_config['LOCAL']['input_root'] = default_inputs
    default_config['LOCAL']['dll_root'] = default_dlls
    default_config['HPC']['input_root'] = default_inputs
    default_config["HPC"]["base_collection_id_input"] = ''

    if not os.path.exists(current_simtools):
        default_config.write(open(current_simtools, 'wb'))
    elif force_new_simtools:
        print("\nA previous simtools.ini global configuration file is present.")

        # Backup copy the current
        dest_filename = timestamp_filename(filename=current_simtools, time=this_time)
        print("simtools.ini already exists: (%s) -> backing up to: %s" % (current_simtools, dest_filename))
        shutil.move(current_simtools, dest_filename)

        # Write new one
        print("Writing new simtools.ini")
        default_config.write(open(current_simtools, 'wb'))

    # ALso write the default_cp in the examples
    # Smoe specific examples modifications
    example_config = deepcopy(default_config)
    example_config['HPC']['exe_path'] = default_eradication
    example_config['HPC']['dll_root'] = default_dlls
    example_config['HPC']['base_collection_id_exe'] = ''
    example_config['HPC']['base_collection_id_dll'] = ''

    # Collect all the places we should write the simtools.ini
    example_folder = os.path.join(current_directory, "examples")
    dirs = [os.path.join(example_folder, d) for d in os.listdir(example_folder)
            if os.path.isdir(os.path.join(example_folder, d)) and d not in ("inputs", "Templates", "notebooks")]

    dirs.append(example_folder)

    for example_dir in dirs:
        simtools = os.path.join(example_dir, "simtools.ini")

        if os.path.exists(simtools):
            if force_new_simtools:
                dest_filename = timestamp_filename(filename=simtools, time=this_time)
                print("Example simtools.ini already exists: (%s) -> backing up to: %s" % (simtools, dest_filename))
                shutil.move(simtools, dest_filename)
            else:
                continue

        example_config.write(open(simtools, 'wb'))


def verify_matplotlibrc():
    """
    on MAC: make sure file matplotlibrc has content
    backend: Agg
    """
    if LocalOS.name not in [LocalOS.MAC]:
        return

    import matplotlib as mpl
    config_dir = mpl.get_configdir()
    rc_file = os.path.join(config_dir, 'matplotlibrc')

    def has_Agg(rc_file):
        with open(rc_file, "r") as f:
            for line in f:
                ok = re.match(r'^.*backend.*:.*$', line)
                if ok:
                    return True

        return False

    if os.path.exists(rc_file):
        ok = has_Agg(rc_file)
        if not ok:
            # make a backup of existing rc file
            directory = os.path.dirname(rc_file)
            backup_id = 'backup_' + re.sub('[ :.-]', '_', str(datetime.now().replace(microsecond=0)))
            shutil.copy(rc_file, os.path.join(directory, '%s_%s' % ('matplotlibrc', backup_id)))

            # append 'backend : Agg' to existing file
            with open(rc_file, "a") as f:
                f.write('\nbackend : TkAgg')
    else:
        # create a rc file
        with open(rc_file, "wb") as f:
            f.write('backend : TkAgg')


def cleanup_locks():
    """
    Deletes the lock files if they exist
    :return:
    """
    current_dir = os.path.dirname(os.path.realpath(__file__))
    setupparser_lock = os.path.join(current_dir, 'simtools', '.setup_parser_init_lock')
    overseer_lock = os.path.join(current_dir, 'simtools', 'ExperimentManager', '.overseer_check_lock')
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
    current_dir = os.path.dirname(os.path.realpath(__file__))
    db_path = os.path.join(current_dir, 'simtools', 'DataAccess', 'db.sqlite')
    if os.path.exists(db_path):
        dest_filename = timestamp_filename(filename=db_path, time=this_time)
        print("Creating a new local database. Backing up existing one to: %s" % dest_filename)
        shutil.move(db_path, dest_filename)


def main():
    # Get OS-specific requirements
    reqs = get_requirements_by_os()

    # Install required packages
    install_packages(reqs)

    # Consider config file
    handle_init()

    # Create new db
    if force_new_db: backup_db()

    # Make sure matplotlibrc file is valid
    verify_matplotlibrc()

    cleanup_locks()

    # Success !
    print("\n=======================================================")
    print("| Dtk-Tools and dependencies installed successfully.  |")
    print("=======================================================")


if __name__ == "__main__":
    # check os first
    if ctypes.sizeof(ctypes.c_voidp) != 8 or sys.version_info < (3,6):
        print("""\nFATAL ERROR: dtk-tools only supports Python 3.6 x64 and above.\n
         Please download and install a x86-64 version of python at:\n
        - Windows: https://www.python.org/downloads/windows/
        - Mac OSX: https://www.python.org/downloads/mac-osx/
        - Linux: https://www.python.org/downloads/source/\n
        Installation is now exiting...""")
        exit()

    main()
