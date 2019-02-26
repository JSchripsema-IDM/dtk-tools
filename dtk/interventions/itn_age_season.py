import numpy as np
import sys
from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event
from dtk.utils.Campaign.CampaignClass import *


def add_ITN_age_season(config_builder, start=1, coverage_all=1, waning={}, discard={},
                       age_dep={}, seasonal_dep={}, cost=5, nodeIDs=[], as_birth=False, duration=-1,
                       triggered_campaign_delay=0, trigger_condition_list=[],
                       ind_property_restrictions=[], node_property_restrictions=[]):

    """
    Add an insecticide-treated net (ITN) intervention with a seasonal usage
    pattern to the campaign using the **UsageDependentBednet** class. The
    arguments **as_birth** and **triggered_condition_list** are mutually
    exclusive. If both are provided, **triggered_condition_list** is ignored.

    You must add the following custom events:
        
        * Bednet_Discarded
        * Bednet_Got_New_One
        * Bednet_Using

    Args:

        config_builder: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        start: The day on which to start distributing the bednets
            (**Start_Day** parameter).
        coverage_all: Fraction of the population receiving bed nets in a given distribution event
        waning: A dictionary defining the durability of the nets
            (**Killing_Config** and **Blocking_Config**). For example,
            to update killing efficacy, provide ``{'Killing_Config' :
            {"Initial_Effect": 0.8}}``. Default is exponential decay with 0.6
            killing efficacy with 1460 decay and 0.9 blocking efficacy with
            730 decay.
        discard: A dictionary defining the net retention rates (
            **Usage_Config_List** parameter). Default is not to discard nets.
        age_dep: A dictionary defining the age dependence of net use.
            Must contain a list of ages in years and list of usage rate. Default
            is uniform across all ages.
        seasonal_dep: A dictionary defining the seasonal dependence of net use.
            Default is constant use during the year. Times are given in days
            of the year; values greater than 365 are ignored. Dictionaries
            can be (times, values) for linear spline or (minimum coverage,
            day of maximum coverage) for sinusoidal dynamics.
        cost: The per-unit cost (**Cost_To_Consumer** parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.
        as_birth: If true, event is specified as a birth-triggered intervention.
        duration: If run as a birth-triggered event or a trigger_condition_list,
            specifies the duration for the distribution to continue. Default
            is to continue until the end of the simulation.
        triggered_campaign_delay: (Optional) After the trigger is received,
            the number of time steps until the campaign starts. Eligibility
            of people or nodes for the campaign is evaluated on the start
            day, not the triggered day.
        trigger_condition_list: (Optional) A list of the events that will
            trigger the ITN intervention. If included, **start** is the day
            when monitoring for triggers begins. This argument cannot
            configure birth-triggered ITN (use **as_birth** instead).
        ind_property_restrictions: The IndividualProperty key:value pairs
            that individuals must have to receive the intervention (
            **Property_Restrictions_Within_Node** parameter). In the format ``[{
            "BitingRisk":"High"}, {"IsCool":"Yes}]``.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention (**Node_Property_Restrictions**
            parameter). In the format ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            waning = {'Blocking_Config':
                        {"class": "WaningEffectMapLinearSeasonal",
                         "Initial_Effect": 0.75,
                         "Durability_Map": {"Times": [1, 90, 180, 270],
                                            "Values": [1, 0.8, 0.6, 0.4]
                                           }
                         }
                      }
            age_dep = {"Times": [0, 4, 10, 60],
                       "Values": [1, 0.9, 0.8, 0.5]}
            add_ITN_age_season(config_builder, start=1, coverage_all=1, waning,
                       age_dep, cost=5, as_birth=True, duration=-1,
                       node_property_restrictions=[{"Place": "Rural"]):
    """

    # Assign net protective properties #
    # Unless specified otherwise, use the default values
    kill_initial = 0.6
    block_initial = 0.9
    kill_decay = 1460
    block_decay = 730

    if waning:
        if 'kill_initial' in waning.keys():
            kill_initial = waning['kill_initial']

        if 'block_initial' in waning.keys():
            block_initial = waning['block_initial']

        if 'kill_decay' in waning.keys():
            kill_decay = waning['kill_decay']

        if 'block_decay' in waning.keys():
            block_decay = waning['block_decay']

    # Assign seasonal net usage #
    # Times are days of the year
    # Input can be provided either as (times, values) for linear spline or (min coverage, day of maximum coverage)
    # under the assumption of sinusoidal dynamics. In the first case, the same value should be provided
    # for both 0 and 365; times > 365 will be ignored.
    if all([k in seasonal_dep.keys() for k in ['times', 'values']]):
        seasonal_times = seasonal_dep['times']
        seasonal_values = seasonal_dep['values']
    elif all([k in seasonal_dep.keys() for k in ['min_cov', 'max_day']]):
        seasonal_times = np.append(np.arange(0, 361, 30), 365)
        if seasonal_dep['min_cov'] == 0:
            seasonal_dep['min_cov'] = seasonal_dep['min_cov'] + sys.float_info.epsilon
        seasonal_values = (1-seasonal_dep['min_cov'])/2*np.cos(2*np.pi/365*(seasonal_times-seasonal_dep['max_day'])) + \
                      (1 + seasonal_dep['min_cov'])/2
    else:
        seasonal_times = np.append(np.arange(0, 361, 30), 365)
        seasonal_values = np.linspace(1, 1, len(seasonal_times))

    # Assign age-dependent net usage #
    # Times are ages in years (note difference from seasonal dependence)
    if all([k in age_dep.keys() for k in ['times', 'values']]):
        age_times = age_dep['times']
        age_values = age_dep['values']
    elif all([k in age_dep.keys() for k in ['youth_cov','youth_min_age','youth_max_age']]):
        age_times = [0, age_dep['youth_min_age']-0.1, age_dep['youth_min_age'],
                     age_dep['youth_max_age']-0.1, age_dep['youth_max_age']]
        age_values = [1, 1, age_dep['youth_cov'], age_dep['youth_cov'], 1]
    else:
        age_times = [0, 125]  # Dan B has hard-coded an upper limit of 125, will return error for larger values
        age_values = [1, 1]

    # Assign net ownership retention times #
    # Mean discard times in days; coverage half-life is discard time * ln(2)
    if all([k in discard.keys() for k in ['halflife1', 'halflife2','fraction1']]):  # Two retention subgroups
        discard_time1 = discard['halflife1']
        discard_time2 = discard['halflife2']
        discard_fraction1 = discard['fraction1']
    elif 'halflife' in discard.keys():  # Single mean retention time
        discard_time1 = discard['halflife']
        discard_time2 = 365*40
        discard_fraction1 = 1
    else:                               # No discard of nets
        discard_time1 = 365*40
        discard_time2 = 365*40
        discard_fraction1 = 1

    # Assign node IDs #
    # Defaults to all nodes unless a node set is specified
    if not nodeIDs:
        nodeset_config = NodeSetAll()
    else:
        nodeset_config = NodeSetNodeList(Node_List=nodeIDs)

    itn_campaign = MultiInterventionDistributor(
        Intervention_List=
        [
            UsageDependentBednet(
                Bednet_Type="ITN",
                Blocking_Config=WaningEffectExponential(
                    Decay_Time_Constant=block_decay,
                    Initial_Effect=block_initial
                ),
                Cost_To_Consumer=cost,
                Killing_Config=WaningEffectExponential(
                    Decay_Time_Constant=kill_decay,
                    Initial_Effect=kill_initial
                ),
                Usage_Config_List=
                [
                    WaningEffectMapLinearAge(
                        Initial_Effect=1.0,
                        Durability_Map=
                        {
                            "Times": list(age_times),
                            "Values": list(age_values)
                        }
                    ),
                    WaningEffectMapLinearSeasonal(
                        Initial_Effect=1.0,
                        Durability_Map=
                        {
                            "Times": list(seasonal_times),
                            "Values": list(seasonal_values)
                        }
                    )
                ],
                Received_Event="Bednet_Got_New_One",
                Using_Event="Bednet_Using",
                Discard_Event="Bednet_Discarded",
                Expiration_Distribution_Type=UsageDependentBednet_Expiration_Distribution_Type_Enum.DUAL_TIMESCALE_DURATION,
                Expiration_Period_1=discard_time1,
                Expiration_Period_2=discard_time2,
                Expiration_Percentage_Period_1=discard_fraction1
            )
        ]
    )

    # General or birth-triggered
    if as_birth:
        itn_event = CampaignEvent(
            Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                Intervention_Config=BirthTriggeredIV(
                    Actual_IndividualIntervention_Config=itn_campaign,
                    Demographic_Coverage=coverage_all,
                    Duration=duration
                )
            ),
            Nodeset_Config=nodeset_config,
            Start_Day=start
        )

        if ind_property_restrictions:
            itn_event.Event_Coordinator_Config.Intervention_Config.Property_Restrictions_Within_Node = ind_property_restrictions

        if node_property_restrictions:
            itn_event.Event_Coordinator_Config.Intervention_Config.Node_Property_Restrictions = node_property_restrictions
    else:
        if trigger_condition_list:
            if triggered_campaign_delay:
                trigger_condition_list = [triggered_campaign_delay_event(config_builder, start, nodeIDs,
                                                                         triggered_campaign_delay,
                                                                         trigger_condition_list,
                                                                         duration)]

            itn_event = CampaignEvent(
                Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                    Intervention_Config=NodeLevelHealthTriggeredIV(
                        Demographic_Coverage=coverage_all,
                        Duration=duration,
                        Target_Residents_Only=True,
                        Trigger_Condition_List=trigger_condition_list,
                        Property_Restrictions_Within_Node=ind_property_restrictions,
                        Node_Property_Restrictions=node_property_restrictions,
                        Actual_IndividualIntervention_Config=itn_campaign
                    )
                ),
                Nodeset_Config=nodeset_config,
                Start_Day=start
            )
        else:
            itn_event = CampaignEvent(
                Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                    Intervention_Config=itn_campaign,
                    Target_Demographic=StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.Everyone,
                    Demographic_Coverage=coverage_all,
                    Property_Restrictions_Within_Node=ind_property_restrictions,
                    Node_Property_Restrictions=node_property_restrictions,
                    Duration=duration
                ),
                Nodeset_Config=nodeset_config,
                Start_Day=start
            )

    config_builder.add_event(itn_event)