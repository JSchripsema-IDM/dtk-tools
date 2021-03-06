from dtk.utils.Campaign.CampaignClass import *
from dtk.utils.Campaign.CampaignEnum import *


expire_recent_drugs = PropertyValueChanger(
    Target_Property_Key="DrugStatus",
    Target_Property_Value="RecentDrug",
    Daily_Probability=1.0,
    Maximum_Duration=0,
    Revert=0
)


def add_health_seeking(config_builder,
                       start_day=0,
                       targets=[{'trigger': 'NewClinicalCase', 'coverage': 0.8, 'agemin': 15, 'agemax': 70, 'seek': 0.4,
                                 'rate': 0.3},
                                {'trigger': 'NewSevereCase', 'coverage': 0.8, 'seek': 0.6, 'rate': 0.5}],
                       drug=['Artemether', 'Lumefantrine'],
                       dosing='FullTreatmentNewDetectionTech',
                       nodes={"class": "NodeSetAll"},
                       node_property_restrictions=[],
                       ind_property_restrictions=[],
                       disqualifying_properties=[],
                       drug_ineligibility_duration=0,
                       duration=-1,
                       repetitions=1,
                       tsteps_btwn_repetitions=365,
                       broadcast_event_name='Received_Treatment'):

    """
    Add a `SimpleHealthSeekingBehavior <http://www.idmod.org/docs/general/parameter-campaign-individual-simplehealthseekingbehavior.html>`_.

    Args:

        config_builder: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>` containing the campaign configuration
        start_day: The day to start the intervention.
        targets: The different targets of the intervention (see default for an example).
        drug: The drug to administer.
        dosing: The dosing for the drugs.
        nodes: The nodes to target. For all nodes: ``{"class": "NodeSetAll"}``.
           For a subset of nodes: ``{"class": "NodeSetNodeList", "Node_List": list_of_nodeIDs}``.
        node_property_restrictions: The node property values to target; used with NodePropertyRestrictions. For example, ``[{ "NodeProperty1" : "PropertyValue1" }, {'NodeProperty2': "PropertyValue2"}, ...]``
        drug_ineligibility_duration: If this parameter is > 0, use IndividualProperties to prevent people from receiving
            drugs too frequently. The demographics file will need to define the IP DrugStatus with possible values None and
            RecentDrug. Individuals who receive drugs for treatment will have their DrugStatus changed to RecentDrug for
            drug_ineligibility_duration days. Individuals who already have status RecentDrug will not receive drugs for
            treatment.
        duration: The duration of the intervention. 
        repetitions: The number of repetitions.
        tsteps_btwn_repetitions: The number of timesteps between the repetitions.

    .. note:: There is the potential for overlapping treatments in the same individual. 

    :return: Nothing
    """

    receiving_drugs_event = BroadcastEvent(Broadcast_Event=broadcast_event_name)

    if repetitions < 1:
        repetitions = 1

    expire_recent_drugs.Revert = drug_ineligibility_duration

    drug_config, drugs = get_drug_config(drug, dosing, receiving_drugs_event,
                                         drug_ineligibility_duration, expire_recent_drugs)

    for t in targets:

        actual_config = build_actual_treatment_cfg(t['rate'], drug_config, drugs)
        if disqualifying_properties:
            actual_config.Disqualifying_Properties = disqualifying_properties

        health_seeking_config = StandardInterventionDistributionEventCoordinator(
            Number_Repetitions=repetitions,
            Timesteps_Between_Repetitions=tsteps_btwn_repetitions,
            Intervention_Config=NodeLevelHealthTriggeredIV(
                Trigger_Condition_List=[t['trigger']],
                Duration=duration,
                # Tendency=t['seek'],
                Demographic_Coverage=t['coverage'] * t['seek'],  # to be FIXED later for individual properties
                Actual_IndividualIntervention_Config=actual_config
            )
        )

        if ind_property_restrictions :
            health_seeking_config.Intervention_Config.Property_Restrictions_Within_Node = ind_property_restrictions

        if drug_ineligibility_duration > 0:
            drugstatus = {"DrugStatus": "None"}
            if ind_property_restrictions:
                health_seeking_config.Intervention_Config.Property_Restrictions_Within_Node = [
                    dict(drugstatus.items() + x.items()) for x in ind_property_restrictions]
            else:
                health_seeking_config.Intervention_Config.Property_Restrictions_Within_Node = [drugstatus]

        if node_property_restrictions:
            health_seeking_config.Intervention_Config.Node_Property_Restrictions = node_property_restrictions

        if all([k in t.keys() for k in ['agemin', 'agemax']]):
            health_seeking_config.Intervention_Config.Target_Demographic = NodeLevelHealthTriggeredIV_Target_Demographic_Enum.ExplicitAgeRanges  # Otherwise default is Everyone
            health_seeking_config.Intervention_Config.Target_Age_Min = t['agemin']
            health_seeking_config.Intervention_Config.Target_Age_Max = t['agemax']

        health_seeking_event = CampaignEvent(
            Start_Day=start_day,
            Event_Coordinator_Config=health_seeking_config,
            Nodeset_Config=nodes
        )

        config_builder.add_event(health_seeking_event)


