from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event

from dtk.utils.Campaign.CampaignClass import *
from dtk.utils.Campaign.CampaignEnum import *


def change_node_property(cb, target_property_name, target_property_value, start_day=0, daily_prob=1,
                         max_duration=0, revert=0, nodeIDs=[], node_property_restrictions=[], triggered_campaign_delay=0,
                        trigger_condition_list=[], listening_duration=-1):
    """
    Change the node property value after a triggering event as part of an
    intervention distribution in a campaign using the
    **NodePropertyValueChanger** class.

    Args:
        cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        target_property_name: The node property key to assign to the node. For
            example, InterventionStatus.
        target_property_value: The node property value to assign to the node.
            For example, RecentDrug.
        start_day: The day on which to start distributing the intervention
            (**Start_Day** parameter).
        daily_prob: The daily probability that a node's property value will
            be updated (**Daily_Probability** parameter).
        max_duration: The maximum amount of time nodes have to update their
            property value.
        revert: The number of days before a node reverts to its original
            property value.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter).
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``
        triggered_campaign_delay: After the trigger is received, the number of
            time steps until the campaign starts. Eligibility of nodes
            for the campaign is evaluated on the start day, not the triggered
            day.
        trigger_condition_list: A list of the events that will
            trigger the intervention. If included, **start_day** is the day
            when monitoring for triggers begins.
        listening_duration: The number of time steps that the distributed
            event will monitor for triggers. Default is -1, which is indefinitely.

    Returns:
        None
    """
    node_cfg = NodeSetAll()
    if nodeIDs:
        node_cfg = NodeSetNodeList(Node_List=nodeIDs)

    node_property_value_changer = NodePropertyValueChanger(
        Target_NP_Key_Value="%s:%s" % (target_property_name, target_property_value),
        Daily_Probability=daily_prob,
        Maximum_Duration=max_duration,
        Revert=revert
    )

    if trigger_condition_list:
        if triggered_campaign_delay:
            trigger_condition_list = [str(triggered_campaign_delay_event(cb, start_day, nodeIDs, triggered_campaign_delay,
                        trigger_condition_list, listening_duration))]

        changer_event = CampaignEvent(
            Start_Day=int(start_day),
            Nodeset_Config=node_cfg,
            Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                Intervention_Config=NodeLevelHealthTriggeredIV(
                    Blackout_Event_Trigger="Node_Property_Change_Blackout",     # [TODO]: enum??
                    # we don't care about this, just need something to be here so the blackout works at all
                    Blackout_Period=1,  # so we only distribute the node event(s) once
                    Blackout_On_First_Occurrence=1,
                    Duration=listening_duration,
                    Trigger_Condition_List=trigger_condition_list,
                    Actual_IndividualIntervention_Config=node_property_value_changer
                )
            )
        )

        if node_property_restrictions:
            changer_event.Event_Coordinator_Config.Intervention_Config.Node_Property_Restrictions = node_property_restrictions

        cb.add_event(changer_event)

    else:
        prop_ch_config = StandardInterventionDistributionEventCoordinator(Intervention_Config=node_property_value_changer)

        if node_property_restrictions:
            prop_ch_config.Intervention_Config.Node_Property_Restrictions = node_property_restrictions

        event = CampaignEvent(
            Start_Day=start_day,
            Event_Coordinator_Config=prop_ch_config,
            Nodeset_Config=node_cfg
        )

        cb.add_event(event)


