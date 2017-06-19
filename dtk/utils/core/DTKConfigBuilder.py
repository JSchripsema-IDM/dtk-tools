import json
import os
import re  # find listed events by regex

import dtk.dengue.params as dengue_params
import dtk.generic.params as generic_params
import dtk.generic.seir as seir_params
import dtk.generic.seir_vitaldynamics as seir_vitaldynamics_params
import dtk.generic.seirs as seirs_params
import dtk.generic.si as si_params
import dtk.generic.sir as sir_params
import dtk.generic.sir_vaccinations_a as sir_vaccinations_a_params
import dtk.generic.sir_vaccinations_b as sir_vaccinations_b_params
import dtk.generic.sir_vaccinations_c as sir_vaccinations_c_params
import dtk.generic.sirs as sirs_params
import dtk.generic.sis as sis_params
import dtk.malaria.params as malaria_params
import dtk.vector.params as vector_params
from dtk.interventions.empty_campaign import empty_campaign
from dtk.interventions.seir_initial_seeding import seir_campaign
from dtk.interventions.seir_vitaldynamics import seir_vitaldynamics_campaign
from dtk.interventions.seirs import seirs_campaign
from dtk.interventions.si_initial_seeding import si_campaign
from dtk.interventions.sir_initial_seeding import sir_campaign
from dtk.interventions.sir_vaccinations_a_initial_seeding import sir_vaccinations_a_campaign
from dtk.interventions.sir_vaccinations_b_initial_seeding import sir_vaccinations_b_campaign
from dtk.interventions.sir_vaccinations_c_initial_seeding import sir_vaccinations_c_campaign
from dtk.interventions.sirs_initial_seeding import sirs_campaign
from dtk.interventions.sis_initial_seeding import sis_campaign
from dtk.utils.parsers.JSON import json2dict
from dtk.utils.reports.CustomReport import format as format_reports
from simtools.SimConfigBuilder import SimConfigBuilder
from simtools.Utilities.Encoding import NumpyEncoder
from simtools.Utilities.General import init_logging

logger = init_logging('ConfigBuilder')


