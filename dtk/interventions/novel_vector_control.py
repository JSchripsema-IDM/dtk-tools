from dtk.utils.Campaign.CampaignClass import *


def add_ATSB(cb, start=0, coverage=0.15, kill_cfg=None, duration=180, duration_std_dev=14,
             nodeIDs=None, node_property_restrictions=None):
    """
    Add an attractive targeted sugar bait (ATSB) intervention (**SugarTrap** class) using the
    **StandardInterventionDistributionEventCoordinator**.

    Args:
        cb: The The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>` 
            containing the campaign configuration.
        start: The day on which to start distributing the intervention (**Start_Day** parameter).
        coverage: The proportion of the population that will receive the 
            intervention (**Demographic_Coverage** parameter).
        kill_cfg: The killing efficacy and waning of ATSB (**Killing_Config** 
            parameter) and species (optional, will be added based on the 
            configuration file if not included).
        duration: The length of time the ATSB is active for, independent
            of the waning profile of killing. This allows the node to prematurely
            get rid of the ATSB, much like **UsageDependentBednet** allows
            bednet users to get rid of good bednets. The expiration time
            is drawn from a Gaussian distribution with (mu, s) = (**duration**,
            **duration_std_dev**). 
        duration_std_dev: Width of the Gaussian distribution from which 
            the ATSB expiration time is drawn.
        nodeIDs: The list of nodes to apply this intervention to 
            (**Node_List** parameter). If not provided, set value of NodeSetAll.
        node_property_restrictions: The NodeProperty key:value pairs that 
            nodes must have to receive the intervention (**Node_Property_Restrictions** 
            parameter).

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            kill_cfg = {"class": "WaningEffectBox", "Box_Duration": 120,
                        "Initial_Effect": 0.35}
            add_ATSB(cb, start=30, coverage=0.15, kill_cfg,
                     duration=90, duration_std_dev=7,
                     node_property_restrictions= [{"Place": "Rural"}])
    """

    cfg_species = [x for x in cb.get_param('Vector_Species_Names') if cb.get_param('Vector_Species_Params')[x]['Vector_Sugar_Feeding_Frequency'] != 'VECTOR_SUGAR_FEEDING_NONE']
    atsb_master = WaningEffectBoxExponential(Initial_Effect=0.0337*coverage,
                                             Box_Duration=180,
                                             Decay_Time_Constant=30)

    # default killing cfg
    killing_cfg = [{'Species': sp,
                    'Killing_Config': atsb_master} for sp in cfg_species]

    # if user has specified a kill cfg, just use dicts rather than CampaignClasses. If user doesn't specified a kill cfg,
    # use the default killing cfg
    if kill_cfg :
        # if user-inputed killing cfg is dict and species not specified, make a list
        if isinstance(kill_cfg, dict) :
            if 'Killing_Config' not in kill_cfg:
                raise ValueError('Each config in SugarTrap killing config list must contain Killing_Config')
            else:
                kill_cfg['Killing_Config']['Initial_Effect'] *= coverage
            if 'Species' not in kill_cfg :
                killing_cfg = [{'Species': sp,
                                'Killing_Config': kill_cfg['Killing_Config']} for sp in cfg_species]
            else :
                killing_cfg = [kill_cfg]
        # if user-inputed killing cfg is list, check if each listed species is sugar-feeding species in config.
        elif isinstance(kill_cfg, list) :
            for x in kill_cfg :
                if 'Species' not in x :
                    raise ValueError('Each config in SugarTrap killing config list must contain species name')
                elif 'Killing_Config' not in x:
                    raise ValueError('Each config in SugarTrap killing config list must contain Killing_Config')
                else:
                    x['Killing_Config']['Initial_Effect'] *= coverage
            listed_sp = [x['Species'] for x in kill_cfg]
            if any([x not in cfg_species for x in listed_sp]) :
                raise ValueError('A targeted SugarTrap species is not a sugar-feeding species in config')
            killing_cfg = [x for x in kill_cfg if x['Species'] in cfg_species]
        else :
            raise ValueError('Invalid SugarTrap killing config')

    atsb_config = SugarTrap(
        Cost_To_Consumer=3.75,
        Killing_Config_Per_Species=killing_cfg,
        Expiration_Distribution_Type="GAUSSIAN_DURATION",
        Expiration_Period_Mean=duration,
        Expiration_Period_Std_Dev=duration_std_dev
    )

    node_cfg = NodeSetNodeList(Node_List=nodeIDs) if nodeIDs else NodeSetAll()

    ATSB_event = CampaignEvent(
        Start_Day=start,
        Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(Intervention_Config=atsb_config),
        Intervention_Name="Attractive Toxic Sugar Bait",
        Demographic_Coverage=1,
        Node_Property_Restrictions=node_property_restrictions,
        Nodeset_Config=node_cfg
    )

    cb.add_event(ATSB_event)


