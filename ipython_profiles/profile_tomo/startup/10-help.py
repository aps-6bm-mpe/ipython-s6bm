# document functions defined in the profile


instruction_dict = {
    "in_production": "whether beam line in production mode (ready)",
    "in_dryrun": "testing model flag that supercedes in_production",
    "instrument_in_use()": "check instrument status",
    "hutch_light_on()": "check if hutch light is on",
}

def quick_look(topic=None):
    if topic is None:
        print("Common functionality available")
        print("\n".join([f"{k}:\t{v}" for k,v in instruction_dict.items()]))
    else:
        raise NotImplementedError
