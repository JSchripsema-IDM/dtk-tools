import json
import os
import sys
from ConfigParser import ConfigParser

from dtk.utils.ioformat.OutputMessage import OutputMessage


class SetupParser:
    """
    Parse user settings and directory locations
    from setup configuration file: simtools.cfg
    """
    selected_block = None
    setup_file = None

    def __init__(self, selected_block=None, setup_file=None, force=False, fallback='LOCAL', quiet=False):
        """
        Build a SetupParser.
        The selected_block and setup_file will be stored in class variables and will only be replaced in subsequent
        instances if the force parameter is True.

        If no setup_file is specified, the SetupParser will look in the current working directory for a simtools.ini
        file. If a file is specified, then this file is used and simtools.ini in the working directory is ignored.

        The global defaults (simtools/simtools.ini) are always loaded first before any overlay is applied.

        If the current selected_block cannot be found in the global default or overlay, then the fallback block is used.

        :param selected_block: The current block we want to use
        :param setup_file: The current overlay file we want to use
        :param force: Force the replacement of selected_block and setup_file in the class variable
        :param fallback: Fallback block if the selected_block cannot be found
        """
        # Store the selected_block in the class only if passed
        if selected_block and (not SetupParser.selected_block or force):
            SetupParser.selected_block = selected_block
        elif not SetupParser.selected_block and not selected_block:
            # There's no block stored and none passed -> assume the fallback
            SetupParser.selected_block = fallback

        if setup_file and (not SetupParser.setup_file or force):
            # Only add the file if it exists
            if os.path.exists(setup_file):
                SetupParser.setup_file = setup_file
            else:
                if not quiet:
                    OutputMessage('The setup file (%s) do not exist anymore, ignoring...' % setup_file, 'warning')

        # First, always load the defaults
        self.setup = ConfigParser()
        self.setup.read(os.path.join(os.path.dirname(__file__), 'simtools.ini'))

        # Add the defaults of LOCAL/HPC to the other blocks in the defaults
        for section in self.setup.sections():
            if section in ('LOCAL','HPC'): continue

            # get the type
            type = self.setup.get(section,'type')

            # brings the missing params
            for item in self.setup.items(type):
                if not self.setup.has_option(section, item[0]):
                    self.setup.set(section, item[0],item[1])

        # Then overlays the eventual setup_file passed or simtools.ini in working dir
        overlay_path = None
        if self.setup_file and os.path.exists(self.setup_file):
            overlay_path = self.setup_file
        elif os.path.exists(os.path.join(os.getcwd(), 'simtools.ini')):
            overlay_path = os.path.join(os.getcwd(), 'simtools.ini')

        # Add the user to the default
        if sys.platform == 'win32':
            user = os.environ['USERNAME']
        else:
            import pwd
            user = pwd.getpwuid(os.geteuid())[0]
        self.setup.set('DEFAULT', 'user', user)

        # If we found an overlay applies it
        if overlay_path:
            overlay = ConfigParser()
            overlay.read(overlay_path)

            # Add the user just in case if not specified already
            if not overlay.has_option('DEFAULT','user'):
                overlay.set('DEFAULT','user',user)

            # Overlay
            self.overlay_setup(overlay)

        # Test if we now have the block we want
        if not self.setup.has_section(self.selected_block):
            setup_file_path = overlay_path if overlay_path else os.path.join(os.path.dirname(__file__), 'simtools.ini')
            if not quiet:
                OutputMessage("Selected setup block %s not present in the file (%s).\n Reverting to %s instead!" % (selected_block, setup_file_path, fallback), 'warning')
            # The current block was not found... revert to the fallback
            return self.override_block(fallback)

        # If the selected block is type=HPC, take care of HPC initialization
        if self.get('type') == "HPC":
            try:
                os.environ['COMPS_REST_HOST'] = self.get('server_endpoint')
                from pyCOMPS import pyCOMPS

            except ImportError:
                print('Failed loading pyCOMPS package; you will only be able to run local simulations.')

            except KeyError:
                print('Unable to determine JAVA_HOME; please set JAVA_HOME environment variable as described in pyCOMPS README.txt')

        # Validate
        self.validate()

    def override_block(self,block):
        """
        Overrides the selected block.
        Basically call the constructor with force=True
        :param block: New block we want to use
        """
        self.__init__(selected_block=block, force=True)

    def overlay_setup(self,cp):
        """
        Overlays a ConfigParser on the current self.setup ConfigParser
        :param cp: The ConfigParser to overlay
        """
        # If the cp doesnt have the selected block, no need of overlaying
        if not cp.has_section(self.selected_block):
            return

        # If the current section doesnt exist in the current setup ->create it
        if not self.setup.has_section(self.selected_block):
            # Create the section
            self.setup.add_section(self.selected_block)

            # Depending on the type grab the default from HPC or LOCAL
            for item in self.setup.items(cp.get(self.selected_block,'type')):
                self.setup.set(self.selected_block, item[0], item[1])

        # Go through all the parameters of the cp for the selected_block and overlay them to the current section
        for item in cp.items(self.selected_block):
            self.setup.set(self.selected_block,item[0], item[1])

    def get(self, parameter):
        if not self.has_option(parameter):
            raise ValueError("%s block does not have the option %s!" % (self.selected_block, parameter))
        return self.setup.get(self.selected_block,parameter)

    def has_option(self,option):
        return self.setup.has_option(self.selected_block,option)

    def set(self, parameter, value):
        self.setup.set(self.selected_block, parameter, value)

    def items(self):
        return self.setup.items(self.selected_block)

    def getboolean(self, param):
        return self.setup.getboolean(self.selected_block, param)

    def load_schema(self):
        json_schema = json.load(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config_schema.json")))
        self.schema = json_schema
        return json_schema

    def file_name(self):
        return self.ini_file

    def validate(self):
        pass

