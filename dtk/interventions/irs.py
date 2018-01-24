''' OLD
# IRS parameters
irs_housingmod = {"class": "IRSHousingModification",
                  "Blocking_Rate": 0.0,  # i.e. repellency
                  "Killing_Rate": 0.7,
                  "Durability_Time_Profile": "DECAYDURABILITY",
                  "Primary_Decay_Time_Constant": 365,  # killing
                  "Secondary_Decay_Time_Constant": 365,  # blocking
                  "Cost_To_Consumer": 8.0
                  }
'''
import copy

irs_housingmod = { "class": "IRSHousingModification",
                "Killing_Config": {
                    "Initial_Effect": 0.5,
                    "Decay_Time_Constant": 90,
                    "class": "WaningEffectExponential"
                },
                "Blocking_Config": {
                    "Initial_Effect": 0.0,
                    "Decay_Time_Constant": 730,
                    "class": "WaningEffectExponential"
                },
               "Cost_To_Consumer": 8.0
}

node_irs_config = { "Reduction_Config": {
                        "Decay_Time_Constant": 365, 
                        "Initial_Effect": 0, 
                        "class": "WaningEffectExponential"
                    }, 
                    "Cost_To_Consumer": 1.0, 
                    "Habitat_Target": "ALL_HABITATS", 
                    "Killing_Config": {
                        "Decay_Time_Constant": 90, 
                        "Initial_Effect": 0.5, 
                        "class": "WaningEffectExponential"
                    }, 
                    "Spray_Kill_Target": "SpaceSpray_Indoor", 
                    "class": "SpaceSpraying"
                }


def add_IRS(config_builder, start, coverage_by_ages, cost=None, nodeIDs=[],
            initial_killing=0.5, duration=90, waning={}, node_property_restrictions=[],
            ind_property_restrictions=[], trigger_string=''):
    """
    Add an IRS intervention to the config_builder passed.

    :param config_builder: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>` holding the campaign that will receive the IRS event
    :param start: The start day of the spraying
    :param coverage_by_ages: a list of dictionaries defining the coverage per age group
    :param waning: a dictionary defining the durability of the nets. if empty the default ``DECAYDURABILITY`` with 1 year primary and 1 year secondary will be used.
    :param cost: Set the ``Cost_To_Consumer`` parameter
    :param nodeIDs: If empty, all nodes will get the intervention. If set, only the nodeIDs specified will receive the intervention.
    :return: Nothing
    """
    
    receiving_irs_event = {
        "class": "BroadcastEvent",
        "Broadcast_Event": "Received_IRS"
    }

    if waning:
        for cfg in waning :
            irs_housingmod[cfg].update(waning[cfg])

    if initial_killing:
        irs_housingmod['Killing_Config']['Initial_Effect'] = initial_killing


    if duration:
        irs_housingmod['Killing_Config']['Decay_Time_Constant'] = duration

    if cost:
        irs_housingmod['Cost_To_Consumer'] = cost

    irs_housingmod_w_event = {
        "Intervention_List" : [irs_housingmod, receiving_irs_event] ,
        "class" : "MultiInterventionDistributor"
        }

    for coverage_by_age in coverage_by_ages:
        IRS_event = {"class": "CampaignEvent",
                     "Start_Day": int(start),
                     "Event_Coordinator_Config": {
                         "class": "StandardInterventionDistributionEventCoordinator",
                         "Demographic_Coverage": coverage_by_age["coverage"]

                     }
                     }
        if trigger_string:
            IRS_event['Event_Coordinator_Config']['Intervention_Config'] = {
                "class" : "NodeLevelHealthTriggeredIV",
                "Blackout_On_First_Occurrence": 1,
                "Trigger_Condition_List": [trigger_string],
                "Actual_IndividualIntervention_Config" : irs_housingmod_w_event,
                "Target_Residents_Only": 1
            }
        else:
            IRS_event['Event_Coordinator_Config'].update(
                {
                         "Intervention_Config": irs_housingmod_w_event,
                         "Target_Residents_Only": 1
                     })

        if node_property_restrictions:
            IRS_event['Event_Coordinator_Config']['Node_Property_Restrictions'].extend(node_property_restrictions)

        if all([k in coverage_by_age.keys() for k in ['min', 'max']]):
            target_by_age ={
                "Target_Demographic": "ExplicitAgeRanges",
                "Target_Age_Min": coverage_by_age["min"],
                "Target_Age_Max": coverage_by_age["max"]}


        if trigger_string:
            IRS_event["Event_Coordinator_Config"]['Intervention_Config'].update(target_by_age)
        else:
            IRS_event["Event_Coordinator_Config"].update(target_by_age)

        if not nodeIDs:
            IRS_event["Nodeset_Config"] = {"class": "NodeSetAll"}
        else:
            IRS_event["Nodeset_Config"] = {"class": "NodeSetNodeList", "Node_List": nodeIDs}

        if 'birth' in coverage_by_age.keys() and coverage_by_age['birth']:
            birth_triggered_intervention = {
            "class": "BirthTriggeredIV",
            "Duration": coverage_by_age.get('duration', -1), # default to forever if duration not specified
            "Demographic_Coverage": coverage_by_age["coverage"],
            "Actual_IndividualIntervention_Config": irs_housingmod
            }

            IRS_event["Event_Coordinator_Config"]["Intervention_Config"] = birth_triggered_intervention
            IRS_event["Event_Coordinator_Config"].pop("Demographic_Coverage")
            IRS_event["Event_Coordinator_Config"].pop("Target_Residents_Only")

            if ind_property_restrictions:
                IRS_event["Event_Coordinator_Config"]["Intervention_Config"][
                    "Property_Restrictions_Within_Node"] = ind_property_restrictions

        elif ind_property_restrictions:
            if trigger_string:
                IRS_event["Event_Coordinator_Config"]['Intervention_Config'][
                    "Property_Restrictions_Within_Node"] = ind_property_restrictions
            else:
                IRS_event["Event_Coordinator_Config"]["Property_Restrictions_Within_Node"] = ind_property_restrictions

        config_builder.add_event(IRS_event)


