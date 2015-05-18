def drug_configs_from_code(cb,drug_code):
    dosing_type = drug_cfg[drug_code]["dosing"]
    drug_array = drug_cfg[drug_code]["drugs"]

    cb.set_param("PKPD_Model", "CONCENTRATION_VERSUS_TIME")

    drug_configs = []
    for drug in drug_array:
        cb.config["parameters"]["Malaria_Drug_Params"][drug] = drug_params[drug]
        drug_intervention = {
            "class": "AntimalarialDrug",
            "Drug_Type": drug,
            "Dosing_Type": dosing_type,
            "Cost_To_Consumer": 1.5
        }
        drug_configs.append(drug_intervention)
    return drug_configs

# Distribute drug campaigns
def add_drug_campaign(cb, drug_code, start_days, coverage=1.0, repetitions=3, interval=60):

    drug_configs = drug_configs_from_code(cb,drug_code)

    for start_day in start_days:
        drug_event = {
            "class": "CampaignEvent",
            "Start_Day": start_day,
            "Event_Coordinator_Config": {
                "class": "MultiInterventionEventCoordinator",
                "Target_Demographic": "Everyone",
                "Demographic_Coverage": coverage,
                "Intervention_Configs": drug_configs,
                "Number_Repetitions": repetitions,
                "Timesteps_Between_Repetitions": interval
                }, 
            "Nodeset_Config": {
                "class": "NodeSetAll"
                }
            }

        cb.add_event(drug_event)

def set_drug_param(cb,drugname,parameter,value):
    cb.config['parameters']['Malaria_Drug_Params'][drugname][parameter]=value

def get_drug_param(cb,drugname,parameter):
    try:
        return cb.config['parameters']['Malaria_Drug_Params'][drugname][parameter]
    except:
        print('Unable to get parameter %s for drug %s' % (parameter,drugname))
        return None