def add_topical_repellent(config_builder, start, coverage_by_ages, cost=0, initial_blocking=0.95, duration=0.3,
                          repetitions=1, interval=1, nodeIDs=[]):
    """
    Add a topical insect repellent intervention (**SimpleIndividualRepellent** class)
    using the **StandardInterventionDistributionEventCoordinator**.

    Args:
        config_builder: The The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>` containing the 
            campaign configuration.
        start: The day on which to start distributing the intervention (**Start_Day** parameter).
        coverage_by_ages: A list of dictionaries defining the coverage per
            age group or birth-triggered intervention. For example,
            ``[{"coverage":1,"min": 1, "max": 10},{"coverage":1,"min": 11,
            "max": 50}]``
        cost: The cost of each individual application (**Cost_To_Consumer** parameter).
        initial_blocking: The initial blocking effect of the repellent 
            (**Initial_Effect** parameter).
        duration: The duration of the effectiveness (**Box_Duration** 
            parameter with the **WaningEffectBox** class).
        repetitions: The number of times to repeat the intervention 
            (**Number_Repetitions** parameter).
        interval: The timesteps between repeated distributions 
            (**Timesteps_Between_Repetitions** parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            add_topical_repellent(config_builder, start=10,
                                  coverage_by_ages = [{"coverage": 0.9,
                                                       "min": 1,
                                                       "max": 10}],
                                  cost=1, initial_blocking=0.86, duration=0.3,
                                  repetitions=2, interval=1, nodeIDs=[1, 4, 19])
    """

    repellent = {   "class": "SimpleIndividualRepellent",
                    "Event_Name": "Individual Repellent",
                    "Blocking_Config": {
                        "Initial_Effect": initial_blocking,
                        "Box_Duration": duration,
                        "class": "WaningEffectBox"
                    },
                    "Cost_To_Consumer": cost
    }

    for coverage_by_age in coverage_by_ages:

        repellent_event = { "class" : "CampaignEvent",
                          "Start_Day": start,
                          "Event_Coordinator_Config": {
                              "class": "StandardInterventionDistributionEventCoordinator",
                              "Target_Residents_Only" : 0,
                              "Demographic_Coverage": coverage_by_age["coverage"],
                              "Intervention_Config": repellent,
                              "Number_Repetitions": repetitions,
                              "Timesteps_Between_Repetitions": interval
                          }
                        }

        if all([k in coverage_by_age.keys() for k in ['min','max']]):
            repellent_event["Event_Coordinator_Config"].update({
                   "Target_Demographic": "ExplicitAgeRanges",
                   "Target_Age_Min": coverage_by_age["min"],
                   "Target_Age_Max": coverage_by_age["max"]})

        if not nodeIDs:
            repellent_event["Nodeset_Config"] = { "class": "NodeSetAll" }
        else:
            repellent_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

        if 'birth' in coverage_by_age.keys() and coverage_by_age['birth']:
            birth_triggered_intervention = {
                "class": "BirthTriggeredIV",
                "Duration": coverage_by_age.get('duration', -1), # default to forever if  duration not specified
                "Demographic_Coverage": coverage_by_age["coverage"],
                "Actual_IndividualIntervention_Config": repellent
            }

            repellent_event["Event_Coordinator_Config"]["Intervention_Config"] = birth_triggered_intervention
            repellent_event["Event_Coordinator_Config"].pop("Demographic_Coverage")
            repellent_event["Event_Coordinator_Config"].pop("Target_Residents_Only")

        config_builder.add_event(repellent_event)



