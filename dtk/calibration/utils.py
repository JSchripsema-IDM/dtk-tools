#####################################################################
# utils.py
#
# Helpful utility functions
#
# write_to_file()
#
# update_settings()
#
# clean_directory()
#
# check_for_done()
# cleanup()
#####################################################################


import json
import os
import time
from collections import Counter

import pandas as pd
import math

from dtk.commands import reload_experiment


def concat_likelihoods(settings) :

    df = pd.DataFrame()
    for i in range(settings['max_iterations']) :
        try :
            LL = pd.read_csv(os.path.join(settings['exp_dir'] ,'iter' + str(i),'LL.csv'))
            LL['iteration'] = pd.Series([i]*len(LL.index))
            df = pd.concat([df, LL])
        except IOError :
            break
    write_to_file(df, os.path.join(settings['exp_dir'],'LL_all.csv'))

def write_to_file(samples, outstem) :
    samples.to_csv(outstem, index=False)

def update_settings(settings, iteration) :

    settings['curr_iteration_dir'] = os.path.join(settings['exp_dir'], 'iter' + str(iteration))
    settings['prev_iteration_dir'] = os.path.join(settings['exp_dir'], 'iter' + str(iteration-1))
    try :
        os.mkdir(settings['curr_iteration_dir'])
    except OSError :
        pass

    return settings

def clean_directory(settings) :

    this_dir = settings['curr_iteration_dir']
    sites = settings['sites'].keys()

    try :
        os.remove(this_dir + 'params.json')
        os.remove(this_dir + 'exp')
        os.remove(this_dir + 'params_withpaths.json')
        os.remove(this_dir + 'params_withpaths.txt')
        for site in sites :
            os.remove(this_dir + 'parsed_' + site + '.json')
        os.remove(this_dir + 'LL.json')
        os.remove(this_dir + 'LL.txt')

    except OSError :
        pass

def check_for_done(settings, sleeptime=0) :
    # First get the experiment id with the sim.json file contained in the current iteration
    with open(os.path.join(settings['curr_iteration_dir'],'sim.json')) as fin :
        sim = json.loads(fin.read())

    exp_id = sim['exp_name'] + '_' + sim['exp_id']
    sim_count = len(sim["sims"])

    # If we want to wait => wait
    if sleeptime > 0 :
        time.sleep(sleeptime)
        return

    start_time = time.time()
    start_run_time = -1

    while True :
        args = type('obj', (object,), {'expId' : exp_id})

        # Reset the count
        new_status = { 'Commissioned' : 0, 'Running' : 0, 'Succeeded' : 0, 'Failed' : 0,
               'Canceled' : 0, 'Created' : 0, 'CommissionRequested' : 0,
               'Provisioning' : 0, 'Retry' : 0, 'CancelRequested' : 0,
               'Finished' : 0, 'Waiting' : 0}

        # set new_status with the data coming from the simulation status
        sm = reload_experiment(args)
        states, msgs = sm.get_simulation_status()
        states_dict =  dict(Counter(states.values()))
        for (status,number) in states_dict.iteritems():
            new_status[status] = number

        # If we have as many simulations done (failed, cancel, succeeded or finished) than total simulations => exit the loop
        if new_status['Succeeded'] + new_status['Failed'] + new_status['Canceled'] + new_status['Finished'] ==  sim_count:
            break

        # Update the time and the count of simulations
        curr_time = time.time() - start_time
        new_status['Finished'] = new_status['Succeeded'] + new_status['Failed'] + new_status['Canceled'] + new_status['Finished']
        new_status['Waiting'] = new_status['Commissioned'] + new_status['CommissionRequested'] + new_status['Provisioning']

        if start_run_time < 0 and new_status['Finished'] + new_status['Running'] > 0 :
            start_run_time = curr_time

        # Display
        print 'time since submission: ', int(curr_time/60),
        print 'time_since running began: ', int((curr_time - start_run_time)/60)
        print 'Running: ' + str(new_status['Running']),
        print 'Waiting: ' + str(new_status['Waiting']),
        print 'Finished: ' + str(new_status['Finished'])

        # Wait a certain time
        time.sleep(get_sleep_time(new_status, sim_count, curr_time, start_run_time))


def get_sleep_time(status, numsims, curr_time, start_run_time) :

    if status['Waiting'] == numsims :
        return min([max([60, curr_time*2]), 300])
    if status['Running'] < 0.5*numsims :
        return min([max([60, start_run_time*2]), 300])
    if (status['Finished']) > 0 :
        return min([60, 10*status['Running']])

    return 60

def calc_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    km = 6371 * c
    return km

def latlon_to_anon(lats, lons, reflat=0, reflon=0) :

    if reflat == 0 or reflon == 0 :
        reflat = lats[0]
        reflon = lons[0]

    ycoord = [calc_distance(x, reflon, reflat, reflon) for x in lats]
    xcoord = [calc_distance(reflat, x, reflat, reflon) for x in lons]
    for i in range(len(lats)) :
        if lats[i] < reflat :
            ycoord[i] *= -1
        if lons[i] < reflon :
            xcoord[i] *= -1
    midx = (max(xcoord) + min(xcoord))/2
    midy = (max(ycoord) + min(ycoord))/2
    xcoord = [x - midx for x in xcoord]
    ycoord = [x - midy for x in ycoord]

    return xcoord, ycoord
