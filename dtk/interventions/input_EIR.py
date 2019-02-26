from dtk.utils.Campaign.CampaignClass import *


def add_InputEIR(cb, monthlyEIRs, age_dependence="SURFACE_AREA_DEPENDENT", start_day=0, nodeIDs=None,
                 ind_property_restrictions=None):
    """
    Create an intervention introducing new malaria infections using the
    **InputEIR** class. If another InputEIR event is distributed to a node
    with an existing InputEIR event, the second one replaces the first (much
    like a new bednet replaces an old bednet).

    Args:
        cb: The :py:class:`DTKConfigBuilder <dtk.utils.core.DTKConfigBuilder>`
            containing the campaign parameters.
        monthlyEIRs: A list of monthly EIRs (must contain 12 items).
        age_dependence: The effect of EIR based on age. Accepted
        values are LINEAR or SURFACE_AREA_DEPENDENT.
        start_day: The day to distribute new infections (**Start_Day**
            parameter).
        nodeIDs: The list of nodes to apply this intervention to (**Node_List**
            parameter). If not provided, set value of NodeSetAll.
        ind_property_restrictions: The IndividualProperty key:value pairs to
            target (**Property_Restrictions_Within_Node** parameter). In the
            format ``[{"IndividualProperty1" : "PropertyValue1"},
            {'IndividualProperty2': "PropertyValue2"}, ...]``

    Returns:
        None

    Example:
        ::

            cb = DTKConfigBuilder.from_defaults(sim_example)
            add_InputEIR(cb, monthlyEIRs=[0.39, 0. 19, 0.77, 0, 0, 0, 6.4, 2.2,
                                          4.7, 3.9, 0.87, 0.58],
                         age_dependence="SURFACE_AREA_DEPENDENT", start_day=1,
                         ind_property_restrictions=[{"Age_Bin":
                         "Age_Bin_Property_From_0_To_6"}])
    """

    nodes = NodeSetNodeList(Node_List=nodeIDs) if nodeIDs else NodeSetAll()
    if ind_property_restrictions is None:
        ind_property_restrictions = []

    if len(monthlyEIRs) is not 12:
        raise Exception('The input argument monthlyEIRs should have 12 entries, not %d' % len(monthlyEIRs))

    input_EIR_event = CampaignEvent(
        Event_Name="Input EIR intervention",
        Start_Day=start_day,
        Event_Coordinator_Config=StandardInterventionDistributionEventCoordinator(
            Number_Repetitions=-1,
            Intervention_Config=InputEIR(
                Age_Dependence=InputEIR_Age_Dependence_Enum[age_dependence],
                Monthly_EIR=monthlyEIRs
            )
        ),
        Nodeset_Config=nodes
    )

    if ind_property_restrictions:
        input_EIR_event.Event_Coordinator_Config.Intervention_Config["Property_Restrictions_Within_Node"] = ind_property_restrictions

    cb.add_event(input_EIR_event)