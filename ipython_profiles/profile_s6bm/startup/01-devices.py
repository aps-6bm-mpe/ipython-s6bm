# define devices used for tomo scan at 6BM
_sep = u"🙉"*30
print(f'{_sep}\nInitializing devices on Python end with {__file__}')


# ----
# Shutter
from bluesky.suspenders import SuspendFloor
print("Setting up Shutter")
if in_production:
    # define the real shutter used at 6BMA@APS
    # NOTE: 
    #   this requires connection to the hardware, otherwise a connection error will be raised

    A_shutter = APS_devices.ApsPssShutterWithStatus(
            "6bmb1:rShtrA:",
            "PA:06BM:STA_A_FES_OPEN_PL",
            name="A_shutter",
        )
    A_shutter.pss_state
    # no scans until A_shutter is open
    suspend_A_shutter = SuspendFloor(A_shutter.pss_state, 1)
    # NOTE:
    # since tomo scan take dark field images with shutter colosed, the
    # suspender installation for A_shutter is located in the plan for
    # granular control.
    
    # no scans if aps.current is too low
    suspend_APS_current = SuspendFloor(aps.current, 2, resume_thresh=10)
    RE.install_suspender(suspend_APS_current)

else:
    # for testing during dark time (no beam, shutter closed by APS)
    A_shutter = APS_devices.SimulatedApsPssShutterWithStatus(name="A_shutter")
    suspend_A_shutter = SuspendFloor(A_shutter.pss_state, 1)
    print("---use simulated shutter---")


# ------
# Motors
# -- step motor
from ophyd import MotorBundle
from ophyd import Component
from ophyd import EpicsMotor

class TomoStage(MotorBundle):
    #rotation
    preci = Component(EpicsMotor, "6bmpreci:m1", name='preci')    
    samX = Component(EpicsMotor, "6bma1:m19", name='samX')
    samY = Component(EpicsMotor, "6bma1:m18", name="samY")

print("\nSetting up motors")
if in_production or in_dryrun:
    tomostage = TomoStage(name='tomostage')

    samx  = tomostage.samX
    samy  = tomostage.samY
    preci = tomostage.preci

else:
    tomostage = MotorBundle()
    tomostage.preci = sim.motor
    tomostage.samX = sim.motor
    tomostage.samY = sim.motor
    print("using simulated detectors")

# -- PSOFlyDevice
from ophyd import EpicsSignal
from ophyd import Device
import bluesky.plan_stubs as bps
class TaxiFlyScanDevice(Device):
    """
    BlueSky Device for APS taxi & fly scans
    
    Some EPICS fly scans at APS are triggered by a pair of 
    EPICS busy records. The busy record is set, which triggers 
    the external controls to do the fly scan and then reset 
    the busy record. 
    
    The first busy is called taxi and is responsible for 
    preparing the hardware to fly. 
    The second busy performs the actual fly scan. 
    In a third (optional) phase, data is collected 
    from hardware and written to a file.
    """
    taxi = Component(EpicsSignal, "taxi", put_complete=True)
    fly = Component(EpicsSignal, "fly", put_complete=True)
    
    def plan(self):
        yield from bps.mv(self.taxi, self.taxi.enum_strs[1])
        yield from bps.mv(self.fly, self.fly.enum_strs[1])

class EnsemblePSOFlyDevice(TaxiFlyScanDevice):
    motor_pv_name = Component(EpicsSignalRO, "motorName")
    start = Component(EpicsSignal, "startPos")
    end = Component(EpicsSignal, "endPos")
    slew_speed = Component(EpicsSignal, "slewSpeed")

    # scan_delta: output a trigger pulse when motor moves this increment
    scan_delta = Component(EpicsSignal, "scanDelta")

    # advanced controls
    delta_time = Component(EpicsSignalRO, "deltaTime")
    # detector_setup_time = Component(EpicsSignal, "detSetupTime")
    # pulse_type = Component(EpicsSignal, "pulseType")

    scan_control = Component(EpicsSignal, "scanControl")

# make the fly motor
psofly = EnsemblePSOFlyDevice("6bmpreci:eFly:", name="psofly")


# -------------
# Area Detector
#   Initialize the area detector here, but allow user to update the results
#   later
import os
import datetime
from pathlib import Path, PureWindowsPath

print("\nSetting up area detector")
# production control ENV vars
ADPV_prefix = "1idPG2"   # AreaDetector prefix

config_experiment = {
    "OUTPUT_ROOT" : "Y:\\",     # The control os is windows...
    "CYCLE" : "2019-1",
    "EXPID" : "startup_apr19",
    "USER"  : "tomo",
    'SAMPLE' : "test",
}

def get_file_path(config_dict=config_experiment):
    return str(PureWindowsPath(Path("/".join([v for _,v in config_dict.items()])+"/")))+'\\'

FILE_PATH = get_file_path(config_experiment)
FILE_PREFIX = config_experiment['SAMPLE']

print("***Make sure update FILE_PATH and FILE_PREFIX before experiment")
print("***--- FILE_PATH can also be generated by passing config_experiment to get_file_path()")
print("***--- read the config dictionary config_experiment for more details")

