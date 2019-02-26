import random
from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event
from dtk.utils.Campaign.CampaignClass import *


# the old MigrateTo has now been split into MigrateIndividuals and MigrateFamily.
# add_migration_event adds a MigrateIndividuals event.
def add_migration_event(cb, nodeto, start_day=0, coverage=1, repetitions=1, tsteps_btwn=365,
                        duration_at_node_distr_type='FIXED_DURATION', 
                        duration_of_stay=100, duration_of_stay_2=0, 
                        duration_before_leaving_distr_type='FIXED_DURATION', 
                        duration_before_leaving=0, duration_before_leaving_2=0, 
                        target='Everyone', nodesfrom={"class": "NodeSetAll"},
                        ind_property_restrictions=[], node_property_restrictions=[], triggered_campaign_delay=0,
                        trigger_condition_list=[], listening_duration=-1):

    """
    Add a migration event to a campaign that moves individuals from one node
    to another using the **MigrateIndividuals** class.

    Args:
        cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        nodeto: The NodeID that the individuals will travel to.
        start_days: A list of days when ivermectin is distributed
            (**Start_Day** parameter).
        coverage: The proportion of the population covered by the intervention
            (**Demographic_Coverage** parameter).
        repetitions: The number of times to repeat the intervention
            (**Number_Repetitions** parameter).
        tsteps_btwn: The number of time steps between repetitions.
        duration_at_node_distr_type: The distribution type to draw from for
            determining the time spent at the destination node.
        duration_of_stay: The first parameter defining the distribution for
            duration of stay, the meaning of which depends upon the distribution
            type.
        duration_of_stay_2: The second parameter defining the distribution for
            duration of stay, the meaning of which depends upon the distribution
            type.
        duration_before_leaving_distr_type: The distribution type to draw from
            for determining the time spent waiting at the starting node before
            traveling to the destination node.
        duration_before_leaving: The first parameter defining the distribution
            for waiting time, the meaning of which depends upon the distribution
            type.
        duration_before_leaving_2: The second parameter defining the
            distribution for waiting time, the meaning of which depends upon
            the distribution type.
        target: The individuals to target with the intervention. To
            restrict by age, provide a dictionary of {'agemin' : x, 'agemax' :
            y}. Default is targeting everyone.
        nodesfrom: The dictionary definition the nodes that individuals will
            migrate from (**Nodeset_Config** parameter).
        ind_property_restrictions: The IndividualProperty key:value pairs
            that individuals must have to receive the intervention
            (**Property_Restrictions_Within_Node** parameter). In the format
            ``[{"BitingRisk":"High"}, {"IsCool":"Yes}]``.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention
            (**Node_Property_Restrictions** parameter). In the format
            ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``.
        triggered_campaign_delay: After the trigger is received, the number of
            time steps until distribution starts. Eligibility of people or nodes
            for the campaign is evaluated on the start day, not the triggered
            day.
        trigger_condition_list: A list of the events that will
            trigger the ivermectin intervention. If included, **start_days** is
            then used to distribute **NodeLevelHealthTriggeredIV**.
        listening_duration: The number of time steps that the distributed
            event will monitor for triggers. Default is -1, which is
            indefinitely.

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            add_migration_event(cb, nodeto=5, start_day=1, coverage=0.75,
                                repetitions=1, tsteps_btwn=90,
                                duration_at_node_distr_type='UNIFORM_DURATION',
                                duration_of_stay=30, duration_of_stay_2=90,
                                duration_before_leaving_distr_type='UNIFORM_DURATION',
                                duration_before_leaving=1,
                                duration_before_leaving_2=5,
                                target='Everyone', nodesfrom={"class": "NodeSetAll"},
                                node_property_restrictions=[{"Place": "Rural"}])
    """
    migration_event = MigrateIndividuals(
        NodeID_To_Migrate_To=nodeto,
        Is_Moving=False
    )

    migration_event = update_duration_type(migration_event, duration_at_node_distr_type,
                                           dur_param_1=duration_of_stay, dur_param_2=duration_of_stay_2,
                                           leaving_or_at='at')
    migration_event = update_duration_type(migration_event, duration_before_leaving_distr_type,
                                           dur_param_1=duration_before_leaving, dur_param_2=duration_before_leaving_2,
                                           leaving_or_at='leaving')

    if trigger_condition_list:
        if repetitions > 1 or triggered_campaign_delay > 0:
            event_to_send_out = random.randrange(100000)
            for x in range(repetitions):
                # create a trigger for each of the delays.
                triggered_campaign_delay_event(cb, start_day, nodesfrom,
                                               triggered_campaign_delay + x * tsteps_btwn,
                                               trigger_condition_list,
                                               listening_duration, event_to_send_out)
            trigger_condition_list = [str(event_to_send_out)]

        event = CampaignEvent(
            Event_Name="Migration Event Triggered",
            Start_Day=start_day,
            Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                Intervention_Config=NodeLevelHealthTriggeredIV(
                    Duration=listening_duration,
                    Trigger_Condition_List=trigger_condition_list,
                    Target_Demographic=StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum[target],
                    Target_Residents_Only=True,
                    Node_Property_Restrictions=node_property_restrictions,
                    Property_Restrictions_Within_Node=ind_property_restrictions,
                    Demographic_Coverage=coverage,
                    Actual_IndividualIntervention_Config=migration_event
                )
            ),
            Nodeset_Config=nodesfrom
        )

        if isinstance(target, dict) and all([k in target.keys() for k in ['agemin', 'agemax']]):
            event.Event_Coordinator_Config.Intervention_Config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges
            event.Event_Coordinator_Config.Intervention_Config.Target_Age_Min = target['agemin']
            event.Event_Coordinator_Config.Intervention_Config.Target_Age_Max = target['agemax']

    else:
        event = CampaignEvent(
            Event_Name="Migration Event",
            Start_Day=start_day,
            Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                Property_Restrictions_Within_Node=ind_property_restrictions,
                Node_Property_Restrictions=node_property_restrictions,
                Number_Distributions=-1,
                Number_Repetitions=repetitions,
                Target_Residents_Only=True,
                Target_Demographic=StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum[target],
                Timesteps_Between_Repetitions=tsteps_btwn,
                Demographic_Coverage=coverage,
                Intervention_Config=migration_event
            ),
            Nodeset_Config=nodesfrom
        )

        if isinstance(target, dict) and all([k in target for k in ['agemin', 'agemax']]):
            event.Event_Coordinator_Config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges
            event.Event_Coordinator_Config.Target_Age_Min = target['agemin']
            event.Event_Coordinator_Config.Target_Age_Max = target['agemax']

    cb.add_event(event)


