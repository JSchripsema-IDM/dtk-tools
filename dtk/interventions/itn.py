# Bednet parameters
itn_bednet = { "class": "SimpleBednet",
               "Bednet_Type": "ITN", 
               "Blocking_Rate": 0.9,
               "Killing_Rate": 0.6, 
               "Durability_Time_Profile": "DECAYDURABILITY", 
               "Primary_Decay_Time_Constant":   4 * 365,   # killing
               "Secondary_Decay_Time_Constant": 2 * 365,   # blocking
               "Cost_To_Consumer": 3.75
}

# Bednet distribution event parameters
def add_ITN(config_builder, start, coverage_by_ages, waning={}, cost=None, nodeIDs=[]):

    if waning:
        itn_bednet.update({ "Durability_Time_Profile":       waning['profile'], 
                            "Primary_Decay_Time_Constant":   waning['kill'] * 365,
                            "Secondary_Decay_Time_Constant": waning['block'] * 365 })

    if cost:
        itn_bednet['Cost_To_Consumer'] = cost

    for coverage_by_age in coverage_by_ages:

        ITN_event = { "class" : "CampaignEvent",
                      "Start_Day": start,
                      "Event_Coordinator_Config": {
                          "class": "StandardInterventionDistributionEventCoordinator",
                          "Demographic_Coverage": coverage_by_age["coverage"],
                          "Intervention_Config": itn_bednet
                      }
                    }

        if all([k in coverage_by_age.keys() for k in ['min','max']]):
            ITN_event["Event_Coordinator_Config"].update({
                   "Target_Demographic": "ExplicitAgeRanges",
                   "Target_Age_Min": coverage_by_age["min"],
                   "Target_Age_Max": coverage_by_age["max"]})

        if not nodeIDs:
            ITN_event["Nodeset_Config"] = { "class": "NodeSetAll" }
        else:
            ITN_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

        if 'birth' in coverage_by_age.keys() and coverage_by_age['birth']:
            birth_triggered_intervention = {
                "class": "BirthTriggeredIV",
                "Duration": -1, # forever.  could expire and redistribute every year with different coverage values
                "Demographic_Coverage": coverage_by_age["coverage"],
                "Actual_IndividualIntervention_Config": itn_bednet
            }
            ITN_event["Event_Coordinator_Config"]["Intervention_Config"] = birth_triggered_intervention
            ITN_event["Event_Coordinator_Config"].pop("Demographic_Coverage")

        config_builder.add_event(ITN_event)