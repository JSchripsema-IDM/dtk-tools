import copy
from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event
from dtk.utils.Campaign.CampaignClass import *


itn_bednet = SimpleBednet(Bednet_Type='ITN',
                          Killing_Config=WaningEffectExponential(Initial_Effect=0.6, Decay_Time_Constant=1460),
                          Blocking_Config=WaningEffectExponential(Initial_Effect=0.9, Decay_Time_Constant=730),
                          Usage_Config=WaningEffectRandomBox(Expected_Discard_Time=3650, Initial_Effect=1.0),
                          Cost_To_Consumer=3.75
                          )

receiving_itn_event = BroadcastEvent(Broadcast_Event='Received_ITN')


def add_ITN(config_builder, start, coverage_by_ages, waning={}, cost=0, nodeIDs=[], node_property_restrictions=[],
            ind_property_restrictions=[], triggered_campaign_delay=0, trigger_condition_list=[], listening_duration=1):
    """
     Add an insecticide-treated net (ITN) intervention to the campaign
     using the **SimpleBednet** class.
    
    Args:

        config_builder: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        start: The day on which to start distributing the bednets
            (**Start_Day** parameter).
        coverage_by_ages: A list of dictionaries defining the coverage per
            age group. For example, ``[{"coverage":1,"min": 1, "max": 10},
            {"coverage":1,"min": 11, "max": 50},{ "coverage":0.5, "birth":"birth",
            "duration":34}]``.
        waning: A dictionary defining the durability of the nets. If not
            provided, the default decay profile for **Killing_Config**,
            **Blocking_Config**, and **Usage_Config** are used. For example,
            to update usage duration, provide ``{"Usage_Config" : {
            "Expected_Discard_Time": 180}}``.
        cost: The per-unit cost (**Cost_To_Consumer** parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.
        ind_property_restrictions: The IndividualProperty key:value pairs
            that individuals must have to receive the intervention (
            **Property_Restrictions_Within_Node** parameter). In the format ``[{
            "BitingRisk":"High"}, {"IsCool":"Yes}]``.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``.
        triggered_campaign_delay: After the trigger is received, the number of
            time steps until the campaign starts. Eligibility of people or nodes
            for the campaign is evaluated on the start day, not the triggered
            day.
        trigger_condition_list: (Optional) A list of the events that will
            trigger the ITN intervention. If included, **start** is the day
            when monitoring for triggers begins. This argument cannot
            configure birth-triggered ITN (use **coverage_by_ages** instead).
        listening_duration: The number of time steps that the distributed
            event will monitor for triggers. Default is -1, which is indefinitely.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            coverage_by_ages = [{"coverage": 1, "min": 1, "max": 10},
                                {"coverage": 0.75, "min": 11, "max": 60}]
            add_ITN(config_builder, start=1, coverage_by_ages,
                    cost=1, nodeIDs=[2, 5, 7, 21],
                    node_property_restrictions=[{"Place": "Urban"}],
                    ind_property_restrictions=[{"Biting_Risk": "High"],
                    triggered_campaign_delay=14,
                    trigger_condition_list=["NewClinicalCase", "NewSevereCase"],
                    listening_duration=-1)
    """

    if waning:
        for w, w_config in waning.items():
            setattr(itn_bednet, w, w_config)

    itn_bednet.Cost_To_Consumer = cost

    itn_bednet_w_event = MultiInterventionDistributor(Intervention_List=[itn_bednet, receiving_itn_event])

    # Assign node IDs #
    # Defaults to all nodes unless a node set is specified
    if not nodeIDs:
        nodeset_config = NodeSetAll()
    else:
        nodeset_config = NodeSetNodeList(Node_List=nodeIDs)

    if triggered_campaign_delay:
        trigger_condition_list = [str(triggered_campaign_delay_event(config_builder,
                                                                     start,  nodeIDs,
                                                                     triggered_campaign_delay,
                                                                     trigger_condition_list,
                                                                     listening_duration))]

    for coverage_by_age in coverage_by_ages:
        if trigger_condition_list:
            if not 'birth' in coverage_by_age.keys():
                intervention_config = NodeLevelHealthTriggeredIV(
                    Trigger_Condition_List=trigger_condition_list,
                    Duration=listening_duration,
                    Demographic_Coverage=coverage_by_age["coverage"],
                    Target_Residents_Only=True,
                    Actual_IndividualIntervention_Config=itn_bednet_w_event  # itn_bednet
                )

                ITN_event = CampaignEvent(Start_Day=int(start),
                                          Nodeset_Config=nodeset_config,
                                          Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                                              Intervention_Config=intervention_config)
                                          )

                if all([k in coverage_by_age.keys() for k in ['min', 'max']]):
                    ITN_event_e_i = ITN_event.Event_Coordinator_Config.Intervention_Config
                    ITN_event_e_i.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges
                    ITN_event_e_i.Target_Age_Min = coverage_by_age["min"]
                    ITN_event_e_i.Target_Age_Max = coverage_by_age["max"]

                if ind_property_restrictions:
                    ITN_event_e_i.Property_Restrictions_Within_Node = ind_property_restrictions

                if node_property_restrictions:
                    ITN_event_e_i.Node_Property_Restrictions = node_property_restrictions

        else:
            event_coordinator_config = StandardInterventionDistributionEventCoordinator(
                Node_Property_Restrictions=[],
                Target_Residents_Only=1,
                Demographic_Coverage=coverage_by_age["coverage"],
                Intervention_Config=itn_bednet_w_event              # itn_bednet
            )
            ITN_event = CampaignEvent(Start_Day=int(start),
                                      Nodeset_Config=nodeset_config,
                                      Event_Coordinator_Config=event_coordinator_config
                                      )

            if node_property_restrictions:
                ITN_event.Event_Coordinator_Config.Node_Property_Restrictions.extend(node_property_restrictions)

            if all([k in coverage_by_age.keys() for k in ['min', 'max']]):
                ITN_event.Event_Coordinator_Config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges
                ITN_event.Event_Coordinator_Config.Target_Age_Min = coverage_by_age["min"]
                ITN_event.Event_Coordinator_Config.Target_Age_Max = coverage_by_age["max"]

            if 'birth' in coverage_by_age.keys() and coverage_by_age['birth']:
                birth_triggered_intervention = BirthTriggeredIV(
                    Duration=coverage_by_age.get('duration', -1),               # default to forever if  duration not specified
                    Demographic_Coverage=coverage_by_age["coverage"],
                    Actual_IndividualIntervention_Config=itn_bednet_w_event     # itn_bednet
                )

                ITN_event.Event_Coordinator_Config.Intervention_Config = birth_triggered_intervention
                del ITN_event.Event_Coordinator_Config.Demographic_Coverage
                del ITN_event.Event_Coordinator_Config.Target_Residents_Only

                if ind_property_restrictions:
                    ITN_event.Event_Coordinator_Config.Intervention_Config.Property_Restrictions_Within_Node = ind_property_restrictions

            elif ind_property_restrictions:
                ITN_event.Event_Coordinator_Config.Property_Restrictions_Within_Node = ind_property_restrictions

        config_builder.add_event(ITN_event)