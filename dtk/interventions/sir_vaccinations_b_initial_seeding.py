sir_vaccinations_b_campaign = {
    "Campaign_Name": "Initial Seeding",
    "Events": [
        {
            "Event_Coordinator_Config": {
                "Demographic_Coverage": 0.5,
                "Intervention_Config": {
                    "Cost_To_Consumer": 10,
                    "Reduced_Transmit": 0,
                    "Vaccine_Take": 1,
                    "Vaccine_Type": "AcquisitionBlocking",
                    "Waning_Config": {
                        "Box_Duration": 3650,
                        "Initial_Effect": 1,
                        "class": "WaningEffectBox"
                    },
                    "class": "SimpleVaccine"
                },
                "Number_Repetitions": 3,
                "Target_Demographic": "Everyone",
                "Timesteps_Between_Repetitions": 7,
                "class": "StandardInterventionDistributionEventCoordinator"
            },
            "Nodeset_Config": {
                "class": "NodeSetAll"
            },
            "Start_Day": 1,
            "class": "CampaignEvent"
        },
        {
            "Event_Coordinator_Config": {
                "Demographic_Coverage": 0.001,
                "Intervention_Config": {
                    "Antigen": 0,
                    "Genome": 0,
                    "Outbreak_Source": "PrevalenceIncrease",
                    "class": "OutbreakIndividual"
                },
                "Target_Demographic": "Everyone",
                "class": "StandardInterventionDistributionEventCoordinator"
            },
            "Event_Name": "Outbreak",
            "Nodeset_Config": {
                "class": "NodeSetAll"
            },
            "Start_Day": 30,
            "class": "CampaignEvent"
        }
    ],
    "Use_Defaults": 1
}