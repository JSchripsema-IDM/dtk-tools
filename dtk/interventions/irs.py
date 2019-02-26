""" 
This module has been updated. The old IRS parameters were as follows::

        irs_housingmod = {"class": "IRSHousingModification",
                          "Blocking_Rate": 0.0,  # i.e. repellency
                          "Killing_Rate": 0.7,
                          "Durability_Time_Profile": "DECAYDURABILITY",
                          "Primary_Decay_Time_Constant": 365,  # killing
                          "Secondary_Decay_Time_Constant": 365,  # blocking
                          "Cost_To_Consumer": 8.0
                         }

"""


import copy, random
from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event
from dtk.utils.Campaign.CampaignClass import *


irs_housingmod_master = IRSHousingModification(
    Killing_Config=WaningEffectExponential(
        Initial_Effect=0.5,
        Decay_Time_Constant=90
    ),
    Blocking_Config=WaningEffectExponential(
        Initial_Effect=0.0,
        Decay_Time_Constant=730
    ),
    Cost_To_Consumer=8.0
)

node_irs_config = SpaceSpraying(
    Reduction_Config=WaningEffectExponential(
        Decay_Time_Constant=365,
        Initial_Effect=0
    ),
    Cost_To_Consumer=1.0,
    Habitat_Target=SpaceSpraying_Habitat_Target_Enum.ALL_HABITATS,
    Killing_Config=WaningEffectExponential(
        Decay_Time_Constant=90,
        Initial_Effect=0.5
    ),
    Spray_Kill_Target=SpaceSpraying_Spray_Kill_Target_Enum.SpaceSpray_Indoor
)


