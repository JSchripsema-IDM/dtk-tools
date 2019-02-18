import platform
import getpass
from simtools.Utilities import Distro
from distutils import spawn


def get_linux_distribution():
    name = Distro.name().lower()

    if 'centos' in name:
        return 'CentOS'
    elif 'ubuntu' in name:
        return 'Ubuntu'
    elif 'debian' in name:
        return 'Debian'
    elif 'fedora' in name:
        return 'Fedora'


class LocalOS:
    """
    A Central class for representing values whose proper access methods may differ between platforms.
    """
    class UnknownOS(Exception):
        pass

    WINDOWS = 'win'
    LINUX = 'lin'
    MAC = 'mac'
    ALL = (WINDOWS, LINUX, MAC)
    OPERATING_SYSTEMS = {
        'windows': {
            'name': WINDOWS,
            'username': getpass.getuser()
        },
        'linux': {
            'name': LINUX,
            'username': getpass.getuser()
        },
        'darwin': {
            'name': MAC,
            'username': getpass.getuser()
        }
    }
    PIP_COMMANDS = ['pip3', 'pip3.7', 'pip3.6', 'pip']

    _os = platform.system().lower()
    if not _os in OPERATING_SYSTEMS.keys():
        raise UnknownOS("Operating system %s is not currently supported." % platform.system())

    username = OPERATING_SYSTEMS[_os]['username']
    name = OPERATING_SYSTEMS[_os]['name']

    Distribution = get_linux_distribution()

    @classmethod
    def get_pip_command(cls):
        for pip in cls.PIP_COMMANDS:
            if spawn.find_executable(pip):
                return pip

        # If we get to this point, no pip was found -> exception
        raise OSError("pip could not be found on this system.\n"
                      "Make sure Python is installed correctly and pip is in the PATH")