def add_health_seeking_by_chw(config_builder,
                               start_day=0,
                               targets=[{'trigger': 'NewClinicalCase', 'coverage': 0.8, 'agemin': 15, 'agemax': 70,
                                         'seek': 0.4, 'rate': 0.3},
                                {'trigger': 'NewSevereCase', 'coverage': 0.8, 'seek': 0.6, 'rate': 0.5}],
                               drug=['Artemether', 'Lumefantrine'],
                               dosing='FullTreatmentNewDetectionTech',
                               nodeIDs=[],
                               node_property_restrictions=[],
                               ind_property_restrictions=[],
                               drug_ineligibility_duration=0,
                               duration=100000,
                               chw={}):

    chw_config = {
        'class': 'CommunityHealthWorkerEventCoordinator',
        'Duration': duration,
        'Distribution_Rate': 5,
        'Waiting_Period': 7,
        'Days_Between_Shipments': 90,
        'Amount_In_Shipment': 1000,
        'Max_Stock': 1000,
        'Initial_Amount_Distribution_Type': CommunityHealthWorkerEventCoordinator_Initial_Amount_Distribution_Type_Enum.FIXED_DURATION,
        'Initial_Amount': 1000,
        'Target_Demographic': CommunityHealthWorkerEventCoordinator_Target_Demographic_Enum.Everyone,
        'Target_Residents_Only': False,
        'Demographic_Coverage': 1,
        'Trigger_Condition_List': ['CHW_Give_Drugs'],
        'Property_Restrictions_Within_Node': []}

    if chw:
        chw_config.update(chw)

    chw_config.pop('class')
    chw_config = CommunityHealthWorkerEventCoordinator(**chw_config)

    receiving_drugs_event = BroadcastEvent(Broadcast_Event='Received_Treatment')

    # NOTE: node property restrictions isn't working yet for CHWEC (3/29/17)
    if node_property_restrictions:
        chw_config.Node_Property_Restrictions = node_property_restrictions

    nodes = NodeSetNodeList(Node_List=nodeIDs) if nodeIDs else NodeSetNodeList()

    add_health_seeking(config_builder, start_day=start_day, targets=targets, drug=[], nodes=nodes,
                       node_property_restrictions=node_property_restrictions,
                       ind_property_restrictions=ind_property_restrictions,
                       duration=duration, broadcast_event_name='CHW_Give_Drugs')

    if drug_ineligibility_duration > 0:
        chw_config.Property_Restrictions_Within_Node.append({"DrugStatus": "None"})

    expire_recent_drugs.Revert = drug_ineligibility_duration
    drug_config, drugs = get_drug_config(drug, dosing, receiving_drugs_event,
                                         drug_ineligibility_duration, expire_recent_drugs)
    actual_config = build_actual_treatment_cfg(0, drug_config, drugs)

    chw_config.Intervention_Config = actual_config

    chw_event = CampaignEvent(
        Start_Day=start_day,
        Event_Coordinator_Config=chw_config,
        Nodeset_Config=nodes
    )

    config_builder.add_event(chw_event)
    return


def get_drug_config(drug, dosing, receiving_drugs_event, drug_ineligibility_duration, expire_recent_drugs) :

    # if drug variable is a list, let's use MultiInterventionDistributor
    if isinstance(drug, str):
        drug_config = AntimalarialDrug(
            Cost_To_Consumer=1,
            Drug_Type=drug,
            Dosing_Type=dosing
        )

        drugs = drug
    else:
        drugs = []
        for d in drug:
            drugs.append(AntimalarialDrug(
                Cost_To_Consumer=1,
                Drug_Type=d,
                Dosing_Type=dosing
            ))

        drugs.append(receiving_drugs_event)
        if drug_ineligibility_duration > 0:
            drugs.append(expire_recent_drugs)

        drug_config = MultiInterventionDistributor(Intervention_List=drugs)

    return drug_config, drugs


def build_actual_treatment_cfg(rate, drug_config, drugs) :

    if rate > 0:
        actual_config = DelayedIntervention(
            Coverage=1.0,
            Delay_Distribution="EXPONENTIAL_DURATION",
            Delay_Period=1.0 / rate,
            Actual_IndividualIntervention_Configs=drugs
        )
    else:
        actual_config = drug_config

    return actual_config