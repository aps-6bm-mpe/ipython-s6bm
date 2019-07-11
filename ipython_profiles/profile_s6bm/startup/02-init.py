# ----- generalized initialization ----- #
keywords_reserved.append('init_tomo()')
def init_tomo(mode='debug', config=None):
    """
    (Re)-initialize all devices based on given mode
        simulated devices <-- debug
        actual devices    <-- dryrun, production
    """
    global tomostage
    global preci, samX, ksamx, samY 
    global psofly
    global det

    # some quick sanity check production mode
    import apstools.devices as APS_devices
    aps = APS_devices.ApsMachineParametersDevice(name="APS")
    if mode.lower() == 'production':
        if aps.inUserOperations and (instrument_in_use() in (1, "6-BM-A")) and (not hutch_light_on()):
            pass
        else:
            raise ValueError("Cannot be in production mode!")
    else:
        pass
                    
    # re-init all tomo related devices
    A_shutter = get_shutter(mode=mode)
    tomostage = get_motors(mode=mode) 
    preci = tomostage.preci              
    samX = tomostage.samX               
    ksamx = tomostage.ksamx    
    samY = tomostage.samY               
    psofly = get_fly_motor(mode=mode)
    det = get_detector(mode=mode)

    # TODO:
    # initialize all values in the dictionary

print(f"""
🙊: Use init_tomo() to toggle between
    debug :     development mode, no hardware connection
    dryrun:     testing mode, connect to hardware, no beam
    production: ready for experiment
""")

# TODO: define init for other experiment devices
