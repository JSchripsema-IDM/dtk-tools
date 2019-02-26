import copy
from dtk.utils.Campaign.CampaignClass import *


default_larvicides = Larvicides(
    Blocking_Config=WaningEffectBoxExponential(
        Box_Duration=100,
        Decay_Time_Constant=150,
        Initial_Effect=0.4
    ),
    Cost_To_Consumer=1.0,
    Habitat_Target=Larvicides_Habitat_Target_Enum.ALL_HABITATS,
    Killing_Config=WaningEffectBoxExponential(
        Box_Duration=100,
        Decay_Time_Constant=150,
        Initial_Effect=0.2
    )
)


def add_larvicides(config_builder, start, killing=None, reduction=None, habitat_target=None, waning=None, nodesIDs = None):

    """
    Add a mosquito larvicide intervention to the campaign using the
    **Larvicides** class.

    Args:
        config_builder: The :py:class:`DTKConfigBuilder
            <dtk.utils.core.DTKConfigBuilder>` containing the campaign
            configuration.
        start: The day on which to start distributing the larvicide
            (**Start_Day** parameter).
        killing: The initial larval killing efficacy (**Initial_Effect** in
            **Killing_Config**).
        reduction: The initial larval habitat reduction efficacy
            (**Initial_Effect** in **Blocking_Config**).
        habitat_target: The larval habitat type targeted by the larvicide
            (**Habitat_Target** parameter).
        waning: A dictionary defining the box duration and decay in efficacy of
            the killing and/or habitat reduction of the larvicide using the
            **WaningEffectBoxExponential** class. If not provided, uses the
            default of 100 days at the given initial efficacy with a
            **Decay_Time_Constant** of 150.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            add_larvicides(config_builder, start=1, killing=0.75,
            reduction=0.9, habitat_target="ALL_HABITATS",
            nodesIDs=[2, 5, 7])
    """
    event = CampaignEvent(
        Start_Day=start,
        Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator()
    )

    # Take care of specified NodeIDs if any
    if not nodesIDs:
        event.Nodeset_Config = NodeSetAll()
    else:
        event.Nodeset_Config = NodeSetNodeList(Node_List=nodesIDs)

    # Copy the default event
    larvicides_event = copy.deepcopy(default_larvicides)

    # Change according to parameters
    if killing:
        larvicides_event.Killing_Config.Initial_Effect = killing

    if reduction:
        larvicides_event.Blocking_Config.Initial_Effect = reduction

    if habitat_target:
        larvicides_event.Habitat_Target = Larvicides_Habitat_Target_Enum[habitat_target]

    if waning:
        if "blocking" in waning:
            for k, v in waning["blocking"].items():
                setattr(larvicides_event.Blocking_Config, k, v)
        if "killing" in waning:
            for k, v in waning["killing"].items():
                setattr(larvicides_event.Killing_Config, k, v)

    # Add the larvicides to the event coordinator
    event.Event_Coordinator_Config.Intervention_Config = larvicides_event

    # Add to the config builder
    config_builder.add_event(event)
