import random

from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event

# the old MigrateTo has now been split into MigrateIndividuals and MigrateFamily.
# add_migration_event adds a MigrateIndividuals event.
def add_migration_event(cb, nodeto, start_day=0, coverage=1, repetitions=1, tsteps_btwn=365,
                        duration_at_node_distr_type='FIXED_DURATION', 
                        duration_of_stay=100, duration_of_stay_2=0, 
                        duration_before_leaving_distr_type='FIXED_DURATION', 
                        duration_before_leaving=0, duration_before_leaving_2=0, 
                        target='Everyone', nodesfrom={"class": "NodeSetAll"},
                        ind_property_restrictions=[], node_property_restrictions=[], triggered_campaign_delay=0,
                        trigger_condition_list=[], listening_duration=-1) :
    migration_event ={
                "class": "MigrateIndividuals",
                "NodeID_To_Migrate_To": nodeto,
                "Is_Moving" : 0 }

    migration_event = update_duration_type(migration_event, duration_at_node_distr_type,
                                           dur_param_1=duration_of_stay, dur_param_2=duration_of_stay_2,
                                           leaving_or_at='at')
    migration_event = update_duration_type(migration_event, duration_before_leaving_distr_type,
                                           dur_param_1=duration_before_leaving, dur_param_2=duration_before_leaving_2,
                                           leaving_or_at='leaving')

    if trigger_condition_list:
            event_to_send_out = random.randrange(100000)
            for x in range(repetitions):
                # create a trigger for each of the delays.
                trigger_condition_list = [str(triggered_campaign_delay_event(cb, start_day, nodesfrom,
                                                                                 triggered_campaign_delay + x * tsteps_btwn,
                                                                                 trigger_condition_list,
                                                                                 listening_duration, event_to_send_out))]
            event = {
                        "Event_Name": "Migration Event Triggered",
                        "class": "CampaignEvent",
                        "Start_Day": start_day,
                        "Event_Coordinator_Config": {
                            "class": "StandardInterventionDistributionEventCoordinator",
                            "Intervention_Config":
                                {
                                    "class": "NodeLevelHealthTriggeredIV",
                                    "Duration": listening_duration,
                                    "Trigger_Condition_List": trigger_condition_list,
                                    "Target_Demographic": target,
                                    "Target_Residents_Only": 1,
                                    "Node_Property_Restrictions": node_property_restrictions,
                                    "Property_Restrictions_Within_Node": ind_property_restrictions,
                                    "Demographic_Coverage": coverage,
                                    "Actual_IndividualIntervention_Config":migration_event
                                 }
                            },
                        "Nodeset_Config": nodesfrom
                        }

            if isinstance(target, dict) and all([k in target for k in ['agemin', 'agemax']]):
                event["Event_Coordinator_Config"]["Intervention_Config"].update({
                    "Target_Demographic": "ExplicitAgeRanges",
                    "Target_Age_Min": target['agemin'],
                    "Target_Age_Max": target['agemax']})

            cb.add_event(event)

    else:
        event = { "Event_Name": "Migration Event",
                            "class": "CampaignEvent",
                            "Start_Day": start_day,
                            "Event_Coordinator_Config": {
                                "class": "StandardInterventionDistributionEventCoordinator",
                                "Property_Restrictions_Within_Node": ind_property_restrictions,
                                "Node_Property_Restrictions": node_property_restrictions,
                                "Number_Distributions": -1,
                                "Number_Repetitions": repetitions,
                                "Target_Residents_Only" : 1,
                                "Target_Demographic": target,
                                "Timesteps_Between_Repetitions": tsteps_btwn,
                                "Demographic_Coverage": coverage,
                                "Intervention_Config": migration_event
                                },
                            "Nodeset_Config": nodesfrom
                            }

        if isinstance(target, dict) and all([k in target for k in ['agemin','agemax']]) :
            event["Event_Coordinator_Config"].update({
                    "Target_Demographic": "ExplicitAgeRanges",
                    "Target_Age_Min": target['agemin'],
                    "Target_Age_Max": target['agemax'] })

        cb.add_event(event)


def update_duration_type(migration_event, duration_at_node_distr_type, dur_param_1=0, dur_param_2=0, leaving_or_at='at') :

    if leaving_or_at == 'leaving' :
        trip_end = 'Before_Leaving'
    else:
        trip_end = 'At_Node'

    if duration_at_node_distr_type == 'FIXED_DURATION' :
        migration_event["Duration_" + trip_end + "_Distribution_Type"] = "FIXED_DURATION"
        migration_event["Duration_" + trip_end + "_Fixed"] = dur_param_1
    elif duration_at_node_distr_type == 'UNIFORM_DURATION' :
        migration_event["Duration_" + trip_end + "_Distribution_Type"] = "UNIFORM_DURATION"
        migration_event["Duration_" + trip_end + "_Uniform_Min"] = dur_param_1
        migration_event["Duration_" + trip_end + "_Uniform_Max"] = dur_param_2
    elif duration_at_node_distr_type == 'GAUSSIAN_DURATION' :
        migration_event["Duration_" + trip_end + "_Distribution_Type"] = "GAUSSIAN_DURATION"
        migration_event["Duration_" + trip_end + "_Gausian_Mean"] = dur_param_1
        migration_event["Duration_" + trip_end + "_Gausian_StdDev"] = dur_param_2
    elif duration_at_node_distr_type == 'EXPONENTIAL_DURATION' :
        migration_event["Duration_" + trip_end + "_Distribution_Type"] = "EXPONENTIAL_DURATION"
        migration_event["Duration_" + trip_end + "_Exponential_Period"] = dur_param_1
    elif duration_at_node_distr_type == 'POISSON_DURATION' :
        migration_event["Duration_" + trip_end + "_Distribution_Type"] = "POISSON_DURATION"
        migration_event["Duration_" + trip_end + "_Poisson_Mean"] = dur_param_1
    else :
        print("warning: unsupported duration distribution type, reverting to fixed duration")
        migration_event["Duration_" + trip_end + "_Distribution_Type"] = "FIXED_DURATION"
        migration_event["Duration_" + trip_end + "_Fixed"] = dur_param_1

    return migration_event
