from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event

from dtk.utils.Campaign.CampaignClass import *
from dtk.utils.Campaign.CampaignEnum import *


def change_node_property(cb, target_property_name: str=None, target_property_value: str=None, start_day: int=0,
                         daily_prob: float=1, max_duration: int=3.40282e+38, revert: int=0, nodeIDs: list=None,
                         node_property_restrictions: list=None, triggered_campaign_delay: int=0,
                         trigger_condition_list: list=None, listening_duration: int=-1,
                         disqualifying_properties: list=None):
    """
    Add an intervention that changes the node property value to another on a
    particular day or after a triggering event using the
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
            be updated (**Daily_Probability** parameter). For example,
            the default value of 1 changes all values on the same day.
        max_duration: The maximum amount of time nodes have to move to a new
            NodeProperty value. This timing works in conjunction with
            **daily_prob**; nodes not moved to the new value by the end of
            **max_duration** keep the same value.
        revert: The number of days before a node reverts to its original
            property value. Default of 0 means the new value is kept forever.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, defaults to all nodes.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"Swamp", "Place":"NoRoads"},
            {"Place":"ForestLand}]``. Restrictions within each dictionary are
            connected with "and" condition and within the list are "or",
            so the example restricts the intervention to (Swamp Land AND No
            Roads) OR (Forest Land) nodes.
        triggered_campaign_delay: The number of days the campaign is delayed
            after being triggered. Eligibility of people or nodes
            for the campaign is evaluated on the start day, not the triggered
            day.
        trigger_condition_list: A list of the events that will
            trigger the intervention. If included, **start_day** is the day
            when monitoring for triggers begins.
        listening_duration: The number of time steps that the
            triggered campaign will be active for. Default is -1, which is
            indefinitely.
        disqualifying_properties: A list of NodeProperty key:value pairs that
            cause an intervention to be aborted (persistent interventions
            will stop being distributed to nodes with these values). For
            example, ["Place:Swamp"].

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            change_node_property(cb, target_property_name="InterventionStatus",
            target_property_value="RecentSpray", start_day=0,
                             daily_prob=1, max_duration=1,
                             revert=0, triggered_campaign_delay=0,
                             trigger_condition_list=["SpaceSpraying"],
                             listening_duration=-1)

    """
    if not target_property_name or not target_property_value:
        raise ValueError("Please define both:  target_property_name and target_property_value.\n")
    if node_property_restrictions is None:
        node_property_restrictions = []
    if disqualifying_properties is None:
        disqualifying_properties = []
    node_cfg = NodeSetAll()
    if nodeIDs:
        node_cfg = NodeSetNodeList(Node_List=nodeIDs)

    node_property_value_changer = NodePropertyValueChanger(
        Target_NP_Key_Value="%s:%s" % (target_property_name, target_property_value),
        Daily_Probability=daily_prob,
        Disqualifying_Properties=disqualifying_properties,
        Maximum_Duration=max_duration,
        Revert=revert
    )

    if trigger_condition_list:
        if triggered_campaign_delay:
            trigger_condition_list = [str(triggered_campaign_delay_event(cb, start_day, nodeIDs,
                                                                         triggered_campaign_delay,
                                                                         trigger_condition_list,
                                                                         listening_duration))]

        changer_event = CampaignEvent(
            Start_Day=start_day,
            Nodeset_Config=node_cfg,
            Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                Intervention_Config=NodeLevelHealthTriggeredIV(
                    Blackout_Event_Trigger="Node_Property_Change_Blackout",     # [TODO]: enum??
                    # we don't care about this, just need something to be here so the blackout works at all
                    Blackout_Period=1,  # so we only distribute the node event(s) once on that day in case of
                                        # multiple triggers
                    Blackout_On_First_Occurrence=1,
                    Duration=listening_duration,
                    Trigger_Condition_List=trigger_condition_list,
                    Actual_IndividualIntervention_Config=node_property_value_changer,
                    Node_Property_Restrictions=node_property_restrictions
                )
            )
        )
        cb.add_event(changer_event)

    else:
        changer_event = CampaignEvent(
            Start_Day=start_day,
            Nodeset_Config=node_cfg,
            Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                Intervention_Config=node_property_value_changer,
                Node_Property_Restrictions=node_property_restrictions
            )
        )
        cb.add_event(changer_event)