# Definitions of drug blocks
drug_params = {

  # Parameterized according to simple model and 50 kg person
  "Artemether": {
     # Drug PkPd
    "Drug_Cmax": 114,                    # dose/(Vc+Vp)*0.5
    "Drug_Decay_T1": 0.12, 
    "Drug_Decay_T2": 0.12, 
    "Drug_Vd": 1, 
    "Drug_PKPD_C50": 0.6,                # based on 2 nM IC50

    # Treatment regimen
    "Drug_Fulltreatment_Doses": 6, 
    "Drug_Dose_Interval": 0.5, 

    # These are daily parasite killing rates for:
     # These are daily parasite killing rates for:
    "Drug_Gametocyte02_Killrate": 2.5,   # ... gametocyte - early stages
    "Drug_Gametocyte34_Killrate": 1.5,   # ...            - late stages
    "Drug_GametocyteM_Killrate":  0.7,   # ...            - mature
    "Drug_Hepatocyte_Killrate":   0.0,   # ... hepatocytes
    "Max_Drug_IRBC_Kill":         8.9,   # ... asexual parasites
    #"Max_Drug_IRBC_Kill":         2.9,   # ... asexual parasites, drug resistant

    # Adherence rate for subsequent doses
    "Drug_Adherence_Rate" : 1.0,

    # Cmax modifications due to age-based dosing and bodyweight-dependence Vd
    "Bodyweight_Exponent": 1,
    "Fractional_Dose_By_Upper_Age": [{"Upper_Age_In_Years": 3, "Fraction_Of_Adult_Dose": 0.25},{"Upper_Age_In_Years": 6, "Fraction_Of_Adult_Dose": 0.5},{"Upper_Age_In_Years": 10, "Fraction_Of_Adult_Dose": 0.75}]
  },

  "Lumefantrine": {
     # Drug PkPd
    "Drug_Cmax": 1017,
    "Drug_Decay_T1": 1.3, 
    "Drug_Decay_T2": 2.0, 
    "Drug_Vd": 1.2, 
    "Drug_PKPD_C50": 280, 

    # Treatment regimen
    "Drug_Fulltreatment_Doses": 6, 
    "Drug_Dose_Interval": 0.5, 

    # These are daily parasite killing rates for:
    "Drug_Gametocyte02_Killrate": 2.4,   # ... gametocyte - early stages
    "Drug_Gametocyte34_Killrate": 0.0,   # ...            - late stages
    "Drug_GametocyteM_Killrate":  0.0,   # ...            - mature
    "Drug_Hepatocyte_Killrate":   0.0,   # ... hepatocytes
    "Max_Drug_IRBC_Kill":         4.8,   # ... asexual parasites

    # Adherence rate for subsequent doses
    "Drug_Adherence_Rate" : 1.0,

    # Cmax modifications due to age-based dosing and bodyweight-dependence Vd
    "Bodyweight_Exponent": 0.35,
    "Fractional_Dose_By_Upper_Age": [{"Upper_Age_In_Years": 3, "Fraction_Of_Adult_Dose": 0.25},{"Upper_Age_In_Years": 6, "Fraction_Of_Adult_Dose": 0.5},{"Upper_Age_In_Years": 10, "Fraction_Of_Adult_Dose": 0.75}]
  },

  "DHA": {
     # Drug PkPd
    "Drug_Cmax": 200, 
    "Drug_Decay_T1": 0.12, 
    "Drug_Decay_T2": 0.12, 
    "Drug_Vd": 1, 
    "Drug_PKPD_C50": 0.6, 

    # Treatment regimen
    "Drug_Fulltreatment_Doses": 3, 
    "Drug_Dose_Interval": 1, 

    # These are daily parasite killing rates for:
    "Drug_Gametocyte02_Killrate": 2.5,   # ... gametocyte - early stages
    "Drug_Gametocyte34_Killrate": 1.5,   # ...            - late stages
    "Drug_GametocyteM_Killrate":  0.7,   # ...            - mature
    "Drug_Hepatocyte_Killrate":   0.0,   # ... hepatocytes
    "Max_Drug_IRBC_Kill":         9.2,   # ... asexual parasites
    #"Max_Drug_IRBC_Kill":         3.2,   # ... asexual parasites, drug resistant

    # Adherence rate for subsequent doses
    "Drug_Adherence_Rate" : 1.0,

    # Cmax modifications due to age-based dosing and bodyweight-dependence Vd
    "Bodyweight_Exponent": 1,
    # current sigma-tau dosing
    #"Fractional_Dose_By_Upper_Age": [{"Upper_Age_In_Years": 2, "Fraction_Of_Adult_Dose": 0.17},{"Upper_Age_In_Years": 6, "Fraction_Of_Adult_Dose": 0.33},{"Upper_Age_In_Years": 11, "Fraction_Of_Adult_Dose": 0.67}]
    # dosing recommended by Tarning CPT 2012
    "Fractional_Dose_By_Upper_Age": [{"Upper_Age_In_Years": 0.83, "Fraction_Of_Adult_Dose": 0.375},{"Upper_Age_In_Years": 2.83, "Fraction_Of_Adult_Dose": 0.5},{"Upper_Age_In_Years": 5.25, "Fraction_Of_Adult_Dose": 0.625},
                                     {"Upper_Age_In_Years": 7.33, "Fraction_Of_Adult_Dose": 0.75}, {"Upper_Age_In_Years": 9.42, "Fraction_Of_Adult_Dose": 0.875}]
  },

  "Piperaquine": {
     # Drug PkPd
    "Drug_Cmax": 30,#10.4, 
    "Drug_Decay_T1": 0.17, 
    "Drug_Decay_T2": 41, 
    "Drug_Vd": 49, 
    "Drug_PKPD_C50": 5, 

    # Treatment regimen
    "Drug_Fulltreatment_Doses": 3, 
    "Drug_Dose_Interval": 1, 

    # These are daily parasite killing rates for:
    "Drug_Gametocyte02_Killrate": 2.3,   # ... gametocyte - early stages
    "Drug_Gametocyte34_Killrate": 0.0,   # ...            - late stages
    "Drug_GametocyteM_Killrate":  0.0,   # ...            - mature
    "Drug_Hepatocyte_Killrate":   0.0,   # ... hepatocytes
    "Max_Drug_IRBC_Kill":         4.6,   # ... asexual parasites

    # Adherence rate for subsequent doses
    "Drug_Adherence_Rate" : 1.0,

    # Cmax modifications due to age-based dosing and bodyweight-dependence Vd
    "Bodyweight_Exponent": 0,
    # current sigma-tau dosing
    #"Fractional_Dose_By_Upper_Age": [{"Upper_Age_In_Years": 2, "Fraction_Of_Adult_Dose": 0.17},{"Upper_Age_In_Years": 6, "Fraction_Of_Adult_Dose": 0.33},{"Upper_Age_In_Years": 11, "Fraction_Of_Adult_Dose": 0.67}]
    # dosing recommended by Tarning CPT 2012
    "Fractional_Dose_By_Upper_Age": [{"Upper_Age_In_Years": 0.83, "Fraction_Of_Adult_Dose": 0.375},{"Upper_Age_In_Years": 2.83, "Fraction_Of_Adult_Dose": 0.5},{"Upper_Age_In_Years": 5.25, "Fraction_Of_Adult_Dose": 0.625},
                                     {"Upper_Age_In_Years": 7.33, "Fraction_Of_Adult_Dose": 0.75}, {"Upper_Age_In_Years": 9.42, "Fraction_Of_Adult_Dose": 0.875}]
  },
  
  "Primaquine" : {
     # Drug PkPd
    "Drug_Cmax": 75, #19.5 for 0.065 mg.kg, 30 for 0.1mg/kg, 75 for 0.25 mg/kg, 120 for 0.4 mg/kg, 225 for 0.75 mg/kg
    "Drug_Decay_T1": 0.36, 
    "Drug_Decay_T2": 0.36, 
    "Drug_Vd": 1, 
    "Drug_PKPD_C50": 15,#183, 

    # Treatment regimen
    "Drug_Fulltreatment_Doses": 1, #cmax and dosing for single 45 mg (adult) dose
    "Drug_Dose_Interval": 1, 

    # These are daily parasite killing rates for:
    "Drug_Gametocyte02_Killrate": 2.0,   # ... gametocyte - early stages
    "Drug_Gametocyte34_Killrate": 5.0,   # ...            - late stages
    "Drug_GametocyteM_Killrate":  50.0,   # ...            - mature
    "Drug_Hepatocyte_Killrate":   0.1,   # ... hepatocytes
    "Max_Drug_IRBC_Kill":         0.0,   # ... asexual parasites

    # Adherence rate for subsequent doses
    "Drug_Adherence_Rate" : 1.0,

    # Cmax modifications due to age-based dosing and bodyweight-dependence Vd
    "Bodyweight_Exponent": 1,
    "Fractional_Dose_By_Upper_Age": [{"Upper_Age_In_Years": 5, "Fraction_Of_Adult_Dose": 0.17},{"Upper_Age_In_Years": 9, "Fraction_Of_Adult_Dose": 0.33},{"Upper_Age_In_Years": 14, "Fraction_Of_Adult_Dose": 0.67}]
  },

    "Vehicle": { #empty drug
     # Drug PkPd
    "Drug_Cmax": 10,
    "Drug_Decay_T1": 1, 
    "Drug_Decay_T2": 1, 
    "Drug_Vd": 10, 
    "Drug_PKPD_C50": 5, 

    # Treatment regimen
    "Drug_Fulltreatment_Doses": 1, 
    "Drug_Dose_Interval": 1, 

    # These are daily parasite killing rates for:
    "Drug_Gametocyte02_Killrate": 0.0,   # ... gametocyte - early stages
    "Drug_Gametocyte34_Killrate": 0.0,   # ...            - late stages
    "Drug_GametocyteM_Killrate":  0.0,   # ...            - mature
    "Drug_Hepatocyte_Killrate":   0.0,   # ... hepatocytes
    "Max_Drug_IRBC_Kill":         0.0,   # ... asexual parasites
  }
}


