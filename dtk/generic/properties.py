import os
import json
import getpass
import datetime

from dtk.utils.core.DTKSetupParser import DTKSetupParser

def set_property(property, values, initial):
    '''
    For example:
    set_property('Accessibility', ['Easy', 'Hard'], [0.5, 0.5])
    '''
    return {'Property': property, 'Values': values, 'Initial_Distribution': initial, 'Transitions': []}

def init_access(**kwargs):
    '''
    For example:
    init_access(Easy=0.5, Hard=0.5)
    '''
    return set_property('Accessibility', kwargs.keys(), kwargs.values())

def add_properties_overlay(cb, properties, directory=DTKSetupParser().get('LOCAL','input_root'), tag=''):

    filenames = cb.get_param('Demographics_Filenames')
    demogfiles = [f for f in filenames if 'demographics' in f]

    if len(demogfiles) != 1:
        print(demogfiles)
        raise Exception('add_properties_overlay function is expecting exactly one base demographics file.')

    demog_filename = demogfiles[0]

    if not os.path.exists(os.path.join(directory, demog_filename)):
        raise OSError('No demographics file %s in local input directory %s' % (demog_filename, directory))

    with open(os.path.join(directory, demog_filename)) as f:
        j = json.loads(f.read())

    metadata = j['Metadata']
    metadata.update({'Author': getpass.getuser(),
                     'DateCreated': datetime.datetime.now().strftime('%a %b %d %X %Y'),
                     'Tool': os.path.basename(__file__)})

    overlay_content = {'Metadata': metadata,
                       'Defaults': {'IndividualProperties': properties},
                       'Nodes': [{'NodeID': n['NodeID']} for n in j['Nodes']]}

    prefix = demog_filename.split('.')[0]
    immune_init_name = prefix.replace('demographics', 'properties' + tag, 1)
    cb.add_demog_overlay(os.path.basename(immune_init_name), overlay_content)
    cb.enable('Property_Output')