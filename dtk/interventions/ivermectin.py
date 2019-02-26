import copy
from dtk.utils.Campaign.CampaignClass import *
from dtk.interventions.triggered_campaign_delay_event import triggered_campaign_delay_event


# Ivermectin parameters
ivermectin_cfg = Ivermectin(
    Killing_Config=WaningEffectBox(
        Box_Duration=7,
        Initial_Effect=0.95
    ),
    Cost_To_Consumer=1.0
)

# set up events to broadcast when receiving campaign drug
receiving_IV_event = BroadcastEvent(Broadcast_Event="Received_Ivermectin")


def ivermectin_config_by_duration(box_duration='WEEK', initial_effect: float=0.95):
    """
    Provide the duration of ivermectin efficacy and return the correct
    **Killing_Config** dictionary using the **WaningEffectBox** class.

    Args:
        drug_code: The duration of drug efficacy. Supported values are:

            * DAY
            * WEEK
            * MONTH
            * XDAYS where "X" is an integer.
        initial_effect: The initial efficacy of the drug treatment.

    Returns:
        A dictionary of ivermectin configuration with the **Box_Duration**
        set to the **drug_code** parameter.
    """

    cfg = copy.deepcopy(ivermectin_cfg)
    if isinstance(box_duration, str):
        if box_duration == 'DAY':
            cfg.Killing_Config.Box_Duration = 1
        elif box_duration == 'WEEK':
            cfg.Killing_Config.Box_Duration = 7
        elif box_duration == 'MONTH':
            cfg.Killing_Config.Box_Duration = 30
        elif box_duration == '90DAYS':
            cfg.Killing_Config.Box_Duration = 90
        else:
            raise ValueError("Don't recognize box_duration : {} \nPlease pass in 'DAY','WEEK','MONTH', or"
                             " '90DAYS'\n".format(box_duration))
    elif isinstance(box_duration, (int, float)):
        cfg.Killing_Config.Box_Duration = box_duration
    else:
        raise ValueError("Please pass in a valid drug code.\nOptions: Sting - 'DAY','WEKK','MONTH', or "
                         "'90DAYS'.\nInt or Float of number of days for the Box_Duration.\n")

    cfg.Killing_Config.Initial_Effect = initial_effect


    return cfg



def add_ivermectin(config_builder, box_duration: any="WEEK", initial_effect: float=0.95, coverage: float=1.0,
                   start_days: list=None, trigger_condition_list: list=None, triggered_campaign_delay: int=0,
                   listening_duration: int=-1, nodeIDs: list=None, target_group: any="Everyone",
                   target_residents_only: bool=1, node_property_restrictions: list=None,
                   ind_property_restrictions: list=None):

    """
    Add an ivermectin intervention to the campaign using the **Ivermectin**
    class.

    Args:
        config_builder: The :py:class:`DTKConfigBuilder
            <dtk.utils.core.DTKConfigBuilder>` containing the campaign
            configuration.
        box_duration: The length of ivermectin effect for **Box_Duration**.
            Accepted values are an integer, float, or one of the following:

            * DAY
            * WEEK
            * MONTH
            * 90DAYS

        initial_effect: The initial efficacy of the drug treatment.
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
        node_IDs: The list of nodes to apply this intervention to (**Node_List**
            parameter).
        target_group: A dictionary targeting an age range and gender of
            individuals for treatment. In the format
            ``{"agemin": x, "agemax": y, "gender": "z"}``.
        target_residents_only: Set to 1 to target only individuals
            who started the simulation in this node and are still in
            this node; set to 0 to target all individuals, including those who are
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

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            add_ivermectin(config_builder, box_duration=45,
                           initial_effect=0.75, coverage=0.8,
                           start_days=[1, 30, 60],
                           trigger_condition_list=["NewClinicalCase", "NewSevereCase"],
                           triggered_campaign_delay=7, listening_duration=-1,
                           nodeIDs=[1, 4, 6],
                           target_group={"agemin": 3,
                                         "agemax": 10,
                                         "gender": "female"},
                           target_residents_only=1,
                           ind_property_restrictions=[{"BitingRisk": "Medium"}])
    """

    if node_property_restrictions is None:
        node_property_restrictions = []
    if ind_property_restrictions is None:
        ind_property_restrictions = []
    if not start_days:
        start_days = [0]
    if nodeIDs:
        node_cfg = NodeSetNodeList(Node_List=nodeIDs)
    else:
        node_cfg = NodeSetAll()

    cfg = [ivermectin_config_by_duration(box_duration, initial_effect), receiving_IV_event]
    intervention_cfg = MultiInterventionDistributor(Intervention_List=cfg)

    if triggered_campaign_delay > 0:
        if not trigger_condition_list:
            raise Exception("When using triggered_campaign_delay, please specify triggered_condition_list, too.\n")
        trigger_condition_list = [triggered_campaign_delay_event(config_builder, start_days[0],
                                                                 nodeIDs=nodeIDs,
                                                                 triggered_campaign_delay=triggered_campaign_delay,
                                                                 trigger_condition_list=trigger_condition_list,
                                                                 listening_duration=listening_duration,
                                                                 ind_property_restrictions=ind_property_restrictions,
                                                                 node_property_restrictions=node_property_restrictions)]

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
                             "{'agemin' : x, 'agemax' : y, 'gender': 'Female'} to target  to individuals between x and "
                             "y years of age, and (optional) gender.\n")

    if trigger_condition_list:
        ivm_event = CampaignEvent(
                    Start_Day=start_days[0],
                    Nodeset_Config=node_cfg,
                    Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                        Intervention_Config=NodeLevelHealthTriggeredIV(
                            Trigger_Condition_List=trigger_condition_list,
                            Target_Residents_Only=target_residents_only,
                            Property_Restrictions_Within_Node=ind_property_restrictions,
                            Node_Property_Restrictions=node_property_restrictions,
                            Duration=listening_duration,
                            Demographic_Coverage=coverage,
                            Target_Demographic=target_group,
                            Target_Age_Min=age_min,
                            Target_Age_Max=age_max,
                            Target_Gender=gender,
                            Actual_IndividualIntervention_Config=intervention_cfg)
                    )
        )
        config_builder.add_event(ivm_event)
    else:
        for start_day in start_days:
                ivm_event = CampaignEvent(
                    Start_Day=start_day,
                    Nodeset_Config=node_cfg,
                    Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
                        Target_Residents_Only=target_residents_only,
                        Demographic_Coverage=coverage,
                        Property_Restrictions_Within_Node=ind_property_restrictions,
                        Node_Property_Restrictions=node_property_restrictions,
                        Target_Demographic=target_group,
                        Target_Age_Min=age_min,
                        Target_Age_Max=age_max,
                        Target_Gender=gender,
                        Intervention_Config=intervention_cfg)
                )
                config_builder.add_event(ivm_event)