def add_ors_node(config_builder, start, coverage=1, initial_killing=0.95, duration=30, cost=0,
                 nodeIDs=[]):
    """
    Add an outdoor residential spraying intervention (**SpaceSpraying** class) using **NodeEventCoordinator**.

    Args:
        config_builder: The The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>` 
            containing the campaign configuration.
        start: The day on which to start distributing the intervention 
            (**Start_Day** parameter).
        coverage: The proportion of the population that will receive the 
            intervention (**Demographic_Coverage** parameter).
        initial_killing:  The initial killing effect of the outdoor spraying 
            (**Initial_Effect** parameter).
        duration: The exponential decay constant of the effectiveness 
            (**Decay_Time_Constant** parameter with the **WaningEffectExponential** 
            class).
        cost: The cost of each individual application (**Cost_To_Consumer** 
            parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List** 
            parameter). If not provided, set value of NodeSetAll.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            add_ors_node(config_builder, start=20, coverage=0.8,
                         initial_killing=0.85, duration=45, cost=1,
                         nodeIDs=[1, 4, 7])
    """

    ors_config = {  "Reduction_Config": {
                        "Decay_Time_Constant": 365, 
                        "Initial_Effect": 0, 
                        "class": "WaningEffectBox"
                    }, 
                    "Habitat_Target": "ALL_HABITATS", 
                    "Cost_To_Consumer": cost, 
                    "Killing_Config": {
                        "Decay_Time_Constant": duration, 
                        "Initial_Effect": initial_killing*coverage, 
                        "class": "WaningEffectExponential"
                    }, 
                    "Spray_Kill_Target": "SpaceSpray_FemalesAndMales", 
                    "class": "SpaceSpraying"
                }

    ORS_event = {   "Event_Coordinator_Config": {
                        "Intervention_Config": ors_config,
                        "class": "NodeEventCoordinator"
                    },
                    "Nodeset_Config": {
                        "class": "NodeSetAll"
                    },
                    "Start_Day": start,
                    "Event_Name": "Outdoor Residual Spray",
                    "class": "CampaignEvent"
                }

    if nodeIDs:
        ORS_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

    config_builder.add_event(ORS_event)


def add_larvicide(config_builder, start, coverage=1, initial_killing=1.0, duration=30, cost=0,
                  habitat_target="ALL_HABITATS", nodeIDs=[]):

    """
    Add a larvicide intervention (**Larvicides** class).

    Args:
        config_builder: The The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>` 
            containing the campaign configuration.
        start: The day on which to start distributing the intervention 
            (**Start_Day** parameter).
        coverage: The proportion of the population that will receive the 
            intervention (**Demographic_Coverage** parameter).
        initial_killing:  The initial killing effect of the larvicide 
            (**Initial_Effect** parameter).
        duration: The exponential decay constant of the effectiveness 
            (**Decay_Time_Constant** parameter with the **WaningEffectExponential** class).
        cost: The cost of each individual application (**Cost_To_Consumer** 
            parameter).
        habitat_target: The larval habitat to target (**Habitat_Target** 
            parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List** 
            parameter). If not provided, set value of NodeSetAll.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            add_larvicide(config_builder, start=0, coverage=0.85,
                          initial_killing=0.75, duration=30, cost=1,
                          habitat_target="BRACKISH_SWAMP", nodeIDs=[2, 5, 22])
    """

    larvicide_config = {  "Blocking_Config": {
                        "Decay_Time_Constant": 365, 
                        "Initial_Effect": 0, 
                        "class": "WaningEffectBox"
                    }, 
                    "Habitat_Target": habitat_target, 
                    "Cost_To_Consumer": cost, 
                    "Killing_Config": {
                        "Decay_Time_Constant": duration, 
                        "Initial_Effect": initial_killing*coverage, 
                        "class": "WaningEffectBox"
                    }, 
                    "class": "Larvicides"
                }

    larvicide_event = {   "Event_Coordinator_Config": {
                        "Intervention_Config": larvicide_config, 
                        "class": "NodeEventCoordinator"
                    }, 
                    "Nodeset_Config": {
                        "class": "NodeSetAll"
                    }, 
                    "Start_Day": start, 
                    "Event_Name": "Larvicide",
                    "class": "CampaignEvent"
                }

    if nodeIDs:
        larvicide_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

    config_builder.add_event(larvicide_event)


