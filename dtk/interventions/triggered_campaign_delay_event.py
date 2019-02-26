from dtk.utils.Campaign.CampaignClass import *
import random


def triggered_campaign_delay_event(config_builder, start: int=0,  nodeIDs: list=None,
                                   delay_distribution: str="FIXED_DURATION",
                                   delay_period_mean: float=1, delay_period_std_dev: float=1,
                                   delay_period_max: float=1, coverage: float=1,
                                   triggered_campaign_delay: int=0, trigger_condition_list: list=None,
                                   listening_duration: int=-1, event_to_send_out: str=None,
                                   node_property_restrictions: list=None, ind_property_restrictions: list=None,
                                   only_target_residents: bool=1):
    """
    Create a triggered campaign that broadcasts an event after a delay. The
    event it broadcasts can be specified or randomly generated.

    Args:
        config_builder: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        start: The day on which to start distributing the intervention
            (**Start_Day** parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, defaults to all nodes.
        delay_distribution: The distribution type of the length of the delay.
            Possible values are FIXED_DURATION or GAUSSIAN_DURATION.
        delay_period_mean: For GAUSSIAN_DURATION, the mean duration of the
            delay period.
        delay_period_std_dev: For GAUSSIAN_DURATION, the standard deviation of
            the delay period.
        delay_period_max: For GAUSSIAN_DURATION, the maximum duration of the
            delay period.
        coverage: The proportion of the population covered by the intervention
            (**Demographic_Coverage** parameter).
        triggered_campaign_delay: For FIXED_DURATION, the duration of the delay
            period. Eligibility of people or nodes for the campaign is
            evaluated on the start day, not the triggered day.
        trigger_condition_list: A list of the events that will
            trigger the delayed event broadcast. For example, ["HappyBirthday",
            "Received_Treatment"].
        listening_duration: The number of time steps that the distributed
            event will monitor for triggers. Default is -1, which is
            indefinitely.
        event_to_send_out: If specified, the event that will be broadcast
            after the delay.
        node_property_restrictions:The NodeProperty key:value pairs that
            nodes must have to receive the intervention
            (**Node_Property_Restrictions** parameter). In the format
            ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``.
        ind_property_restrictions: The IndividualProperty key:value pairs
            that individuals must have to receive the intervention
            (**Property_Restrictions_Within_Node** parameter). In the format
            ``[{"BitingRisk":"High"}, {"IsCool":"Yes}]``.
        only_target_residents: If true (1), the campaign only affects people
            who started the simulation in the node and still are in the node
            targeted.

    Returns:
        The event that is broadcast after the delay.

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            triggered_campaign_delay_event(config_builder, start=0,
                                           nodeIDs=[1, 5, 11],
                                           delay_distribution="GAUSSIAN_DURATION",
                                           delay_period_mean=14,
                                           delay_period_std_dev=4,
                                           delay_period_max=30, coverage=1,
                                           trigger_condition_list=["HappyBirthday"],
                                           listening_duration=-1,
                                           event_to_send_out="FirstCheckup",
                                           node_property_restrictions=[{"Place": "Urban"}],
                                           only_target_residents=1)

    """
    if nodeIDs:
        node_cfg = NodeSetNodeList(Node_List=nodeIDs)
    else:
        node_cfg = NodeSetAll()
    if not node_property_restrictions:
        node_property_restrictions = []
    if not ind_property_restrictions:
        ind_property_restrictions = []
    if not event_to_send_out:
        event_to_send_out = 'Delayed_Event_%d' % random.randrange(100000)
    if not triggered_campaign_delay:
        raise ValueError("Why are you using this with a 0 delay? This is used to add delay to triggered events by "
                         "sending out a delayed event.\n")

    event_cfg = BroadcastEvent(Broadcast_Event=event_to_send_out)

    if delay_distribution == 'FIXED_DURATION':
        intervention = DelayedIntervention(
            Delay_Distribution=delay_distribution,
            Delay_Period=triggered_campaign_delay,
            Delay_Period_Fixed=triggered_campaign_delay, # new style
            Actual_IndividualIntervention_Configs=[event_cfg]
         )
    elif delay_distribution == 'GAUSSIAN_DURATION':
        intervention = DelayedIntervention(
            Delay_Distribution=delay_distribution,
            Delay_Period_Mean=delay_period_mean,
            Delay_Period_Std_Dev=delay_period_std_dev,
            Delay_Period_Max=delay_period_max,
            Delay_Period_Gaussian_Mean=delay_period_mean, # new style
            Delay_Period_Gaussian_Std_Dev=delay_period_std_dev,  #new style
            Delay_Period_Gaussian_Max=delay_period_max, # new style
            Actual_IndividualIntervention_Configs=[event_cfg]
            )
    else:
        raise ValueError("{} is not a recognized delay_distribution. Please use GAUSSIAN_DURATION or FIXED_DURAION.\n")

    triggered_delay = CampaignEvent(
        Start_Day=start,
        Nodeset_Config=node_cfg,
        Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                Intervention_Config=NodeLevelHealthTriggeredIV(
                    Trigger_Condition_List=trigger_condition_list,
                    Duration=listening_duration,
                    Demographic_Coverage=coverage,
                    Target_Residents_Only=only_target_residents,
                    Node_Property_Restrictions=node_property_restrictions,
                    Property_Restrictions_Within_Node=ind_property_restrictions,
                    Actual_IndividualIntervention_Config=intervention)
        )
        )
    config_builder.add_event(triggered_delay)

    return event_to_send_out
