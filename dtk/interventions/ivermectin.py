import copy
from dtk.utils.Campaign.CampaignClass import *
from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event


# Ivermectin parameters
ivermectin_cfg = Ivermectin(
    Killing_Config=WaningEffectBox(
        Box_Duration=1,
        Initial_Effect=0.95
    ),
    Cost_To_Consumer=15.0
)

# set up events to broadcast when receiving campaign drug
receiving_IV_event = BroadcastEvent(Broadcast_Event="Received_Ivermectin")


def ivermectin_config_by_duration(drug_code=None):
    """
    Provide the duration of ivermectin efficacy and return the correct
    **Killing_Config** dictionary using the **WaningEffectBox** class.

    Args:
        drug_code: The duration of drug efficacy. Supported values are:

            * DAY
            * WEEK
            * MONTH
            * XDAYS where "X" is an integer.

    Returns:
         A dictionary with the correct **Killing_Config** and box duration set.
    """

    if not drug_code:
        return {}
    cfg = copy.deepcopy(ivermectin_cfg)
    if isinstance(drug_code, str):
        if drug_code == 'DAY':
            cfg.Killing_Config.Box_Duration = 1
        elif drug_code == 'WEEK':
            cfg.Killing_Config.Box_Duration = 7
        elif drug_code == 'MONTH':
            cfg.Killing_Config.Box_Duration = 30
        elif drug_code == '90DAYS':
            cfg.Killing_Config.Box_Duration = 90
        else:
            raise Exception("Don't recognize drug_code" % drug_code)
    elif isinstance(drug_code, (int, float)):
        cfg.Killing_Config.Box_Duration = drug_code
    else:
        raise Exception("Drug code should be the IVM duration in days or a string like 'DAY', 'WEEK', 'MONTH'")

    return cfg



def add_ivermectin(config_builder, drug_code, coverage, start_days,
                   trigger_condition_list=None, triggered_campaign_delay=0,
                   listening_duration=-1, nodeids=None, target_residents_only=1,
                   node_property_restrictions=None, ind_property_restrictions=None):

    """
    Add an ivermectin intervention to the campaign using the **Ivermectin**
    class.

    Args:
        config_builder: The :py:class:`DTKConfigBuilder
            <dtk.utils.core.DTKConfigBuilder>` containing the campaign
            configuration.
        drug_code: The duration of drug efficacy. Supported values are:

            * DAY
            * WEEK
            * MONTH
            * XDAYS where "X" is an integer.
        coverage: The proportion of the population covered by the intervention
            (**Demographic_Coverage** parameter).
        start_days: A list of days when ivermectin is distributed
            (**Start_Day** parameter).
        trigger_condition_list: A list of the events that will
            trigger the ivermectin intervention. If included, **start_days** is
            then used to distribute **NodeLevelHealthTriggeredIV**.
        triggered_campaign_delay: After the trigger is received, the number of
            time steps until distribution starts. Eligibility of people or nodes
            for the campaign is evaluated on the start day, not the triggered
            day.
        listening_duration: The number of time steps that the distributed
            event will monitor for triggers. Default is -1, which is
            indefinitely.
        target_residents_only: Set to 1 to target only residents of the node;
            set to 0 to target all individuals, including those who are
            traveling.
        node_property_restrictions: The NodeProperty key:value pairs that
            nodes must have to receive the intervention
            (**Node_Property_Restrictions** parameter). In the format
            ``[{"Place":"RURAL"}, {"ByALake":"Yes}]``.
        ind_property_restrictions: The IndividualProperty key:value pairs
            that individuals must have to receive the intervention
            (**Property_Restrictions_Within_Node** parameter). In the format
            ``[{"BitingRisk":"High"}, {"IsCool":"Yes}]``.

    Returns:
        None

    """

    if node_property_restrictions is None:
        node_property_restrictions = []
    if ind_property_restrictions is None:
        ind_property_restrictions = []


    cfg = ivermectin_config_by_duration(drug_code)

    cfg = [cfg] + [receiving_IV_event]

    intervention_cfg = MultiInterventionDistributor(Intervention_List=cfg)

    if triggered_campaign_delay > 0:
        trigger_condition_list = [triggered_campaign_delay_event(config_builder, start_days[0],
                                                                 nodeIDs=nodeids,
                                                                 triggered_campaign_delay=triggered_campaign_delay,
                                                                 trigger_condition_list=trigger_condition_list,
                                                                 listening_duration=listening_duration,
                                                                 node_property_restrictions=node_property_restrictions)]

    if nodeids:
        node_cfg = NodeSetNodeList(Node_List=nodeids)
    else:
        node_cfg = NodeSetAll()

    for start_day in start_days:
        IVM_event = CampaignEvent(
            Start_Day=start_day,
            Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(),
            Nodeset_Config=node_cfg
        )

        if trigger_condition_list:
            IVM_event.Event_Coordinator_Config.Intervention_Config = NodeLevelHealthTriggeredIV(
                Trigger_Condition_List=trigger_condition_list,
                Target_Residents_Only=target_residents_only,
                Property_Restrictions_Within_Node=ind_property_restrictions,
                Node_Property_Restrictions=node_property_restrictions,
                Duration=listening_duration,
                Demographic_Coverage=coverage,
                Actual_IndividualIntervention_Config=intervention_cfg
            )
        else:
            IVM_event.Event_Coordinator_Config.Target_Residents_Only = True if target_residents_only else False
            IVM_event.Event_Coordinator_Config.Demographic_Coverage = coverage
            IVM_event.Event_Coordinator_Config.Property_Restrictions_Within_Node=ind_property_restrictions
            IVM_event.Event_Coordinator_Config.Node_Property_Restrictions=node_property_restrictions
            IVM_event.Event_Coordinator_Config.Intervention_Config = intervention_cfg

        config_builder.add_event(IVM_event)
