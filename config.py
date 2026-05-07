# All paths are relative to notebooks folder
RAW_DIR = "../../data/raw"
PROCESSED_DIR = "../../data/processed"
OUTPUT_DIR = "../../data/output"

# knmi data dir
KNMI_DIR = f"{RAW_DIR}/knmi"
KNMI_TEMP_DIR = f"{KNMI_DIR}/air_temperature_2021060130-0023H.nc"

# Gemeente dir
GM_DIR = f"{PROCESSED_DIR}/gemeentes"
GM_SHP_DIR = f"{GM_DIR}/corrected/Gemeentes2013TrMr.shp"

# Disease type 1 and 3 outbreak (from WUR) dir

DISEASE_3_INPUT = f"{RAW_DIR}/disease_type_3_outbreak"
DISEASE_3_OUTPUT = f"{PROCESSED_DIR}/disease_type_3_outbreak"

DISEASE_1_INPUT = f"{RAW_DIR}/disease_type_1_outbreak"
DISEASE_1_OUTPUT = f"{PROCESSED_DIR}/disease_type_1_outbreak"

# Disease type 2 foi
FOI_INPUT = f"{PROCESSED_DIR}/foi"
WFOI_OUTPUT = f"{PROCESSED_DIR}/foi/weighted_foi.csv"