def change_individual_property_at_age(cb, target_property_name, target_property_value, change_age_in_days, start_day=0,
                                      duration=-1, coverage=1, daily_prob=1, max_duration=0, revert=0, nodeIDs=[],
                                      node_property_restrictions=[]):
    """
    Change the individual property value at a given age as part of an
    intervention distribution in a campaign using the
    **PropertyValueChanger** class.

    Args:
        cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        target_property_name: The individual property key to assign to the
            individual. For example, InterventionStatus.
        target_property_value: The individual property value to assign to the
            individual. For example, RecentDrug.
        change_age_in_days: The age, in days, after birth to change the property
            value.
        start_day: The day on which to start distributing the intervention
            (**Start_Day** parameter).
        duration: The number of days to continue the intervention after
            **start_day**.
        coverage: The proportion of the population that will receive the
            intervention (**Demographic_Coverage** parameter).
        daily_prob: The daily probability that an individual's property value
            will be updated (**Daily_Probability** parameter).
        max_duration: The maximum amount of time individuals have to update
            their property value.
        revert: The number of days before an individual reverts to their
            original property value.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter).
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``

    Returns:
        None
    """

    actual_config = PropertyValueChanger(
        Target_Property_Key=target_property_name,
        Target_Property_Value=target_property_value,
        Daily_Probability=daily_prob,
        Maximum_Duration=max_duration,
        Revert=revert
    )

    birth_triggered_intervention = BirthTriggeredIV(
        Duration=duration,  # default to forever if  duration not specified
        Demographic_Coverage=coverage,
        Actual_IndividualIntervention_Config=DelayedIntervention(
            Coverage=1,
            Delay_Distribution=DelayedIntervention_Delay_Distribution_Enum.FIXED_DURATION,
            Delay_Period=change_age_in_days,
            Actual_IndividualIntervention_Configs=[actual_config]
        )
    )

    prop_ch_config = StandardInterventionDistributionEventCoordinator(
        Intervention_Config=birth_triggered_intervention
    )

    if node_property_restrictions:
        prop_ch_config.Intervention_Config.Node_Property_Restrictions = node_property_restrictions

    node_cfg = NodeSetAll()
    if nodeIDs :
        node_cfg = NodeSetNodeList(Node_List=nodeIDs)

    event = CampaignEvent(
        Start_Day=start_day,
        Event_Coordinator_Config=prop_ch_config,
        Nodeset_Config=node_cfg
    )

    cb.add_event(event)


