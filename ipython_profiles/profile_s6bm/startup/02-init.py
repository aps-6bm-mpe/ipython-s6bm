print(f'Enter {__file__}...')
# ----- generalized initialization ----- #

class RuntimeMode():

    def __init__(self):
        self._mode = 'debug'
        self.set(mode='debug')

    def __repr__(self):
        return f"Current runtime mode is set to: {self._mode} ['debug', 'dryrun', 'production']"

    def set(self, mode='debug', config=None):
        """
        (Re)-initialize all devices based on given mode
        simulated devices <-- debug
        actual devices    <-- dryrun, production
        """
        if mode.lower() not in ['debug', 'dryrun', 'production']:
            raise ValueError(f"Unknown mode: {mode}")
        else:
            self._mode = mode
        
        global A_shutter
        global suspend_A_shutter
        global tomostage
        global preci, samX, ksamX, ksamZ, samY 
        global psofly
        global det

        # re-init all tomo related devices
        A_shutter = get_shutter(mode=mode)
        tomostage = get_motors(mode=mode) 
        preci     = tomostage.preci              
        samX      = tomostage.samX               
        ksamX     = tomostage.ksamX
        ksamZ     = tomostage.ksamZ        
        samY      = tomostage.samY               
        psofly    = get_fly_motor(mode=mode)
        det       = get_detector(mode=mode)

        # some quick sanity check production mode
        import apstools.devices as APS_devices
        aps = APS_devices.ApsMachineParametersDevice(name="APS")
        suspend_A_shutter = SuspendFloor(A_shutter.pss_state, 1)
        """
        if mode.lower() in ['production']:
            if aps.inUserOperations and (instrument_in_use() in (1, "6-BM-A")) and (not hutch_light_on()):
                
                RE.install_suspender(suspend_A_shutter)
            else:
                raise ValueError("Cannot be in production mode!")
        else:
            pass
        """

        # TODO:
        # initialize all values in the dictionary

mode = RuntimeMode()

print(f"""
🙊: Use mode.set(mode=) to toggle between
    debug :     development mode, no hardware connection
    dryrun:     testing mode, connect to hardware, no beam
    production: ready for experiment
""")

# TODO: define init for other experiment devices

print(f'leaving {__file__}...\n')
