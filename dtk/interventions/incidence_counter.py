from dtk.utils.Campaign.CampaignClass import *


def add_incidence_counter(cb,
                          start_day=0,
                          count_duration=365,
                          count_triggers=['NewClinicalCase', 'NewSevereCase'],
                          threshold_type='COUNT',
                          thresholds=[10, 100],
                          triggered_events=['Action1', 'Action2'],
                          coverage=1,
                          repetitions=1,
                          tsteps_btwn_repetitions=365,
                          target_group='Everyone',
                          nodeIDs=[],
                          node_property_restrictions=[],
                          ind_property_restrictions=[]
                          ):
    """
    Add an intervention that monitors for the number of new cases that occur
    during a given time period using the **IncidenceEventCoordinator** class.


    Args:
        cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            that will receive the intervention.
        start_day: The day to distribute the intervention (**Start_Day**
            parameter).
        repetitions: The number of times to repeat the intervention.
        tsteps_btwn_repetitions:  The number of time steps between repetitions.
        count_duration: The number of time steps during which to monitor for
            new cases.
        count_triggers: A list of the events that will increment the
            monitor's count.
        threshold_type: To monitor raw counts, use COUNT; to normalize
            by population, use PERCENTAGE.
        thresholds: The thresholds for each count trigger that will trigger a
            response.
        triggered_events: The event names to broadcast upon surpassing each
            threshold.
        coverage: The demographic coverage of the monitoring. This value
            affects the probability that a **count_trigger** will be counted by
            is ignored for calculating the denominator for PERCENTAGE.
        target_group: Optionally, the age range that monitoring is restricted
            to, formatted as a dict of ``{'agemin': x, 'agemax': y}``. By
            default, everyone is monitored.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.
        ind_property_restrictions: The IndividualProperty key:value pairs
            that individuals must have to receive the intervention (
            **Property_Restrictions_Within_Node** parameter). In the format
            ``[{"IndividualProperty1: "PropertyValue1"},
            {"IndividualProperty2: "IndividualValue2"} ...]``.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"NodeProperty1": "PropertyValue1"},
            {"NodeProperty2": "PropertyValue2"}, ...]``.

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            add_incidence_counter(cb, start_day=1, count_duration=90,
                                  count_triggers=['NewClinicalCase',
                                                  'NewSevereCase'],
                                  threshold_type='PERCENTAGE',
                                  thresholds=[0.1, 1],
                                  triggered_events=['DeployCHW',
                                                    'MassCampaign'],
                                  coverage=1, repetitions=4,
                                  tsteps_btwn_repetitions=90,
                                  target_group='Everyone',
                                  node_property_restrictions=[{'Place':'Rural'}]
                                 )

    """

    counter_config = {
        'Count_Events_For_Num_Timesteps': count_duration,
        'Trigger_Condition_List': count_triggers,
        "Target_Demographic": "Everyone",
        "Demographic_Coverage": coverage
    }
    responder_config = {
        'Threshold_Type': threshold_type,
        'Action_List': [ { 'Threshold' : t, 'Event_To_Broadcast': e} for t, e in zip(thresholds, triggered_events)]
    }

    if target_group != 'Everyone':
        counter_config.update({
            "Target_Demographic": "ExplicitAgeRanges",  # Otherwise default is Everyone
            "Target_Age_Min": target_group['agemin'],
            "Target_Age_Max": target_group['agemax']
        })

    if node_property_restrictions:
        counter_config['Node_Property_Restrictions'] = node_property_restrictions

    if ind_property_restrictions:
        counter_config["Property_Restrictions_Within_Node"] = ind_property_restrictions

    monitoring_event = CampaignEvent(
        Start_Day=start_day,
        Nodeset_Config=NodeSetAll(),
        Event_Coordinator_Config=IncidenceEventCoordinator(
            Number_Repetitions=repetitions,
            Timesteps_Between_Repetitions=tsteps_btwn_repetitions,
            Incidence_Counter=counter_config,
            Responder=responder_config
        )
    )

    if not nodeIDs:
        monitoring_event.Nodeset_Config = NodeSetAll()
    else:
        monitoring_event.Nodeset_Config = NodeSetNodeList(Node_List=nodeIDs)

    cb.add_event(monitoring_event)
    listed_events = cb.get_param('Listed_Events')
    new_events = [x for x in triggered_events if x not in listed_events]
    cb.update_params({'Listed_Events': listed_events + new_events})