def add_node_IRS(config_builder, start, initial_killing=0.5, box_duration=90, cost=None,
                 irs_ineligibility_duration=0, nodeIDs=[], node_property_restrictions=[], trigger_string=''):

    irs_config = copy.deepcopy(node_irs_config)
    irs_config['Killing_Config']['Decay_Time_Constant'] = box_duration
    irs_config['Killing_Config']['Initial_Effect'] = initial_killing

    if cost:
        node_irs_config['Cost_To_Consumer'] = cost

    IRS_event = {
                 "class": "CampaignEvent",
                 "Start_Day": int(start),
                 "Event_Coordinator_Config": {
                     "class": "StandardInterventionDistributionEventCoordinator",
                     'Node_Property_Restrictions': []
                 },
                 "Event_Name": "Node Level IRS"
                 }

    if trigger_string:
        IRS_event['Event_Coordinator_Config']['Intervention_Config'] = {
            "class": "NodeLevelHealthTriggeredIV",
            "Blackout_On_First_Occurrence": 1,
            "Trigger_Condition_List": [trigger_string],
            "Actual_IndividualIntervention_Config": node_irs_config,
            "Target_Residents_Only": 1
        }
    else:
        IRS_event['Event_Coordinator_Config'].update(
            {
                "Intervention_Config": node_irs_config,
                "Target_Residents_Only": 1
            })

    if not nodeIDs:
        IRS_event["Nodeset_Config"] = { "class": "NodeSetAll" }
    else:
        IRS_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

    IRS_cfg = copy.copy(IRS_event)
    if irs_ineligibility_duration > 0:
        recent_irs = {"class": "NodePropertyValueChanger",
                      "Target_NP_Key_Value": "SprayStatus:RecentSpray",
                      "Daily_Probability": 1.0,
                      "Maximum_Duration": 0,
                      'Revert': irs_ineligibility_duration
                      }
        IRS_cfg['Event_Coordinator_Config']['class'] = 'MultiInterventionEventCoordinator'
        IRS_cfg['Event_Coordinator_Config']['Intervention_Configs'] = [
            irs_config,
            recent_irs]
        del IRS_cfg['Event_Coordinator_Config']['Intervention_Config']

        if target_string:
            IRS_cfg['Event_Coordinator_Config']['Intervention_Config']['Node_Property_Restrictions'].extend([{'SprayStatus': 'None'}])
        else:
            IRS_cfg['Event_Coordinator_Config']['Node_Property_Restrictions'].extend([{ 'SprayStatus' : 'None'}])

    if node_property_restrictions:
        if trigger_string:
            IRS_cfg['Event_Coordinator_Config']['Intervention_Config']['Node_Property_Restrictions'].extend(node_property_restrictions)
        else:
            IRS_cfg['Event_Coordinator_Config']['Node_Property_Restrictions'].extend(node_property_restrictions)

    config_builder.add_event(IRS_cfg)
