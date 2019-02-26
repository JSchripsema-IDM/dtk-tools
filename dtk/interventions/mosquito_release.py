from dtk.utils.Campaign.utils.RawCampaignObject import RawCampaignObject

def add_mosquito_release(cb, start_day, species, number=100, repetitions=-1, tsteps_btwn=365, gender='VECTOR_FEMALE',
                         released_genome=[['X', 'X']], released_wolbachia="VECTOR_WOLBACHIA_FREE",
                         nodes={"class": "NodeSetAll"}):
    """
    Add repeated mosquito release events to the campaign using the
    **MosquitoRelease** class.

    Args:
        cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign configuration.
        start_day: The day of the first release (**Start_Day** parameter).
        species: The name of the released mosquito species (**Released_Species**
            parameter).
        number: The number of mosquitoes released by the intervention
            (**Released_Number** parameter).
        repetitions: The number of times to repeat the intervention
            (**Number_Repetitions** parameter).
        tsteps_btwn:  The number of time steps between repetitions.
        gender: The gender of the released mosquitoes (VECTOR_FEMALE OR
            VECTOR_MALE).
        released_genome: A list of allele pairs for each gene in the vector
            genome. Gender is specified using ["X", "X"] or ["X", "Y"].
        released_wolbachia: The Wolbachia type of released mosquitoes. Possible
            values are:

            * WOLBACHIA_FREE
            * VECTOR_WOLBACHIA_A
            * VECTOR_WOLBACHIA_B
            * VECTOR_WOLBACHIA_AB

        nodes: The dictionary defining the nodes this intervention applies to
            (**Nodeset_Config** parameter).

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            nodes = {"class": "NodeSetNodeList", "Node_List": [1, 5, 9, 34]}
            add_mosquito_release(cb, start_day=1, species="gambiae", number=100,
            repetitions=4, tsteps_btwn=365, gender='VECTOR_FEMALE',
                             released_genome=[['X', 'X']],
                             released_wolbachia="VECTOR_WOLBACHIA_A", nodes)
    """
    release_event = { "class" : "CampaignEvent",
                      "Event_Name" : "Mosquito Release",
                        "Start_Day": start_day,
                        "Event_Coordinator_Config": {
                            "class": "StandardInterventionDistributionEventCoordinator",
                            "Number_Distributions": -1,
                            "Number_Repetitions": repetitions,
                            "Timesteps_Between_Repetitions": tsteps_btwn,
                            "Target_Demographic": "Everyone",
                            "Intervention_Config": {        
                                    "Released_Number": number, 
                                    "Released_Species": species, 
                                    "Released_Gender": gender,
                                    "Released_Wolbachia": "VECTOR_WOLBACHIA_FREE",
                                    "Released_Genome": released_genome,
                                    "class": "MosquitoRelease"
                                } 
                            },
                        "Nodeset_Config": nodes
                        }

    cb.add_event(RawCampaignObject(release_event))
