seir_campaign = {
    "Campaign_Name": "Initial Seeding",
    "Events": [
        {
            "Event_Coordinator_Config": {
                "Demographic_Coverage": 0.0005,
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
            "Start_Day": 1,
            "class": "CampaignEvent"
        }
    ],
    "Use_Defaults": 1
}
