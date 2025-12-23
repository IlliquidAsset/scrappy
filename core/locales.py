# Defines the supported locales (e.g., counties, municipalities) for property scraping.
# Each key is a unique locale_code, and the value contains:
#   - "config_path": Path to the JSON configuration file for this locale.
#   - "name": Human-readable name for display purposes (e.g., in CLI prompts).

SUPPORTED_LOCALES = {
    "davidson-tn": {
        "config_path": "configs/davidson-tn.json",
        "name": "Nashville/Davidson County, TN"
    },
    "sumner-tn": {
        "config_path": "configs/sumner-tn.json",
        "name": "Sumner County, TN"
    },
    "montgomery-tn": {
        "config_path": "configs/montgomery-tn.json",
        "name": "Montgomery County, TN"
    }
    # To add a new locale:
    # 1. Create a corresponding JSON configuration file in the 'configs/' directory.
    #    (e.g., configs/new-locale-code.json)
    # 2. Add a new entry here:
    # "new-locale-code": {
    #     "config_path": "configs/new-locale-code.json",
    #     "name": "New Locale Display Name"
    # },
}