def add_IRS(config_builder, start, coverage_by_ages, cost=None, nodeIDs=[],
            initial_killing=0.5, duration=90, waning={}, node_property_restrictions=[],
            ind_property_restrictions=[], triggered_campaign_delay=0, trigger_condition_list=[], listening_duration=-1):
    """
    Add an indoor residual spraying (IRS) intervention using the
    **IRSHousingModification** class, an individual-level intervention. This
    can be distributed on a scheduled day or can be triggered by a list of
    events.
    
    Args:
        config_builder: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        start: The day on which to start distributing the intervention
            (**Start_Day** parameter) or the day to begin monitoring for
            events that trigger IRS.
        coverage_by_ages: A list of dictionaries defining the coverage per
            age group or birth-triggered intervention. For example,
            ``[{"coverage":1,"min": 1, "max": 10},{"coverage":1,"min": 11,
            "max": 50}]``
        cost: The per-unit cost (**Cost_To_Consumer** parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.
        initial_killing: The initial killing effect of IRS
            (**Initial_Effect** in **Killing_Config**).
        duration: The exponential decay constant of the effectiveness
            (**Decay_Time_Constant** parameter with the
            **WaningEffectExponential** class).
        waning: A dictionary defining the durability of the spray. If empty,
            the default of **WaningEffectExponential** with
            **Initial_Effect** = 0.5 and **Decay_Time_Constant** = 90 is used.
        ind_property_restrictions: The IndividualProperty key:value pairs
            that individuals must have to receive the intervention (
            **Property_Restrictions_Within_Node** parameter). In the format ``[{
            "BitingRisk":"High"}, {"IsCool":"Yes}]``.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``
        triggered_campaign_delay: After the trigger is received, the number of
            time steps until the campaign starts. Eligibility of people or nodes
            for the campaign is evaluated on the start day, not the triggered
            day.
        trigger_condition_list: (Optional) A list of the events that will
            trigger the IRS intervention. If included, **start** is the day
            when monitoring for triggers begins. This argument cannot
            configure birth-triggered IRS (use **coverage_by_ages** instead).
        listening_duration: The number of time steps that the distributed
            event will monitor for triggers. Default is -1, which is indefinitely.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            waning = {"class"=""WaningEffectBox",
                      "Box_Duration"= 60,
                      "Initial_Effect"=0.5}
            add_IRS(config_builder, start=1,
                    coverage_by_ages=[{"coverage":1,"min": 1, "max": 18},
                                      {"coverage":0.6,"min": 19, "max": 80}],
                    cost=1, nodeIDs=[1, 2, 5], initial_killing=0.75,
                    duration=90, waning, listening_duration=-1)
    """

    receiving_irs_event = BroadcastEvent(Broadcast_Event="Received_IRS")

    irs_housingmod = copy.deepcopy(irs_housingmod_master)

    irs_housingmod.Killing_Config.Initial_Effect = initial_killing
    irs_housingmod.Killing_Config.Decay_Time_Constant = duration

    if waning:
        for w, w_config in waning.items():
            setattr(irs_housingmod, w, w_config)

    if cost:
        irs_housingmod.Cost_To_Consumer = cost

    irs_housingmod_w_event = MultiInterventionDistributor(Intervention_List=[irs_housingmod, receiving_irs_event])

    nodeset_config = NodeSetAll() if not nodeIDs else NodeSetNodeList(Node_List=nodeIDs)

    if triggered_campaign_delay :
        trigger_condition_list = [triggered_campaign_delay_event(config_builder, start, nodeIDs,
                                                                 triggered_campaign_delay,
                                                                 trigger_condition_list,
                                                                 listening_duration)]

    for coverage_by_age in coverage_by_ages:
        if trigger_condition_list:
            if 'birth' not in coverage_by_age.keys():
                IRS_event = CampaignEvent(
                    Start_Day=int(start),
                    Nodeset_Config=nodeset_config,
                    Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                        Intervention_Config=NodeLevelHealthTriggeredIV(
                            Trigger_Condition_List=trigger_condition_list,
                            Duration=listening_duration,
                            Property_Restrictions_Within_Node=ind_property_restrictions,
                            Node_Property_Restrictions=node_property_restrictions,
                            Demographic_Coverage=coverage_by_age["coverage"],
                            Target_Residents_Only=True,
                            Actual_IndividualIntervention_Config=irs_housingmod_w_event
                        )
                    )
                )

                if all([k in coverage_by_age.keys() for k in ['min', 'max']]):
                    IRS_event.Event_Coordinator_Config.Intervention_Config.Target_Demographic = NodeLevelHealthTriggeredIV_Target_Demographic_Enum.ExplicitAgeRanges
                    IRS_event.Event_Coordinator_Config.Intervention_Config.Target_Age_Min = coverage_by_age["min"]
                    IRS_event.Event_Coordinator_Config.Intervention_Config.Target_Age_Max = coverage_by_age["max"]

                config_builder.add_event(IRS_event)

        else:
            IRS_event = CampaignEvent(
                Start_Day=int(start),
                Nodeset_Config=nodeset_config,
                Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                    Demographic_Coverage=coverage_by_age["coverage"],
                    Target_Residents_Only=True,
                    Intervention_Config=irs_housingmod_w_event
                )
            )

            if all([k in coverage_by_age.keys() for k in ['min', 'max']]):
                IRS_event.Event_Coordinator_Config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges
                IRS_event.Event_Coordinator_Config.Target_Age_Min = coverage_by_age["min"]
                IRS_event.Event_Coordinator_Config.Target_Age_Max = coverage_by_age["max"]

            if 'birth' in coverage_by_age.keys() and coverage_by_age['birth']:
                birth_triggered_intervention = BirthTriggeredIV(
                    Duration=coverage_by_age.get('duration', -1),  # default to forever if duration not specified
                    Demographic_Coverage=coverage_by_age["coverage"],
                    Actual_IndividualIntervention_Config=irs_housingmod_w_event
                )

                IRS_event.Event_Coordinator_Config.Intervention_Config = birth_triggered_intervention
                del IRS_event.Event_Coordinator_Config.Demographic_Coverage
                del IRS_event.Event_Coordinator_Config.Target_Residents_Only

            if ind_property_restrictions and 'birth' in coverage_by_age.keys() and coverage_by_age['birth']:
                IRS_event.Event_Coordinator_Config.Intervention_Config.Property_Restrictions_Within_Node = ind_property_restrictions
            elif ind_property_restrictions:
                IRS_event.Event_Coordinator_Config.Property_Restrictions_Within_Node = ind_property_restrictions

            if node_property_restrictions:
                IRS_event.Event_Coordinator_Config.Node_Property_Restrictions = node_property_restrictions

            config_builder.add_event(IRS_event)