def change_individual_property_at_age(cb, target_property_name: str=None, target_property_value: str=None,
                                      change_age_in_days: int=None, start_day: int=0,
                                      listening_duration: int=-1, coverage: float=1, daily_prob: float=1,
                                      max_duration: int=3.40282e+38, revert: int=0, nodeIDs: list=None,
                                      node_property_restrictions: list=None, ind_property_restrictions: list=None,
                                      disqualifying_properties: list=None):
    """
    Add an intervention that changes an individual's individual property at
    a given number of days after birth using the **PropertyValueChanger**
    class.

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
            will be updated (**Daily_Probability** parameter). Default is 1,
            which changes property values for all individuals on the same day.
        max_duration: The maximum amount of time nodes have to move to a new
            NodeProperty value. This timing works in conjunction with
            **daily_prob**; nodes not moved to the new value by the end of
            **max_duration** keep the same value.
        revert: The number of days before a node reverts to its original
            property value. Default of 0 means the new value is kept forever.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, defaults to all nodes.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"Swamp", "Place":"NoRoads"},
            {"Place":"ForestLand}]``. Restrictions within each dictionary are
            connected with "and" condition and within the list are "or",
            so the example restricts the intervention to (Swamp Land AND No
            Roads) OR (Forest Land) nodes.
        ind_property_restrictions: The IndividualProperty key:value pairs to
            target (**Property_Restrictions_Within_Node** parameter). In the
            format ``[{"IndividualProperty1" : "PropertyValue1"},
            {'IndividualProperty2': "PropertyValue2"}, ...]``
        listening_duration: The number of time steps that the
            triggered campaign will be active for. Default is -1, which is
            indefinitely.
        disqualifying_properties: A list of NodeProperty key:value pairs that
            cause an intervention to be aborted (persistent interventions
            will stop being distributed to nodes with these values).  For
            example, ["Place:Swamp"].

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            change_individual_property_at_age(cb,
                                              target_property_name= "ImmuneStatus",
                                              target_property_value="NoMaternalImmunity",
                                              change_age_in_days=120, start_day=0,
                                              listening_duration=-1, coverage=1,
                                              daily_prob=1, max_duration=1,
                                              revert=0)
    """
    if not target_property_name or not target_property_value or not change_age_in_days:
        raise ValueError("Please define all:  target_property_name and target_property_value and change_age_in_days.\n")
    if node_property_restrictions is None:
        node_property_restrictions = []
    if ind_property_restrictions is None:
        ind_property_restrictions = []
    if disqualifying_properties is None:
        disqualifying_properties = []
    node_cfg = NodeSetAll()
    if nodeIDs:
        node_cfg = NodeSetNodeList(Node_List=nodeIDs)

    property_value_changer = PropertyValueChanger(
        Target_Property_Key=target_property_name,
        Target_Property_Value=target_property_value,
        Disqualifying_Properties=disqualifying_properties,
        Daily_Probability=daily_prob,
        Maximum_Duration=max_duration,
        Revert=revert
    )

    campaign_event = CampaignEvent(
        Start_Day=start_day,
        Nodeset_Config=node_cfg,
        Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
            Intervention_Config=BirthTriggeredIV(
                Duration=listening_duration,
                Demographic_Coverage=coverage,
                Node_Property_Restrictions=node_property_restrictions,
                Property_Restrictions_Within_Node=ind_property_restrictions,
                Actual_IndividualIntervention_Config=DelayedIntervention(
                    Delay_Distribution=DelayedIntervention_Delay_Distribution_Enum.FIXED_DURATION,
                    Delay_Period_Fixed=change_age_in_days, #old style
                    Delay_Period=change_age_in_days, #new style
                    Actual_IndividualIntervention_Configs=[property_value_changer]
                )
            )
        )
    )


    cb.add_event(campaign_event)