class DTKConfigBuilder(SimConfigBuilder):
    """
    A class for building, modifying, and writing
    required configuration files for a DTK simulation.

    There are four ways to create a DTKConfigBuilder:

    1. From a set of defaults, with the :py:func:`from_defaults` class method.
    2. From existing files, with the :py:func:`from_files` class method.
    3. From a default config/campaign by calling the constructor without arguments.
    4. From a custom config and/or campaign by calling the constructor with the ``config`` and ``campaign`` arguments.

    Arguments:
        config (dict): The config (contents of the config.json)
        campaign (dict): The campaign configuration (contents of the campaign.json)
        kwargs (dict): Additional changes to make to the config

    Attributes:
        staged_dlls (dict): Class variable holding the mapping between (type,dll name) and path
        config (dict): Holds the configuration as a dictionary
        campaign (dict): Holds the campaign as a dictionary
        demog_overlays (dict): map the demographic overlay names to content.
            Modified using the function :py:func:`add_demog_overlay`.
        input_files (dict): Dictionary map the input file names to content.
            Modified using the function :py:func:`add_input_file`.
        custom_reports (array): Array holding the custom reporters objects.
            Modified using the function :py:func:`add_reports`.
        dlls (set): Set containing a list of needed dlls for the simulations. The dlls are coming from the
            :py:func:`get_dll_path` function of the reports added by the :py:func:`add_reports`
        emodules_map (dict): Dictionary representing the ``emodules_map.json`` file.
            This dictionary is filled during the staging process happening in :py:func:`stage_required_libraries`.

    Examples:
        One can instantiate a DTKConfigBuilder with::

            config = json.load('my_config.json')
            cb = DTKConfigBuilder(config=config, campaign=None, {'Simulation_Duration':3650})

        Which will instantiate the DTKConfigBuilder with the loaded config and a default campaign and override the
        ``Simulation_Duration`` in the config.

    """

    staged_dlls = {}  # caching to avoid repeat md5 and os calls

    def __init__(self, config=None, campaign=empty_campaign, **kwargs):
        self.config = config or {'parameters': {}}
        self.campaign = campaign
        # Indent the files when dumping or not
        self.human_readability = True
        self.demog_overlays = {}
        self.input_files = {}
        self.custom_reports = []
        self.dlls = set()
        self.emodules_map = {'interventions': [],
                             'disease_plugins': [],
                             'reporter_plugins': []}
        self.update_params(kwargs, validate=True)
        self.assets = None

    @classmethod
    def from_defaults(cls, sim_type=None, **kwargs):
        """
        Build up the default parameters for the specified simulation type.

        Start from required ``GENERIC_SIM`` parameters and layer ``VECTOR_SIM``
        and also ``MALARIA_SIM`` default parameters as required.

        Configuration parameter names and values may be passed as keyword arguments,
        provided they correspond to existing default parameter names.

        P.vivax disease parameters may be approximated using ``VECTOR_SIM`` simulations
        by passing either the ``VECTOR_SIM_VIVAX_SEMITROPICAL`` or ``VECTOR_SIM_VIVAX_CHESSON``
        sim_type argument depending on the desired relapse pattern.

        Attributes:
            sim_type (string): Which simulation will be created.
                Current supported choices are:

                * MALARIA_SIM
                * VECTOR_SIM
                * VECTOR_SIM_VIVAX_SEMITROPICAL
                * VECTOR_SIM_VIVAX_CHESSON
                * GENERIC_SIM_SIR
                * GENERIC_SIM_SIR_Vaccinations_A
                * GENERIC_SIM_SIR_Vaccinations_B
                * GENERIC_SIM_SIR_Vaccinations_C
                * GENERIC_SIM_SEIR
                * GENERIC_SIM_SEIR_VitalDynamics
                * GENERIC_SIM_SIRS
                * GENERIC_SIM_SEIRS
                * GENERIC_SIM_SI
                * GENERIC_SIM_SIS
                * DENGUE_SIM


            kwargs (dict): Additional overrides of config parameters
        """

        if not sim_type:
            raise Exception(
                "Instantiating DTKConfigBuilder from defaults requires a sim_type argument, e.g. 'MALARIA_SIM'.")

        config = {"parameters": generic_params.params}
        campaign = empty_campaign

        if sim_type == "MALARIA_SIM":
            config["parameters"].update(vector_params.params)
            config["parameters"].update(malaria_params.params)

        elif sim_type == "VECTOR_SIM":
            config["parameters"].update(vector_params.params)

        elif sim_type == "VECTOR_SIM_VIVAX_SEMITROPICAL":
            config["parameters"].update(vector_params.params)
            config["parameters"].update(vector_params.vivax_semitropical_params)
            sim_type = "VECTOR_SIM"

        elif sim_type == "VECTOR_SIM_VIVAX_CHESSON":
            config["parameters"].update(vector_params)
            config["parameters"].update(vector_params.vivax_chesson_params)
            sim_type = "VECTOR_SIM"

        elif sim_type == "GENERIC_SIM_SIR":
            config["parameters"].update(sir_params.params)
            campaign = sir_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SIR_Vaccinations_A":
            config["parameters"].update(sir_vaccinations_a_params.params)
            campaign = sir_vaccinations_a_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SIR_Vaccinations_B":
            config["parameters"].update(sir_vaccinations_b_params.params)
            campaign = sir_vaccinations_b_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SIR_Vaccinations_C":
            config["parameters"].update(sir_vaccinations_c_params.params)
            campaign = sir_vaccinations_c_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SEIR":
            config["parameters"].update(seir_params.params)
            campaign = seir_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SEIR_VitalDynamics":
            config["parameters"].update(seir_vitaldynamics_params.params)
            campaign = seir_vitaldynamics_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SIRS":
            config["parameters"].update(sirs_params.params)
            campaign = sirs_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SEIRS":
            config["parameters"].update(seirs_params.params)
            campaign = seirs_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SI":
            config["parameters"].update(si_params.params)
            campaign = si_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "GENERIC_SIM_SIS":
            config["parameters"].update(sis_params.params)
            campaign = sis_campaign
            sim_type = "GENERIC_SIM"

        elif sim_type == "DENGUE_SIM":
            config["parameters"].update(vector_params.params)
            config["parameters"].update(dengue_params.params)
            # campaign = dengue_campaign

        else:
            raise Exception("Don't recognize sim_type argument = %s" % sim_type)

        config["parameters"]["Simulation_Type"] = sim_type

        return cls(config, campaign, **kwargs)

    @classmethod
    def from_files(cls, config_name, campaign_name=None, **kwargs):
        """
        Build up a simulation configuration from the path to an existing
        config.json and optionally a campaign.json file on disk.

        Attributes:
            config_name (string): Path to the config file to load.
            campaign_name (string): Path to the campaign file to load.
            kwargs (dict): Additional overrides of config parameters
        """

        config = json2dict(config_name)
        campaign = json2dict(campaign_name) if campaign_name else empty_campaign

        return cls(config, campaign, **kwargs)

    @property
    def params(self):
        """
        dict: Shortcut to the ``config['parameters']``
        """
        return self.config['parameters']

    def get_input_file_paths(self):
        params_dict = self.config['parameters']
        file_dict = {filename: filepath for (filename, filepath) in params_dict.iteritems()
                      if filename.endswith('_Filename') or filename.startswith('Filename_') or '_Filename_' in filename
                      or filename.endswith('_Filenames') or filename.startswith('Filenames_') or '_Filenames_' in filename}

        return file_dict

    def enable(self, param):
        """
        Enable a parameter.

        Arguments:
            param (string): Parameter to enable. Note that the ``Enable_`` part of the name is automatically added.

        Examples:
            If one wants to set the ``Enable_Air_Migration`` parameter to ``1``, the way to do it would be::

                cb.enable('Air_Migration')
        """
        param = 'Enable_' + param
        self.validate_param(param)
        self.set_param(param, 1)

    def disable(self, param):
        """
        Disable a parameter.

        Arguments:
            param (string): Parameter to disable. Note that the ``Enable_`` part of the name is automatically added.

        Examples:
            If one wants to set the ``Enable_Demographics_Birth`` parameter to ``0``, the way to do it would be::

                cb.disable('Demographics_Birth')
        """
        param = 'Enable_' + param
        self.validate_param(param)
        self.set_param(param, 0)

    def add_event(self, event):
        """
        Add an event to the campaign held by the config builder.

        Args:
            event (dict): The dictionary holding the event to be added.

        Examples:
            To add an event to an existing config builder, one can do::

                event = {
                    "Event_Coordinator_Config": {
                        "Intervention_Config": {
                            [...]
                        },
                        "Number_Repetitions": 1,
                        "class": "StandardInterventionDistributionEventCoordinator"
                    },
                    "Event_Name": "Input EIR intervention",
                    [...]
                    }

                cb.add_event(event)

        """
        self.campaign["Events"].append(event)

    def clear_events(self):
        """
        Removes all events from the campaign
        """
        self.campaign["Events"] = []

    def add_reports(self, *reports):
        """
        Add the reports to the ``custom_reports`` dictionary. Also extract the required dlls and add them to the
        ``dlls`` set.

        Args:
            reports (list): List of reports to add to the config builder
        """
        for r in reports:
            self.custom_reports.append(r)
            dll_type, dll_path = r.get_dll_path()
            self.dlls.add((dll_type, dll_path))

            # path relative to dll_root, will be expanded before emodules_map.json is written
            self.emodules_map[dll_type].append(os.path.join(dll_type, dll_path))

    def add_input_file(self, name, content):
        """
        Add input file to the simulation.
        The file can be of any type.

        Args:
            name (string): Name of the file. Will be used when the file is written to the simulation directory.
            content (string): Contents of the file.

        Examples:
            Usage for this function could be::

                my_txt = open('test.txt', 'r')
                cb.add_input_file('test.txt',my_txt.read())

        """
        if name in self.input_files:
            logger.warn('Already have input file named %s, replacing previous input file.' % name)
        self.input_files[name] = content

    def append_overlay(self, demog_file):
        """
        Append a demographic overlay at the end of the ``Demographics_Filenames`` array.

        Args:
            demog_file (string): The demographic file name to append to the array.

        """
        self.config['parameters']['Demographics_Filenames'].append(demog_file)

    def prepare_assets(self, location, cache=None):
        self.assets = self.get_assets(cache or {})
        self.assets.prepare(location)

    def get_assets(self, cache=None):
        """
        Returns a SimulationAssets object corresponding to the current simulation.
        """
        from simtools.AssetManager.SimulationAssets import SimulationAssets
        from simtools.SetupParser import SetupParser
        base_collection_id = {}
        use_local_files = {}
        for collection_type in SimulationAssets.COLLECTION_TYPES:
            # Each is either None (no existing collection starting point) or an asset collection id
            base_collection_id[collection_type] = SetupParser.get('base_collection_id' + '_' + collection_type)
            if len(base_collection_id[collection_type]) == 0:
                base_collection_id[collection_type] = None

            # True/False, overlay locally-discovered files on top of any provided asset collection id?
            use_local_files[collection_type] = SetupParser.getboolean('use_local' + '_' + collection_type)

        # Takes care of the logic of knowing which files (remote and local) to use in coming simulations and
        # creating local AssetCollection instances internally to represent them.
        assets = SimulationAssets.assemble_assets(config_builder=self,
                                                  base_collection_id=base_collection_id,
                                                  use_local_files=use_local_files,
                                                  cache=cache)
        return assets

    def add_demog_overlay(self, name, content):
        """
        Add a demographic overlay to the simulation.

        Args:
            name (string): Name of the demographic overlay
            content (string): Content of the file

        """
        if name in self.demog_overlays:
            raise Exception('Already have demographics overlay named %s' % name)
        self.demog_overlays[name] = content

    def get_dll_paths_for_asset_manager(self):
        """
        Generates relative path filenames for the requested dll files, relative to the root dll directory.
        :return:
        """
        return [os.path.join(dll_type, dll_name) for dll_type, dll_name in self.dlls]

    def check_custom_events(self):
        # Return difference between config and campaign

        broadcast_events_from_campaign = re.findall(r"['\"]Broadcast_Event['\"]:\s['\"](.*?)['\"]",
                                                    str(json.dumps(self.campaign)), re.DOTALL)

        event_triggers_from_campaign = re.findall(r"['\"]Event_Trigger['\"]:\s['\"](.*?)['\"]",
                                                  str(json.dumps(self.campaign)), re.DOTALL)

        return list(set(event_triggers_from_campaign + broadcast_events_from_campaign)
                    - set(self.config['parameters']['Listed_Events']))

    def file_writer(self, write_fn):
        """
        Dump all the files needed for the simulation in the simulation directory.
        This includes:

        * The campaign file
        * The custom reporters file
        * The different demographic overlays
        * The other input files (``input_files`` dictionary)
        * The config file
        * The emodules_map file

        Args:
            write_fn: The function that will write the files. This function needs to take a file name and a content.

        Examples:
            For example, in the :py:class:`SimConfigBuilder` class, the :py:func:`dump_files` is defining the `write_fn`
            like::

                def write_file(name, content):
                    filename = os.path.join(working_directory, '%s.json' % name)
                    with open(filename, 'w') as f:
                        f.write(content)
        """
        from simtools.SetupParser import SetupParser

        if self.human_readability:
            dump = lambda content: json.dumps(content, sort_keys=True, indent=3, cls=NumpyEncoder).strip('"')
        else:
            dump = lambda content: json.dumps(content, sort_keys=True, cls=NumpyEncoder).strip('"')

        write_fn(self.config['parameters']['Campaign_Filename'], dump(self.campaign))

        if self.custom_reports:
            self.set_param('Custom_Reports_Filename', 'custom_reports.json')
            write_fn('custom_reports.json', dump(format_reports(self.custom_reports)))

        for name, content in self.demog_overlays.items():
            self.append_overlay('%s.json' % name)
            write_fn('%s.json' % name, dump(content))

        for name, content in self.input_files.items():
            write_fn(name, dump(content))

        # Add missing item from campaign individual events into Listed_Events
        self.config['parameters']['Listed_Events'].extend(self.check_custom_events())

        write_fn('config.json', dump(self.config))

        # complete the path to each dll before writing emodules_map.json
        location = SetupParser.get('type')
        if location == 'LOCAL':
            root = SetupParser.get('dll_root')
        elif location == 'HPC':
            root = 'Assets'
        else:
            raise Exception('Unknown location: %s' % location)
        for module_type in self.emodules_map.keys():
            self.emodules_map[module_type] = [ os.path.join(root, dll) for dll in self.emodules_map[module_type] ]
        write_fn('emodules_map.json', dump(self.emodules_map))
