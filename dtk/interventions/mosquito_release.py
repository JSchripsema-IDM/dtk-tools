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
        repetitions: The number of times to repeat the intervention
            (**Number_Repetitions** parameter).
        tsteps_btwn:  The number of time steps between repetitions.
        start_day: The day of the first release (**Start_Day** parameter).

    Returns:
        None
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