def change_individual_property(cb, target_property_name: str=None, target_property_value: str=None,
                               target_group: any='Everyone', start_day: int=0, coverage: float=1, daily_prob: float=1,
                               max_duration: int=3.40282e+38, revert: int=0, nodeIDs: list=None,
                               node_property_restrictions: list=None, ind_property_restrictions: list=None,
                               triggered_campaign_delay: int=0, trigger_condition_list: list=None,
                               listening_duration: int=-1, blackout_flag: bool=True,
                               disqualifying_properties: list=None, target_residents_only: bool=False):
    """
    Add an intervention that changes the individual property value to another on a
    particular day or after a triggering event using the
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
                max_duration: The maximum amount of time nodes have to move to a new
            NodeProperty value. This timing works in conjunction with
            **daily_prob**; nodes not moved to the new value by the end of
            **max_duration** keep the same value.
        revert: The number of days before a node reverts to its original
            property value. Default of 0 means the new value is kept forever.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, defaults to all nodes.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"Swamp", "Place":"NoRoads"},
            {"Place":"ForestLand}]``. Restrictions within each dictionary are
            connected with "and" condition and within the list are "or",
            so the example restricts the intervention to (Swamp Land AND No
            Roads) OR (Forest Land) nodes.
        ind_property_restrictions: The IndividualProperty key:value pairs to
            target (**Property_Restrictions_Within_Node** parameter). In the
            format ``[{"IndividualProperty1" : "PropertyValue1"},
            {'IndividualProperty2': "PropertyValue2"}, ...]``
         triggered_campaign_delay: The number of days the campaign is delayed
            after being triggered.
        trigger_condition_list: A list of the events that will
            trigger the intervention. If included, **start_day** is the day
            when monitoring for triggers begins.
        listening_duration: The number of time steps that the
            triggered campaign will be active for. Default is -1, which is
            indefinitely.
        blackout_flag: Set to True if you don't want the triggered intervention
            to be distributed to the same person more than once a day.
        disqualifying_properties: A list of NodeProperty key:value pairs that
            cause an intervention to be aborted (persistent interventions
            will stop being distributed to nodes with these values). For
            example, ["Place:Swamp"].
        target_residents_only: Set to True to target only the individuals who
            started the simulation in this node and are still in the node.

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            change_individual_property(cb,
                                       target_property_name="InterventionStatus",
                                       target_property_value="DiagnosedPos",
                                       target_group="Everyone", start_day=0,
                                       coverage=1, daily_prob=1,
                                       max_duration=1, revert=0,
                                       node_property_restrictions: list=None,
                                       ind_property_restrictions=[{"InterventionStatus": "Naive"}],
                                       triggered_campaign_delay=0,
                                       trigger_condition_list=["HIVTestedPositive"],
                                       listening_duration=-1, blackout_flag=True,
                                       target_residents_only=False)
    """
    if not target_property_name or not target_property_value:
        raise ValueError("Please define both:  target_property_name and target_property_value.\n")
    if ind_property_restrictions is None:
        ind_property_restrictions = []
    if node_property_restrictions is None:
        node_property_restrictions = []
    if disqualifying_properties is None:
        disqualifying_properties = []
    node_cfg = NodeSetAll()
    if nodeIDs:
        node_cfg = NodeSetNodeList(Node_List=nodeIDs)

    gender = "All"
    age_min = 0
    age_max = 3.40282e+38
    if target_group != "Everyone" and isinstance(target_group, dict):
        try:
            age_min = target_group["agemin"]
            age_max = target_group["agemax"]
            if 'gender' in target_group:
                gender = target_group["gender"]
                target_group = "ExplicitAgeRangesAndGender"
            else:
                target_group = "ExplicitAgeRanges"
        except KeyError:
            raise KeyError("Unknown target_group parameter. Please pass in 'Everyone' or a dictionary of "
                           "{'agemin' : x, 'agemax' : y, 'gender': 'Female'} to target  to individuals between x "
                           "and y years of age, and (optional) gender.\n")

    property_value_changer = PropertyValueChanger(
        Target_Property_Key=target_property_name,
        Target_Property_Value=target_property_value,
        Disqualifying_Properties=disqualifying_properties,
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
        changer_event = CampaignEvent(
                Start_Day=start_day,
                Nodeset_Config=node_cfg,
                Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                    Intervention_Config=NodeLevelHealthTriggeredIV(
                        # Blackout event trigger and period only used when blackout_flag is true
                        Blackout_Event_Trigger="Ind_Property_Blackout",
                        Blackout_Period=1,
                        # so we only change value once per time step
                        Blackout_On_First_Occurrence=blackout_flag,
                        Target_Residents_Only=target_residents_only,
                        Duration=listening_duration,
                        Trigger_Condition_List=trigger_condition_list,
                        Demographic_Coverage=coverage,
                        Target_Demographic=target_group,
                        Target_Age_Min=age_min,
                        Target_Age_Max=age_max,
                        Target_Gender=gender,
                        Node_Property_Restrictions=node_property_restrictions,
                        Property_Restrictions_Within_Node=ind_property_restrictions,
                        Actual_IndividualIntervention_Config=property_value_changer
                    )
                )
            )

        cb.add_event(changer_event)
    else:
        changer_event = CampaignEvent(
            Start_Day=start_day,
            Nodeset_Config=node_cfg,
            Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                Demographic_Coverage=coverage,
                Target_Demographic=target_group,
                Target_Age_Min=age_min,
                Target_Age_Max=age_max,
                Target_Gender=gender,
                Property_Restrictions_Within_Node=ind_property_restrictions,
                Node_Property_Restrictions=node_property_restrictions,
                Intervention_Config=property_value_changer
            )
        )
        cb.add_event(changer_event)

