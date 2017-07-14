
from dtk.vector.species import set_larval_habitat, set_species_param, set_params_by_species
from dtk.interventions.input_EIR import add_InputEIR
from dtk.interventions.mosquito_release import add_mosquito_release
from dtk.interventions.itn import add_ITN
from dtk.interventions.irs import add_node_IRS
from dtk.interventions.outbreakindividual import recurring_outbreak
from dtk.interventions.migrate_to import add_migration_event
from dtk.interventions.health_seeking import add_health_seeking

import json
import numpy as np

def config_setup_fn(duration=21915):
    return lambda cb: cb.update_params({'Simulation_Duration' : duration,
                                        'Infection_Updates_Per_Timestep' : 8})

# reporters
def summary_report_fn(start=1,interval=365,nreports=2000,age_bins=[1000],description='Annual_Report', nodes={"class": "NodeSetAll"}):
    from malaria.reports.MalariaReport import add_summary_report
    return lambda cb: add_summary_report(cb, start=start, interval=interval, nreports=nreports, description=description,age_bins=age_bins, nodes=nodes)

def survey_report_fn(days,interval=10000,nreports=1):
    from malaria.reports.MalariaReport import add_survey_report
    return lambda cb: add_survey_report(cb,survey_days=days,reporting_interval=interval,nreports=nreports)

def filtered_report_fn(start, end, nodes, description=''):
    from malaria.reports.MalariaReport import add_filtered_report
    return lambda cb: add_filtered_report(cb, start=start, end=end, nodes=nodes, description=description)

# vector
def larval_habitat_fn(species, habitats) :
    return lambda cb: set_larval_habitat(cb, {species : habitats})

def species_param_fn(species, param, value) :
    return lambda cb : set_species_param(cb, species, param, value)

def set_params_by_species_fn(species) :
    return lambda cb : set_params_by_species(cb.params, species, 'MALARIA_SIM')

# immune overlays
def add_immunity_fn(tags):
    from malaria.immunity import add_immune_overlays
    return lambda cb: add_immune_overlays(cb,tags=tags)

# input EIR
def site_input_eir_fn(site,birth_cohort=True, set_site_geography=False):
    from malaria.site.input_EIR_by_site import configure_site_EIR
    return lambda cb: configure_site_EIR(cb,site=site,birth_cohort=birth_cohort, set_site_geography=False)

def input_eir_fn(monthlyEIRs, start_day=0, nodes={"class": "NodeSetAll"}):
    return lambda cb: add_InputEIR(cb,monthlyEIRs, start_day=start_day, nodes=nodes)

# importation pressure
def add_outbreak_fn(start_day=0, outbreak_fraction=0.01, repetitions=-1, tsteps_btwn=365, nodes={"class": "NodeSetAll"}) :
    return lambda cb: recurring_outbreak(cb, outbreak_fraction=outbreak_fraction, repetitions=repetitions, tsteps_btwn=tsteps_btwn, start_day=start_day, nodes=nodes)

# migration
def add_migration_fn(nodeto, start_day=0, coverage=1, repetitions=1, tsteps_btwn=365,
                     duration_at_node_distr_type='FIXED_DURATION',
                     duration_of_stay=100, duration_of_stay_2=0,
                     duration_before_leaving_distr_type='FIXED_DURATION',
                     duration_before_leaving=0, duration_before_leaving_2=0,
                     target='Everyone', nodesfrom={"class": "NodeSetAll"}) :
    return lambda cb : add_migration_event(cb, nodeto, start_day=start_day, coverage=coverage, repetitions=repetitions, 
                                           tsteps_btwn=tsteps_btwn,
                                           duration_at_node_distr_type=duration_at_node_distr_type,
                                           duration_of_stay=duration_of_stay,
                                           duration_of_stay_2=duration_of_stay_2,
                                           duration_before_leaving_distr_type=duration_before_leaving_distr_type,
                                           duration_before_leaving=duration_before_leaving,
                                           duration_before_leaving_2=duration_before_leaving_2,
                                           target=target, nodesfrom=nodesfrom)


# mosquito release
def add_mosquito_release_fn(start_day, vector_species, number_vectors, repetitions=-1, tsteps_btwn=365, nodes={"class": "NodeSetAll"}) :
    return lambda cb : add_mosquito_release(cb, start_day, vector_species, number_vectors, repetitions=repetitions, tsteps_btwn=tsteps_btwn, nodes=nodes)


# health-seeking
def add_treatment_fn(start=0,drug=['Artemether', 'Lumefantrine'],targets=[{'trigger':'NewClinicalCase','coverage':0.8,'seek':0.6,'rate':0.2}],nodes={"class": "NodeSetAll"}):
    def fn(cb,start=start,drug=drug,targets=targets):
        add_health_seeking(cb,start_day=start,drug=drug,targets=targets, nodes=nodes)
        cb.update_params({'PKPD_Model': 'CONCENTRATION_VERSUS_TIME'})
    return fn


# health-seeking from nodeid-coverage specified in json
def add_HS_by_node_id_fn(reffname, start=0) :        
    def fn(cb) :
        with open(reffname) as fin :
            cov = json.loads(fin.read())
        for hscov in cov['hscov'] :
            targets = [ { 'trigger': 'NewClinicalCase', 'coverage': 1, 'agemin':15, 'agemax':200, 'seek': hscov['coverage'], 'rate': 0.3 },
                        { 'trigger': 'NewClinicalCase', 'coverage': 1, 'agemin':0, 'agemax':15, 'seek':  min([1, hscov['coverage']*1.5]), 'rate': 0.3 },
                        { 'trigger': 'NewSevereCase',   'coverage': 1, 'seek': 0.8, 'rate': 0.5 } ]
            add_health_seeking(cb, start_day = start, targets=targets, nodes={'Node_List' : hscov['nodes'], "class": "NodeSetNodeList"})
    return fn