# make area detector
from ophyd import AreaDetector
from ophyd import SingleTrigger
from ophyd import ADComponent
from ophyd import PointGreyDetectorCam
from ophyd import ProcessPlugin
from ophyd import TIFFPlugin
from ophyd import HDF5Plugin
from ophyd import sim


class PointGreyDetector6BM(SingleTrigger, AreaDetector):
    """Point Gray area detector used at 6BM"""
    # cam component
    cam = ADComponent(PointGreyDetectorCam, "cam1:")
    
    # proc plugin
    proc1 = ADComponent(ProcessPlugin, suffix="Proc1:")
    
    # tiff plugin
    tiff1 = ADComponent(
        TIFFPlugin,
        suffix="TIFF1:",
        )

    hdf1 = ADComponent(
            HDF5Plugin, 
            suffix="HDF1:",
        )

# Area Detector (AD) config block
# NOTE:  user need to update the entry in these dictionary before
#        running the experiment
config_cam = {
    "num_images":     1,           # number of images (nFrame)
    "image_mode":     "Multiple",  #
    "trigger_mode":   "Internal",  #
    "acquire_time":   0.05,        # exposure time (fExposureTime)
    "acquire_period": 0.05+0.01,   #
    "gain":           5,           # detector gain [0~30]
}

config_proc1 = {
    "enable":           1,  # toggle on proc1
    "enable_filter":    1,  # enable filter
    "num_filter":       5,  # change number_filtered in proc1 (same as nFrame)
    "reset_filter":     1,  # reset number_filtered
}

config_tiff1 = {
    "enable":           0,            # disable by default
    "nd_array_port":    "PROC1",      # switch port for TIFF plugin
    "file_write_mode":  "Capture",     # change write mode
    "auto_increment":   "Yes",
    "auto_save":        "Yes",        # turn on file save
    "file_template":    r"%s%s_%06d.tiff",
    "file_path":        FILE_PATH,    # set file path
    "file_name":        FILE_PREFIX,  # img name prefix
}

config_hdf1 = {
    "enable":          0,           # disable by default
    "nd_array_port":  "PROC1",      # switch port for TIFF plugin
    "auto_save":      "Yes",
    "auto_increment": "Yes",
    "file_write_mode":  "Capture",     # change write mode
    "file_template":    r"%s%s_%06d.hd5",
    "file_path":      FILE_PATH,    # set file path
    "file_name":      FILE_PREFIX,  # img name prefix
}

if offline_testmode:
    det = sim.noisy_det  # use ophyd simulated detector
    print("***Ophyd virtual detector is used for offline dev")
else:
    det = PointGreyDetector6BM(f"{ADPV_prefix}:", name='det')

    # det.read_attrs.append('tiff1')  # this is very important
    # use det.read_attrs[-1] = 'hdf1' to switch to HDF5 output
    
    # catch timeout error in case detector not responding
    try:
        for k, v in config_cam.items():     det.cam.stage_sigs[k]   = v
        for k, v in config_proc1.items():   det.proc1.stage_sigs[k] = v
        for k, v in config_tiff1.items():   det.tiff1.stage_sigs[k] = v
        for k, v in config_hdf1.items():    det.hdf1.stage_sigs[k]  = v
        
    except TimeoutError as _exc:
        print(f"{_exc}\n !! Could not connect with area detector {det}")

    print(f"***Area Detector {det} is primed.")
    print("***Adjust settings (dict) in")
    print("***--- config_cam")
    print("***--- config_proc1")
    print("***--- config_tiff1")
    print("***--- config_hdf1")
    print("***before the acutal scan")

    print("***Switch to manual mode for:")
    print("***--FrameRate")
    det.cam.frame_rate_auto_mode.put(0)
    print("***--AcquirePeriod")
    det.cam.acquire_period_auto_mode.put(0)
    print("***--Gain")
    det.cam.gain_auto_mode.put(0)


# --
# ref: 
# we need to manually setup the PVs to store background and projections
# separately in a HDF5 archive
if offline_testmode:
    pass
else:
    import epics
    # this is the PV we use as the `SaveDest` attribute
    epics.caput("1idPG2:cam1:FrameType.ZRST", "/exchange/data_white_pre")
    epics.caput("1idPG2:cam1:FrameType.ONST", "/exchange/data")
    epics.caput("1idPG2:cam1:FrameType.TWST", "/exchange/data_white_post")
    epics.caput("1idPG2:cam1:FrameType.THST", "/exchange/data_dark")

    # ophyd needs this configuration
    epics.caput("1idPG2:cam1:FrameType_RBV.ZRST", "/exchange/data_white_pre")
    epics.caput("1idPG2:cam1:FrameType_RBV.ONST", "/exchange/data")
    epics.caput("1idPG2:cam1:FrameType_RBV.TWST", "/exchange/data_white_post")
    epics.caput("1idPG2:cam1:FrameType_RBV.TWST", "/exchange/data_dark")

print(f"Done with {__file__}\n{_sep}\n")