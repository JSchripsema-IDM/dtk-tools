from dtk.utils.Campaign.CampaignClass import *


def recurring_outbreak(cb, outbreak_fraction=0.01, repetitions=-1, tsteps_btwn=365, target='Everyone', start_day=0, strain=(0,0), nodes={"class": "NodeSetAll"}, outbreak_source="PrevalenceIncrease"):
    """
    Add introduction of new infections to the campaign using the
    **OutbreakIndividual** class. Outbreaks can be recurring.

    Args:
        cb: The The :py:class:`DTKConfigBuilder
            <dtk.utils.core.DTKConfigBuilder>` containing the campaign
            configuration.
        outbreak_fraction: The fraction of people infected by the outbreak (
            **Demographic_Coverage** parameter).
        repetitions: The number of times to repeat the intervention.
        tsteps_btwn_:  The number of time steps between repetitions.
        target: The individuals to target with the intervention. To
            restrict by age, provide a dictionary of {'agemin' : x, 'agemax' :
            y}. Default is targeting everyone.
        start_day: The day on which to start distributing the intervention
            (**Start_Day** parameter).
        strain: A two-element tuple defining (Antigen, Genome).
        nodes: A dictionary defining the nodes to apply this intervention to
            (**Nodeset_Config** parameter).
        outbreak_source: The source of the outbreak.

    Returns:
        A dictionary holding the fraction and the time steps between events.

        Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            recurring_outbreak(cb, outbreak_fraction=0.005, repetitions=3,
                               tsteps_btwn=30, target={"agemin": 1, "agemax": 5},
                               start_day=0, strain=("A", "H2N2"),
                               nodes={"class": "NodeSetAll"},
                               outbreak_source="PrevalenceIncrease")

    """


    outbreak_event = CampaignEvent(
        Start_Day=start_day,
        Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
            Number_Distributions=-1,
            Number_Repetitions=repetitions,
            Timesteps_Between_Repetitions=tsteps_btwn,
            Target_Demographic=StandardInterventionDistributionEventCoordinator_Target_Demographic_Enum[target],
            Demographic_Coverage=outbreak_fraction,
            Intervention_Config=OutbreakIndividual(
                Antigen=strain[0],
                Genome=strain[1],
                Outbreak_Source=outbreak_source
            )
        ),
        Nodeset_Config=nodes
    )

    cb.add_event(outbreak_event)
    return {'outbreak_fraction': outbreak_fraction,
            'tsteps_btwn': tsteps_btwn}
