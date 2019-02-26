from dtk.utils.Campaign.CampaignClass import *
from dtk.utils.Campaign.CampaignEnum import *


# Add dengue outbreak individual event
def add_OutbreakIndividualDengue(config_builder, start, coverage_by_age, strain_id_name, nodeIDs=[]):
    """
    Add introduction of new dengue infections to the campaign using
    the **OutbreakIndividualDengue** class. Outbreaks can be recurring.

    Args:
        config_builder: The The :py:class:`DTKConfigBuilder
            <dtk.utils.core.DTKConfigBuilder>` containing the campaign
            configuration.
        start: The day on which to start distributing the intervention
            (**Start_Day** parameter).
        coverage_by_age: The age range of the individuals to target with
            the intervention age, provide a dictionary of ``{'agemin' : x,
            'agemax' : y}``. Default is targeting everyone.
        strain_id_name: The name of the dengue strain.
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.

    Returns:
        None

    Example:
        ::

            config_builder = DTKConfigBuilder.from_defaults(sim_example)
            add_OutbreakIndividualDengue(config_builder, start=1,
                                         coverage_by_age = {"agemin": 1,
                                                            "agemax": 12},
                                         strain_id_name = "DEN-3",
                                         nodeIDs=[3, 6, 8, 12])
    """
    dengue_event = CampaignEvent(
        Start_Day=int(start),
        Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
            Intervention_Config=OutbreakIndividualDengue(
                Strain_Id_Name=strain_id_name,  # eg. "Strain_1"
                Antigen=0,
                Genome=0,
                Comment_antigen_genome="See GitHub https://github.com/InstituteforDiseaseModeling/DtkTrunk/issues/1682",
                Incubation_Period_Override=-1
            )
        )
    )

    if all([k in coverage_by_age.keys() for k in ['min', 'max']]):
        dengue_event.Event_Coordinator_Config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.ExplicitAgeRanges
        dengue_event.Event_Coordinator_Config.Target_Age_Min = coverage_by_age["min"]
        dengue_event.Event_Coordinator_Config.Target_Age_Max = coverage_by_age["max"]

    # not sure else is the correct way to do eg.{min: 0} or {max: 1.725}
    else:
        dengue_event.Event_Coordinator_Config.Demographic_Coverage = 0
        dengue_event.Event_Coordinator_Config.Target_Demographic = StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum.Everyone

    if not nodeIDs:
        dengue_event.Nodeset_Config = NodeSetAll()
    else:
        dengue_event.Nodeset_Config = NodeSetNodeList(Node_List=nodeIDs)

    config_builder.add_event(dengue_event)