def add_eave_tubes(config_builder, start, coverage=1, initial_killing=1.0, killing_duration=180, 
                   initial_blocking=1.0, blocking_duration=730, outdoor_killing_discount=0.3, cost=0,
                   nodeIDs=[]):
    """
    Add insecticidal tubes to the eaves of houses (**IRSHousingModification** intervention class).

    Args:
        config_builder: The The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>` 
            containing the campaign configuration.
        start: The day on which to start distributing the intervention 
            (**Start_Day** parameter).
        coverage: The proportion of the population that will receive the intervention 
            (**Demographic_Coverage** parameter).
        initial_killing:  The initial killing effect of the eave tubes 
            (**Initial_Effect** parameter in **Killing_Config**).
        killing_duration: The exponential decay constant of the effectiveness 
            (**Decay_Time_Constant** parameter with the **WaningEffectExponential** 
            class).
        initial_blocking:  The initial blocking effect of the eave tubes 
            (**Initial_Effect** parameter in **Blocking_Config**).
        blocking_duration: The exponential decay constant of the effectiveness 
            (**Decay_Time_Constant** parameter with the **WaningEffectExponential** class).
        outdoor_killing_discount: The value to differentially scale initial 
            killing effect for outdoor vectors vs. indoor vectors.
        cost: The cost of each individual application (**Cost_To_Consumer** parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List** 
            parameter). If not provided, set value of NodeSetAll.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            add_eave_tubes(config_builder, start=7, coverage=0.65,
                           initial_killing=0.85, killing_duration=90,
                           initial_blocking=0.95, blocking_duration=365,
                           outdoor_killing_discount=0.3, cost=1,
                           nodeIDs=[33, 56, 7])
    """

    indoor_config = {   "class": "IRSHousingModification",
                        "Killing_Config": {
                            "Decay_Time_Constant": killing_duration,
                            "Initial_Effect": initial_killing, 
                            "class": "WaningEffectExponential"
                        },
                        "Blocking_Config": {
                            "Decay_Time_Constant": blocking_duration, 
                            "Initial_Effect": initial_blocking, 
                            "class": "WaningEffectExponential"
                        },
                        "Cost_To_Consumer": cost
                        }

    indoor_event = {"class": "CampaignEvent",
                    "Start_Day": start,
                    "Nodeset_Config": {
                        "class": "NodeSetAll"
                    },
                    "Event_Coordinator_Config": {
                        "class": "StandardInterventionDistributionEventCoordinator",
                        "Demographic_Coverage": coverage,
                        "Target_Demographic": "Everyone",
                        "Intervention_Config": indoor_config
                    }
                    }

    if nodeIDs:
        indoor_event["Nodeset_Config"] = { "class": "NodeSetNodeList", "Node_List": nodeIDs }

    config_builder.add_event(indoor_event)
    add_ors_node(config_builder, start, coverage=coverage, 
                 initial_killing=initial_killing*outdoor_killing_discount, 
                 duration=killing_duration, cost=cost, 
                 nodeIDs=nodeIDs)