def update_duration_type(migration_event, duration_at_node_distr_type, dur_param_1=0, dur_param_2=0, leaving_or_at='at') :

    """
    Update the distribution type that determines the length of time that each
    individual waits before migration or stays at the destination node. The
    assigned value for each individual is randomly drawn from the distribution.

    Args:
        migration_event: The **MigrateIndividuals** migration event to be
            updated.
        duration_at_node_distr_type: The distribution type to draw from for
            determining the duration of time spent at the starting or
            destination node.
        dur_param_1: The first parameter defining the distribution for
            duration of stay, the meaning of which depends upon the distribution
            type.
        dur_param_2: The second parameter defining the distribution for
            duration of stay, the meaning of which depends upon the distribution
            type.
        leaving_or_at: The portion of the trip that is updated. Accepted
            values are:

            leaving
                The time spent waiting at the starting node before leaving.
            at
                The time spent at the destination node.

    Returns:
        The updated migration event.


    Example:
        ::

            update_duration_type(migration_event,
                                 duration_at_node_distr_type="UNIFORM_DURATION",
                                 dur_param_1=2, dur_param_2=5,
                                 leaving_or_at="at")
    """
    if leaving_or_at == 'leaving':
        trip_end = 'Before_Leaving'
        MigrateFamily_Duration_Enum = MigrateIndividuals_Duration_Before_Leaving_Distribution_Type_Enum
    else:
        trip_end = 'At_Node'
        MigrateFamily_Duration_Enum = MigrateIndividuals_Duration_At_Node_Distribution_Type_Enum

    if duration_at_node_distr_type == 'FIXED_DURATION' :
        setattr(migration_event, "Duration_" + trip_end + "_Distribution_Type", MigrateFamily_Duration_Enum.FIXED_DURATION)
        setattr(migration_event, "Duration_" + trip_end + "_Fixed", dur_param_1)
    elif duration_at_node_distr_type == 'UNIFORM_DURATION' :
        setattr(migration_event, "Duration_" + trip_end + "_Distribution_Type", MigrateFamily_Duration_Enum.UNIFORM_DURATION)
        setattr(migration_event, "Duration_" + trip_end + "_Uniform_Min", dur_param_1)
        setattr(migration_event, "Duration_" + trip_end + "_Uniform_Max", dur_param_2)
    elif duration_at_node_distr_type == 'GAUSSIAN_DURATION' :
        setattr(migration_event, "Duration_" + trip_end + "_Distribution_Type", MigrateFamily_Duration_Enum.GAUSSIAN_DURATION)
        setattr(migration_event, "Duration_" + trip_end + "_Gausian_Mean", dur_param_1)
        setattr(migration_event, "Duration_" + trip_end + "_Gausian_StdDev", dur_param_2)
    elif duration_at_node_distr_type == 'EXPONENTIAL_DURATION' :
        setattr(migration_event, "Duration_" + trip_end + "_Distribution_Type", MigrateFamily_Duration_Enum.EXPONENTIAL_DURATION)
        setattr(migration_event, "Duration_" + trip_end + "_Exponential_Period", dur_param_1)
    elif duration_at_node_distr_type == 'POISSON_DURATION' :
        setattr(migration_event, "Duration_" + trip_end + "_Distribution_Type", MigrateFamily_Duration_Enum.POISSON_DURATION)
        setattr(migration_event, "Duration_" + trip_end + "_Poisson_Mean", dur_param_1)
    else:
        print("warning: unsupported duration distribution type, reverting to fixed duration")
        setattr(migration_event, "Duration_" + trip_end + "_Distribution_Type", MigrateFamily_Duration_Enum.FIXED_DURATION)
        setattr(migration_event, "Duration_" + trip_end + "_Fixed", dur_param_1)

    return migration_event