# seasonal health-seeking from nodeid-coverage specified in json
def add_seasonal_HS_by_node_id_fn(reffname, days_in_month, scale_by_month, start=0) :

    def fn(cb) :
        with open(reffname) as fin :
            cov = json.loads(fin.read())
        for hscov in cov['hscov'] :
            ad_cov = hscov['coverage']
            kid_cov = min([1, hscov['coverage']*1.5])
            sev_cov = 0.8

            for start_month in range(len(scale_by_month)) :
                start_day = start+np.cumsum(days_in_month)[start_month]
                duration = days_in_month[start_month+1]

                scale = scale_by_month[start_month]
                targets = [
                    {'trigger': 'NewClinicalCase', 'coverage': 1, 'agemin': 15, 'agemax': 200,
                     'seek': min([1, ad_cov*scale]), 'rate': 0.3},
                    {'trigger': 'NewClinicalCase', 'coverage': 1, 'agemin': 0, 'agemax': 15,
                     'seek': min([1, kid_cov*scale]), 'rate': 0.3},
                    {'trigger': 'NewSevereCase', 'coverage': 1,
                     'seek': min([1, max([sev_cov*scale, kid_cov*scale])]), 'rate': 0.5}]

                add_health_seeking(cb, start_day=start_day, targets=targets,
                                   duration=duration, repetitions=-1,
                                   nodes={'Node_List' : hscov['nodes'], "class": "NodeSetNodeList"})
    return fn


# ITNs
def add_itn_fn(start=0, coverage=1, waning={}, nodeIDs=[]) :
    def fn(cb) :
        coverage_by_age = { 'min' : 0, 'max' : 200, 'coverage' : coverage}
        add_ITN(cb, start=start, coverage_by_ages=[coverage_by_age], waning=waning, nodeIDs=nodeIDs)
    return fn


# ITNs from nodeid-coverage specified in json
def add_itn_by_node_id_fn(reffname, itn_dates, itn_fracs, channel='itn2012cov', waning={}) :
    def fn(cb) :
        birth_durations = [itn_dates[x + 1] - itn_dates[x] for x in range(len(itn_dates)-1)]
        itn_distr = zip(itn_dates[:-1], itn_fracs)
        with open(reffname) as fin :
            cov = json.loads(fin.read())
        for itncov in cov[channel] :
            if itncov['coverage'] > 0 :
                for i, (itn_date, itn_frac) in enumerate(itn_distr) :
                    c = itncov['coverage']*itn_frac
                    if i < len(itn_fracs)-1 :
                        c /= np.prod([1 - x*itncov['coverage'] for x in itn_fracs[i+1:]])
                    # coverage = { 'min' : 0, 'max' : 200, 'coverage' : c}
                    add_ITN(cb, itn_date,
                            coverage_by_ages=[{'min': 0, 'max': 5, 'coverage': min([1,c*1.3])},
                                              {'birth': 1, 'coverage': min([1,c*1.3]), 'duration': max([-1, birth_durations[i]])},
                                              {'min': 5, 'max': 20, 'coverage': c / 2},
                                              {'min': 20, 'max': 100, 'coverage': min([1,c*1.3])}],
                            waning=waning, nodeIDs=itncov['nodes'])
    return fn


# IRS from nodeid-coverage specified in json
def add_node_level_irs_by_node_id_fn(reffname, irs_dates, irs_fracs, channel='irs2012cov',
                                     initial_killing=0.5, box_duration=90) :
    def fn(cb) :
        nodelist = {x: [] for x in irs_dates}

        irs_distr = zip(irs_dates, irs_fracs)
        with open(reffname) as fin:
            cov = json.loads(fin.read())
        for irscov in cov[channel]:
            if irscov['coverage'] > 0:
                for i, (irs_date, irs_frac) in enumerate(irs_distr):
                    c = irscov['coverage'] * irs_frac
                    if i < len(irs_fracs) - 1:
                        c /= np.prod([1 - x * irscov['coverage'] for x in irs_fracs[i + 1:]])
                    nodeIDs = [x for x in irscov['nodes'] if np.random.random() <= c]
                    nodelist[irs_date] += nodeIDs

        for i, (irs_date, irs_frac) in enumerate(irs_distr):
            if len(nodelist[irs_date]) > 0 :
                add_node_IRS(cb, irs_date, initial_killing=initial_killing,
                             box_duration=box_duration, nodeIDs=nodelist[irs_date])

    return fn


# drug campaign
def add_drug_campaign_fn(campaign_type, drug_code, start_days, coverage=1.0, repetitions=3,
                         interval=60, diagnostic_threshold=40,
                         snowballs=0, delay=0, nodes=[], target_group='Everyone') :
    from malaria.interventions.malaria_drug_campaigns import add_drug_campaign
    return lambda cb : add_drug_campaign(cb, campaign_type, drug_code, start_days=start_days, coverage=coverage,
                                         repetitions=repetitions, interval=interval,
                                         diagnostic_threshold=diagnostic_threshold,
                                         snowballs=snowballs, delay=delay, nodes=nodes, target_group=target_group)