# Different configurations of regimens and drugs
drug_cfg = {
    "MSAT_ALP": {
        "dosing" : "FullTreatmentNewDetectionTech",
        "drugs" : ["Artemether", "Lumefantrine", "Primaquine"]
    },
    "MSAT_AL": {
        "dosing" : "FullTreatmentNewDetectionTech",
        "drugs" : ["Artemether", "Lumefantrine"]
    },
    "MDA_AL": {
        "dosing" : "FullTreatmentCourse",
        "drugs" : ["Artemether", "Lumefantrine"]
    },
    "MDA_ALP": {
        "dosing" : "FullTreatmentCourse",
        "drugs" : ["Artemether", "Lumefantrine", "Primaquine"]
    },
    "MSAT_DP": {
        "dosing" : "FullTreatmentNewDetectionTech",
        "drugs" : ["DHA", "Piperaquine"]
    },
    "MSAT_DPP": {
        "dosing" : "FullTreatmentNewDetectionTech",
        "drugs" : ["DHA", "Piperaquine", "Primaquine"]
    },
    "MSAT_PPQ": {
        "dosing" : "FullTreatmentNewDetectionTech",
        "drugs" : ["Piperaquine"]
    },
    "MSAT_DHA_PQ": {
        "dosing" : "FullTreatmentNewDetectionTech",
        "drugs" : ["DHA", "Primaquine"]
    },
    "MSAT_DHA": {
        "dosing" : "FullTreatmentNewDetectionTech",
        "drugs" : ["DHA"]
    },
    "MSAT_PMQ": {
        "dosing" : "FullTreatmentNewDetectionTech",
        "drugs" : ["Primaquine"]
    },
    "MDA_DP": {
        "dosing" : "FullTreatmentCourse",
        "drugs" : ["DHA", "Piperaquine"]
    },
    "MDA_PPQ": {
        "dosing" : "FullTreatmentCourse",
        "drugs" : ["Piperaquine"]
    },
    "MDA_DPP": {
        "dosing" : "FullTreatmentCourse",
        "drugs" : ["DHA", "Piperaquine", "Primaquine"]
    },
    "MDA_PMQ": {
        "dosing" : "FullTreatmentCourse",
        "drugs" : ["Primaquine"]
    },
    "MDA_Vehicle": {
        "dosing" : "FullTreatmentCourse",
        "drugs" : ["Vehicle"]
    }
}