def add_node_IRS(config_builder, start, initial_killing=0.5, box_duration=90,
                 waning_effect_type='WaningEffectExponential', cost=None,
                 irs_ineligibility_duration=0, nodeIDs=[], node_property_restrictions=[],
                 triggered_campaign_delay=0, trigger_condition_list=[], listening_duration=-1):
    """
    Add an indoor residual spraying (IRS) intervention using the
    **SpaceSpraying** class, a node-level intervention. This can be distributed
    on a scheduled day or can be triggered by a list of events.

    Args:
        config_builder: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        start: The day on which to start distributing the intervention
            (**Start_Day** parameter) or the day to begin monitoring for
            events that trigger IRS.
        initial_killing: The initial killing effect of IRS
            (**Initial_Effect** in **Killing_Config**).
        box_duration: For "box" waning effects, the number of time steps
            until the efficacy of the intervention begins to decay.
        waning_effect_type: The way in which IRS efficacy decays (see Waning
            Effect classes).
        cost: The per-unit cost (**Cost_To_Consumer** parameter).
        irs_ineligibility_duration: The number of time steps after a node is
            sprayed before it is eligible for another round of IRS.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``
        triggered_campaign_delay: After the trigger is received, the number of
            time steps until the campaign starts. Eligibility of people or nodes
            for the campaign is evaluated on the start day, not the triggered
            day.
        trigger_condition_list: (Optional) A list of the events that will
            trigger the IRS intervention. If included, **start** is the day
            when monitoring for triggers begins. This argument cannot
            configure birth-triggered IRS (use **coverage_by_ages** instead).
        listening_duration: The number of time steps that the distributed
            event will monitor for triggers. Default is -1, which is indefinitely.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            add_node_IRS(config_builder, start=1, initial_killing=0.5,
                         box_duration=90,
                         waning_effect_type='WaningEffectBox', cost=1,
                         irs_ineligibility_duration=14, nodeIDs=[2, 25],
                         triggered_campaign_delay=7,
                         trigger_condition_list=['NewSevereCase'],
                         listening_duration=-1)
    """
    irs_config = copy.deepcopy(node_irs_config)
    irs_config.Killing_Config.Initial_Effect = initial_killing
    irs_config.Killing_Config.Decay_Time_Constant = box_duration

    if waning_effect_type == 'WaningEffectBox':
        irs_config.Killing_Config.Box_Duration = box_duration
        del irs_config.Killing_Config.Decay_Time_Constant

    if not nodeIDs:
        nodeset_config = NodeSetAll()
    else:
        nodeset_config = NodeSetNodeList(Node_List=nodeIDs)

    if cost:
        node_irs_config.Cost_To_Consumer = cost

    node_sprayed_event = BroadcastEvent(Broadcast_Event="Node_Sprayed")

    IRS_event = CampaignEvent(
        Start_Day=int(start),
        Nodeset_Config=nodeset_config,
        Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
            Node_Property_Restrictions=node_property_restrictions,
            Intervention_Config=MultiInterventionDistributor(
                Intervention_List=[irs_config, node_sprayed_event]
            )
        ),
        Event_Name="Node Level IRS"
    )

    if trigger_condition_list:
        if triggered_campaign_delay:
            trigger_condition_list = [str(triggered_campaign_delay_event(config_builder, start, nodeIDs,
                                                                         triggered_campaign_delay=triggered_campaign_delay,
                                                                         trigger_condition_list=trigger_condition_list,
                                                                         listening_duration=listening_duration))]

        IRS_event.Event_Coordinator_Config.Intervention_Config = NodeLevelHealthTriggeredIV(
            Blackout_On_First_Occurrence=True,
            Blackout_Event_Trigger="IRS_Blackout_%d" % random.randint(0, 10000),
            Blackout_Period=1,
            Node_Property_Restrictions=node_property_restrictions,
            Duration=listening_duration,
            Trigger_Condition_List=trigger_condition_list,
            Actual_IndividualIntervention_Config=MultiInterventionDistributor(
                Intervention_List=[irs_config, node_sprayed_event]
            ),
            Target_Residents_Only=True
        )

        del IRS_event.Event_Coordinator_Config.Node_Property_Restrictions

    IRS_cfg = copy.copy(IRS_event)
    if irs_ineligibility_duration > 0:
        recent_irs = NodePropertyValueChanger(
            Target_NP_Key_Value="SprayStatus:RecentSpray",
            Daily_Probability=1.0,
            Maximum_Duration=0,
            Revert=irs_ineligibility_duration
        )

        if trigger_condition_list:
            IRS_cfg.Event_Coordinator_Config.Intervention_Config.Actual_IndividualIntervention_Config.Intervention_List.append(recent_irs)
            if not node_property_restrictions:
                IRS_cfg.Event_Coordinator_Config.Intervention_Config.Node_Property_Restrictions = [{'SprayStatus': 'None'}]
            else:
                for n, np in enumerate(node_property_restrictions) :
                    node_property_restrictions[n]['SprayStatus'] = 'None'
                IRS_cfg.Event_Coordinator_Config.Intervention_Config.Node_Property_Restrictions = node_property_restrictions
        else:
            IRS_cfg.Event_Coordinator_Config.Intervention_Config.Intervention_List.append(recent_irs)
            if not node_property_restrictions:
                IRS_cfg.Event_Coordinator_Config.Node_Property_Restrictions = [{'SprayStatus': 'None'}]
            else:
                for n, np in enumerate(node_property_restrictions):
                    node_property_restrictions[n]['SprayStatus'] = 'None'
                IRS_cfg.Event_Coordinator_Config.Node_Property_Restrictions = node_property_restrictions

    config_builder.add_event(IRS_cfg)
