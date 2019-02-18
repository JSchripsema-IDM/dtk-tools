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
    Creates a triggered campaign that broadcasts an event after a delay. The event it broadcasts can be specified
    or it is randomly generated. You can use either FIXED_DURATION or GAUSSIAN_DURATION for the delay
    Args:
        config_builder:
        start: the first day of the campaign
        nodeIDs: list of nodeIDs there this campaign
        delay_distribution: distribution of the length of the delay, can be FIXED_DURAION or GAUSSIAN_DURATION,
            FIXED_DURATION is the default
        delay_period_mean: for GAUSSIAN_DURATION: the mean time of the duration of the event being sent out
        delay_period_std_dev: for GAUSSIAN_DURATION: the std deviation of the duration of the event being sent out
        delay_period_max: for GAUSSIAN_DURATION: the maximum time of the duration of the event being sent out
        coverage: sets Demographic_Coverage
        triggered_campaign_delay: for FIXED_DURATION: the delay time of the event being sent out
        trigger_condition_list: list of events that trigger the delayed event broadcast,
            example: ["HappyBirthday", "Received_Treatment"]
        listening_duration: the duration for which the listen for the trigger, Default: -1 indicates "indefinitely/forever"
        event_to_send_out: if specified, the event that will be sent out after the delay
        node_property_restrictions: Restricts intervention based on list of dictionaries of node properties in
            format: [{"Land":"Swamp", "Roads":"No"}, {"Land": "Forest"}]; default is no restrictions, with
            restrictions within each dictionary are connected with "and" and within the list are "or", so the
            example restrictions are nodes with (Swamp Land AND No Roads) OR (Forest Land) nodes
        ind_property_restrictions: Restricts intervention based on list of dictionaries of individual properties in
            format: [{"BitingRisk":"High", "IsCool":"Yes}, {"IsRich": "Yes"}]; default is no restrictions, with
            restrictions within each dictionary are connected with "and" and within the list are "or", so the
            example restrictions are individuals with (High Biting Risk AND Yes IsCool) OR (IsRich) individuals
        only_target_residents: only affects people who started the simulation and still are in the node targeted

    Returns:
        The event that will be broadcast after the delay.

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