def change_individual_property(cb, target_property_name, target_property_value, target='Everyone', start_day=0,
                               coverage=1, daily_prob=1, max_duration=0, revert=0, nodeIDs=[],
                               node_property_restrictions=[], ind_property_restrictions=[], triggered_campaign_delay=0,
                               trigger_condition_list=[], listening_duration=-1, blackout_flag=True
                               ):
    """
    Change the individual property value after a triggering event as part of an
    intervention distribution in a campaign using the
    **PropertyValueChanger** class.

    Args:
        cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        target_property_name: The individual property key to assign to the
            individual. For example, InterventionStatus.
        target_property_value: The individual property value to assign to the
            individual. For example, RecentDrug.
        target: The individuals to target with the intervention. To
            restrict by age, provide a dictionary of ``{'agemin' : x, 'agemax' :
            y}``. Default is targeting everyone.
        start_day: The day on which to start distributing the intervention
            (**Start_Day** parameter).
        coverage: The proportion of the population that will receive the
            intervention (**Demographic_Coverage** parameter).
        daily_prob: The daily probability that an individual's property value
            will be updated (**Daily_Probability** parameter).
        max_duration: The maximum amount of time individuals have to update
            their property value.
        revert: The number of days before an individual reverts to its original
            property value.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter).
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``
        ind_property_restrictions: The IndividualProperty key:value pairs that
            indivdiuals must have to receive the intervention (
            **Property_Restrictions_Within_Node** parameter). In the
            format ``[{"IndividualProperty1" : "PropertyValue1"},
            {'IndividualProperty2': "PropertyValue2"}, ...]``
        triggered_campaign_delay: After the trigger is received, the number of
            time steps until the campaign starts. Eligibility of individuals
            for the campaign is evaluated on the start day, not the triggered
            day.
        trigger_condition_list: A list of the events that will
            trigger the intervention. If included, **start_day** is the day
            when monitoring for triggers begins.
        listening_duration: The number of time steps that the distributed
            event will monitor for triggers. Default is -1, which is indefinitely.
        blackout_flag: If True, prevent the event from being distributed
            multiple times per day; if False, allow multiple events per day.

    Returns:

    """
    node_cfg = NodeSetAll()
    if nodeIDs:
        node_cfg = NodeSetNodeList(Node_List=nodeIDs)

    property_value_changer = PropertyValueChanger(
        Target_Property_Key=target_property_name,
        Target_Property_Value=target_property_value,
        Daily_Probability=daily_prob,
        Maximum_Duration=max_duration,
        Revert=revert
    )

    if trigger_condition_list:
        if triggered_campaign_delay:
            trigger_condition_list = [triggered_campaign_delay_event(cb, start_day,
                                                                     nodeIDs=nodeIDs,
                                                                     triggered_campaign_delay=triggered_campaign_delay,
                                                                     trigger_condition_list=trigger_condition_list,
                                                                     listening_duration=listening_duration)]
        if blackout_flag:
            changer_event = CampaignEvent(
                Start_Day=start_day,
                Nodeset_Config=node_cfg,
                Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                    Intervention_Config=NodeLevelHealthTriggeredIV(
                        Blackout_Event_Trigger="Ind_Property_Blackout",
                        # we don't care about this, just need something to be here so the blackout works at all
                        Blackout_Period=1,
                        # so we only distribute the node event(s) once
                        Blackout_On_First_Occurrence=True,
                        Target_Residents_Only=False,
                        Duration=listening_duration,
                        Trigger_Condition_List=trigger_condition_list,
                        # Target_Residents_Only=1,          # [ZDU]: duplicated
                        Demographic_Coverage=coverage,
                        Actual_IndividualIntervention_Config=property_value_changer
                    )
                )
            )
        else:
            changer_event = CampaignEvent(
                Start_Day=start_day,
                Nodeset_Config=node_cfg,
                Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                    Intervention_Config=NodeLevelHealthTriggeredIV(
                        Target_Residents_Only=False,
                        Duration=listening_duration,
                        Trigger_Condition_List=trigger_condition_list,
                        # Target_Residents_Only=1,          # [ZDU]: duplicated
                        Demographic_Coverage=coverage,
                        Actual_IndividualIntervention_Config=property_value_changer
                    )
                )
            )


        if isinstance(target, dict) and all([k in target for k in ['agemin', 'agemax']]):
             changer_event.Event_Coordinator_Config.Intervention_Config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges
             changer_event.Event_Coordinator_Config.Intervention_Config.Target_Age_Min = target['agemin']
             changer_event.Event_Coordinator_Config.Intervention_Config.Target_Age_Max = target['agemax']
        else:
             changer_event.Event_Coordinator_Config.Intervention_Config.Target_Demographic = NodeLevelHealthTriggeredIV_Target_Demographic_Enum[target]  # default is Everyone

        if node_property_restrictions:
             changer_event.Event_Coordinator_Config.Intervention_Config.Node_Property_Restrictions = node_property_restrictions

        if ind_property_restrictions:
             changer_event.Event_Coordinator_Config.Intervention_Config.Property_Restrictions_Within_Node = ind_property_restrictions
        cb.add_event(changer_event)


    else:
        prop_ch_config = StandardInterventionDistributionEventCoordinator(
            Demographic_Coverage=coverage,
            Intervention_Config=property_value_changer
        )

        if isinstance(target, dict) and all([k in target for k in ['agemin','agemax']]) :
            prop_ch_config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges
            prop_ch_config.Target_Age_Min = target['agemin']
            prop_ch_config.Target_Age_Max = target['agemax']
        else:
            prop_ch_config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum[target] # default is Everyone

        if node_property_restrictions:
            prop_ch_config.Intervention_Config.Node_Property_Restrictions = node_property_restrictions

        if ind_property_restrictions:
            prop_ch_config.Intervention_Config.Property_Restrictions_Within_Node = ind_property_restrictions

        event = CampaignEvent(
            Start_Day=start_day,
            Event_Coordinator_Config=prop_ch_config,
            Nodeset_Config=node_cfg
        )

        cb.add_event(event)