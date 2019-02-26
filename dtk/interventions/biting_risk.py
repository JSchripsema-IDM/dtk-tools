from dtk.utils.Campaign.CampaignClass import *
from dtk.utils.Campaign.CampaignEnum import *


def change_biting_risk(cb, start_day=0,
                       risk_config={'Risk_Distribution_Type': 'FIXED_DURATION', 'Constant': 1},
                       coverage=1,
                       repetitions=1,
                       tsteps_btwn_repetitions=365,
                       target_group='Everyone',
                       trigger=None,
                       triggered_biting_risk_duration=-1,
                       nodeIDs=[],
                       node_property_restrictions=[],
                       ind_property_restrictions=[]
                       ):
    """
    Add an intervention to change individual biting risk in a campaign using the
    **BitingRisk** class.

    Args:

        cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            that contains the campaign configuration.
        start_day: The day on which to start distributing the intervention
            (**Start_Day** parameter).
        risk_config: A dictionary containing the risk distribution type and
            distribution parameters that define the distribution from which
            biting risk will be drawn. Assign one of the following to
            **Risk_Distribution_Type**:
        
            FIXED_DURATION
                Parameter: **Constant**
            UNIFORM_DURATION
                Parameters: **Uniform_Min**, **Uniform_Max**
            GAUSSIAN_DURATION
                Parameters: **Gaussian_Mean**, **Gaussian_Std_Dev**
            EXPONENTIAL_DURATION
                Parameter: **Exponential_Mean**
        coverage: The proportion of the population that will receive the
            intervention (**Demographic_Coverage** parameter).
        repetitions: The number of times to repeat the intervention.
        tsteps_btwn_repetitions:  The number of time steps between repetitions.
        target_group: The individuals to target with the intervention. To
            restrict by age, provide a dictionary of ``{'agemin' : x, 'agemax' :
            y}``. Default is targeting everyone.
        trigger: A list of the events that will trigger the biting risk
            intervention. If included, **start_day** is the day when
            monitoring for triggers begins.
        triggered_biting_risk_duration: For triggered changes, the duration
            after **start_day** over which triggered risk-changing will happen.
            Default is indefinitely.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.
        ind_property_restrictions: The IndividualProperty key:value pairs to
            target (**Property_Restrictions_Within_Node** parameter). In the
            format ``[{"IndividualProperty1" : "PropertyValue1"},
            {'IndividualProperty2': "PropertyValue2"}, ...]``
        node_property_restrictions:The NodeProperty key:value pairs that
            nodes must have to receive the intervention
            (**Node_Property_Restrictions** parameter). In the format
            ``[{"NodeProperty1" : "PropertyValue1"}, {'NodeProperty2': "PropertyValue2"}, ...]``

    .. note:: **NewPropertyValue** and **DisqualifyingProperties** have not
            been implemented with this intervention.

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            change_biting_risk(cb, start_day=5,
                               risk_config={'Risk_Distribution_Type': 'UNIFORM_DURATION',
                                            'Uniform_Min': 1,
                                            'Uniform_Max': 5},
                               coverage=0.8, repetitions=2,
                               tsteps_btwn_repetitions=90,
                               target_group={'agemin': 2, 'agemax': 12})
    """

    risk_config = BitingRisk(**risk_config)

    risk_event = CampaignEvent(Start_Day=start_day,
                               Nodeset_Config=NodeSetAll(),
                               Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                                   Number_Repetitions=repetitions,
                                   Timesteps_Between_Repetitions=tsteps_btwn_repetitions,
                                   Target_Demographic=StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.Everyone,
                                   Demographic_Coverage=coverage,
                                   Intervention_Config=risk_config)
                               )

    if target_group != 'Everyone':
        risk_event.Event_Coordinator_Config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges # Otherwise default is Everyone
        risk_event.Event_Coordinator_Config.Target_Age_Min = target_group['agemin']
        risk_event.Event_Coordinator_Config.Target_Age_Max = target_group['agemax']

    if not nodeIDs:
        risk_event.Nodeset_Config = NodeSetAll()
    else:
        risk_event.Nodeset_Config = NodeSetNodeList(Node_List=nodeIDs)

    if node_property_restrictions:
        risk_event.Event_Coordinator_Config.Node_Property_Restrictions = node_property_restrictions

    if ind_property_restrictions:
        risk_event.Event_Coordinator_Config.Property_Restrictions_Within_Node = ind_property_restrictions

    if trigger:

        if 'birth' in trigger.lower():
            triggered_intervention = BirthTriggeredIV(
                Duration=triggered_biting_risk_duration,
                Demographic_Coverage=coverage,
                Actual_IndividualIntervention_Config=risk_config
            )

        else:
            triggered_intervention = NodeLevelHealthTriggeredIV(
                Demographic_Coverage=coverage,
                Duration=triggered_biting_risk_duration,
                Trigger_Condition_List=[trigger],
                Actual_IndividualIntervention_Config=risk_config
            )

        risk_event.Event_Coordinator_Config.Intervention_Config = triggered_intervention

        del risk_event.Event_Coordinator_Config.Demographic_Coverage
        del risk_event.Event_Coordinator_Config.Number_Repetitions
        del risk_event.Event_Coordinator_Config.Timesteps_Between_Repetitions
        del risk_event.Event_Coordinator_Config.Target_Demographic

        if ind_property_restrictions:
            del risk_event.Event_Coordinator_Config.Property_Restrictions_Within_Node
            risk_event.Event_Coordinator_Config.Intervention_Config.Property_Restrictions_Within_Node = ind_property_restrictions

    cb.add_event(risk_event)