def add_ATSB(cb, start=0, coverage=0.15, killing_cfg={}, duration=180, duration_std_dev=14,
             repetitions=1, interval=365,
             nodeIDs=[], node_property_restrictions=[]):

    for key, val in killing_cfg.items() :
        val['Initial_Effect'] *= coverage

    atsb_config = {
        "class": "SugarTrap",
        "Cost_To_Consumer": 3.75,
        "Killing_Config": killing_cfg,
        "Expiration_Distribution_Type" : "GAUSSIAN_DURATION",
        "Expiration_Period_Mean" : duration,
        "Expiration_Period_Std_Dev" : duration_std_dev
    }

    ATSB_event = {  "Event_Coordinator_Config": {
                        "Intervention_Config": atsb_config,
                        "class": "StandardInterventionDistributionEventCoordinator"
                    },
                    "Nodeset_Config": {
                        "class": "NodeSetAll"
                    },
                    "Start_Day": start,
                    "Intervention_Name": "Attractive Toxic Sugar Bait",
                    "Demographic_Coverage" : 1,
                    "Number_Repetitions": repetitions,
                    "Timesteps_Between_Repetitions": interval,
                    "Node_Property_Restrictions": node_property_restrictions,
                    "class": "CampaignEvent"
                }

    if nodeIDs:
        ATSB_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

    cb.add_event(ATSB_event)


def add_topical_repellent(config_builder, start, coverage_by_ages, cost=0, initial_blocking=0.95, duration=0.3,
                          repetitions=1, interval=1, nodeIDs=[]):

    repellent = {   "class": "SimpleIndividualRepellent",
                    "Event_Name": "Individual Repellent",
                    "Blocking_Config": {
                        "Initial_Effect": initial_blocking,
                        "Decay_Time_Constant": duration,
                        "class": "WaningEffectBox"
                    },
                    "Cost_To_Consumer": cost
    }

    for coverage_by_age in coverage_by_ages:

        repellent_event = { "class" : "CampaignEvent",
                          "Start_Day": start,
                          "Event_Coordinator_Config": {
                              "class": "StandardInterventionDistributionEventCoordinator",
                              "Target_Residents_Only" : 0,
                              "Demographic_Coverage": coverage_by_age["coverage"],
                              "Intervention_Config": repellent,
                              "Number_Repetitions": repetitions,
                              "Timesteps_Between_Repetitions": interval
                          }
                        }

        if all([k in coverage_by_age.keys() for k in ['min','max']]):
            repellent_event["Event_Coordinator_Config"].update({
                   "Target_Demographic": "ExplicitAgeRanges",
                   "Target_Age_Min": coverage_by_age["min"],
                   "Target_Age_Max": coverage_by_age["max"]})

        if not nodeIDs:
            repellent_event["Nodeset_Config"] = { "class": "NodeSetAll" }
        else:
            repellent_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

        if 'birth' in coverage_by_age.keys() and coverage_by_age['birth']:
            birth_triggered_intervention = {
                "class": "BirthTriggeredIV",
                "Duration": coverage_by_age.get('duration', -1), # default to forever if  duration not specified
                "Demographic_Coverage": coverage_by_age["coverage"],
                "Actual_IndividualIntervention_Config": itn_bednet_w_event #itn_bednet
            }

            repellent_event["Event_Coordinator_Config"]["Intervention_Config"] = birth_triggered_intervention
            repellent_event["Event_Coordinator_Config"].pop("Demographic_Coverage")
            repellent_event["Event_Coordinator_Config"].pop("Target_Residents_Only")

        config_builder.add_event(repellent_event)



def add_ors_node(config_builder, start, coverage=1, initial_killing=0.95, duration=30, cost=0,
                 nodeIDs=[]):

    ors_config = {  "Reduction_Config": {
                        "Decay_Time_Constant": 365, 
                        "Initial_Effect": 0, 
                        "class": "WaningEffectBox"
                    }, 
                    "Habitat_Target": "ALL_HABITATS", 
                    "Cost_To_Consumer": cost, 
                    "Killing_Config": {
                        "Decay_Time_Constant": duration, 
                        "Initial_Effect": initial_killing*coverage, 
                        "class": "WaningEffectExponential"
                    }, 
                    "Spray_Kill_Target": "SpaceSpray_FemalesAndMales", 
                    "class": "SpaceSpraying"
                }

    ORS_event = {   "Event_Coordinator_Config": {
                        "Intervention_Config": ors_config,
                        "class": "NodeEventCoordinator"
                    },
                    "Nodeset_Config": {
                        "class": "NodeSetAll"
                    },
                    "Start_Day": start,
                    "Event_Name": "Outdoor Residual Spray",
                    "class": "CampaignEvent"
                }

    if nodeIDs:
        ORS_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

    config_builder.add_event(ORS_event)


def add_larvicide(config_builder, start, coverage=1, initial_killing=1.0, duration=30, cost=0,
                  habitat_target="ALL_HABITATS", nodeIDs=[]):

    larvicide_config = {  "Blocking_Config": {
                        "Decay_Time_Constant": 365, 
                        "Initial_Effect": 0, 
                        "class": "WaningEffectBox"
                    }, 
                    "Habitat_Target": habitat_target, 
                    "Cost_To_Consumer": cost, 
                    "Killing_Config": {
                        "Decay_Time_Constant": duration, 
                        "Initial_Effect": initial_killing*coverage, 
                        "class": "WaningEffectBox"
                    }, 
                    "class": "Larvicides"
                }

    larvicide_event = {   "Event_Coordinator_Config": {
                        "Intervention_Config": larvicide_config, 
                        "class": "NodeEventCoordinator"
                    }, 
                    "Nodeset_Config": {
                        "class": "NodeSetAll"
                    }, 
                    "Start_Day": start, 
                    "Event_Name": "Larvicide",
                    "class": "CampaignEvent"
                }

    if nodeIDs:
        larvicide_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

    config_builder.add_event(larvicide_event)


def add_eave_tubes(config_builder, start, coverage=1, initial_killing=1.0, killing_duration=180, 
                   initial_blocking=1.0, blocking_duration=730, outdoor_killing_discount=0.3, cost=0,
                   nodeIDs=[]):

    indoor_config = {   "class": "IRSHousingModification",
                        "Killing_Config": {
                            "Decay_Time_Constant": killing_duration,
                            "Initial_Effect": initial_killing, 
                            "class": "WaningEffectExponential"
                        },
                        "Blocking_Config": {
                            "Decay_Time_Constant": blocking_duration, 
                            "Initial_Effect": initial_blocking, 
                            "class": "WaningEffectExponential"
                        },
                        "Cost_To_Consumer": cost
                        }

    indoor_event = {"class": "CampaignEvent",
                    "Start_Day": start,
                    "Nodeset_Config": {
                        "class": "NodeSetAll"
                    },
                    "Event_Coordinator_Config": {
                        "class": "StandardInterventionDistributionEventCoordinator",
                        "Demographic_Coverage": coverage,
                        "Target_Demographic": "Everyone",
                        "Intervention_Config": indoor_config
                    }
                    }

    if nodeIDs:
        indoor_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

    config_builder.add_event(indoor_event)
    add_ors_node(config_builder, start, coverage=coverage, 
                 initial_killing=initial_killing*outdoor_killing_discount, 
                 duration=killing_duration, cost=cost, 
                 nodeIDs=nodeIDs)