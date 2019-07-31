print(f'Enter {__file__}...')
# ----- Functions for hardware ----- #
from bluesky.suspenders import SuspendFloor

# ------- #
# shutter #
# ------- #
keywords_func['get_shutter'] = 'Return a connection to a sim/real shutter'
def get_shutter(mode='debug'):
    """
    return
        simulated shutter <-- dryrun, debug
        acutal shutter    <-- production
    """
    import apstools.devices as APS_devices
    aps = APS_devices.ApsMachineParametersDevice(name="APS")

    if mode.lower() in ['debug', 'dryrun']:
        A_shutter = APS_devices.SimulatedApsPssShutterWithStatus(name="A_shutter")
    elif mode.lower() == 'production':
        A_shutter = APS_devices.ApsPssShutterWithStatus(
            "6bmb1:rShtrA:",
            "PA:06BM:STA_A_FES_OPEN_PL",
            name="A_shutter",
        )
        suspend_APS_current = SuspendFloor(aps.current, 2, resume_thresh=10)
        RE.install_suspender(suspend_APS_current)
    else:
        raise ValueError(f"🙉: invalide mode, {mode}")

    return A_shutter

A_shutter = get_shutter(mode='debug')
keywords_vars['A_shutter'] = "shutter instance"
# no scans until A_shutter is open
suspend_A_shutter = None  # place holder
keywords_vars['suspend_A_shutter'] = "no scans until A_shutter is open"

# ----------------- #
# Motors definition #
# ----------------- #
from ophyd import MotorBundle
from ophyd import Component
from ophyd import EpicsMotor
from ophyd import sim

class TomoStage(MotorBundle):
    #rotation
    preci = Component(EpicsMotor, "6bmpreci:m1", name='preci')    
    samX  = Component(EpicsMotor, "6bma1:m19", name='samX')
    ksamX = Component(EpicsMotor, "6bma1:m11", name='ksamX')
    ksamZ = Component(EpicsMotor, "6bma1:m12", name='ksamZ')
    samY  = Component(EpicsMotor, "6bma1:m18", name="samY")

keywords_func['get_motors'] = 'Return a connection to sim/real tomostage motor'
def get_motors(mode="debug"):
    """
    sim motor <-- debug
    aerotech  <-- dryrun, production
    """
    if mode.lower() in ['dryrun', 'production']:
        tomostage = TomoStage(name='tomostage')
    elif mode.lower() == 'debug':
        tomostage = MotorBundle(name="tomostage")
        tomostage.preci = sim.motor
        tomostage.samX  = sim.motor
        tomostage.ksamX = sim.motor
        tomostage.ksamZ = sim.motor
        tomostage.samY  = sim.motor
    else:
        raise ValueError(f"🙉: invalide mode, {mode}")
    return tomostage

tomostage = get_motors(mode='debug')
keywords_vars['tomostage'] = 'sim/real tomo stage'
preci = tomostage.preci
keywords_vars['preci'] = 'rotation control'
samX = tomostage.samX
keywords_vars['samX'] = 'tomo stage x-translation'
ksamX = tomostage.ksamX
keywords_vars['ksamX'] = 'sample translation above rotation'
ksamZ = tomostage.ksamZ
keywords_vars['ksamZ'] = 'sample translation above rotation'
samY = tomostage.samY
keywords_vars['samY'] = 'tomo stage y-translation'


# ------------ #
# PSOFlyDevice #
# ------------ #
from ophyd import EpicsSignal
from ophyd import EpicsSignalRO
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

keywords_func['get_fly_motor'] = 'Return a connection to fly IOC control'
def get_fly_motor(mode='debug'):
    """
    sim motor <-- debug
    fly motor <-- dryrun, production
    """
    if mode.lower() == 'debug':
        psofly = sim.flyer1
    elif mode.lower() in ['dryrun', 'production']:
        psofly = EnsemblePSOFlyDevice("6bmpreci:eFly:", name="psofly")
        #psofly = EnsemblePSOFlyDevice("1ide:hexFly1:", name="psofly")   # for test in 1-ID
    else:
        raise ValueError(f"🙉: invalide mode, {mode}")
    return psofly

psofly = get_fly_motor(mode='debug')
keywords_vars['psofly'] = 'fly control instance'


# ------------- #
# area detector #
# ------------- #
from ophyd import AreaDetector
from ophyd import SingleTrigger, EpicsSignalWithRBV
from ophyd import ADComponent
from ophyd import PointGreyDetectorCam
from ophyd import ProcessPlugin
from ophyd import TIFFPlugin
from ophyd import HDF5Plugin
from ophyd import sim
from pathlib import Path
import epics

class PointGreyDetectorCam6BM(PointGreyDetectorCam):
    """PointGrey Grasshopper3 cam plugin customizations (properties)"""
    auto_exposure_on_off = ADComponent(EpicsSignalWithRBV, "AutoExposureOnOff")
    auto_exposure_auto_mode = ADComponent(EpicsSignalWithRBV, "AutoExposureAutoMode")
    sharpness_on_off = ADComponent(EpicsSignalWithRBV, "SharpnessOnOff")
    sharpness_auto_mode = ADComponent(EpicsSignalWithRBV, "SharpnessAutoMode")
    gamma_on_off = ADComponent(EpicsSignalWithRBV, "GammaOnOff")
    shutter_auto_mode = ADComponent(EpicsSignalWithRBV, "ShutterAutoMode")
    gain_auto_mode = ADComponent(EpicsSignalWithRBV, "GainAutoMode")
    trigger_mode_on_off = ADComponent(EpicsSignalWithRBV, "TriggerModeOnOff")
    trigger_mode_auto_mode = ADComponent(EpicsSignalWithRBV, "TriggerModeAutoMode")
    trigger_delay_on_off = ADComponent(EpicsSignalWithRBV, "TriggerDelayOnOff")
    frame_rate_on_off = ADComponent(EpicsSignalWithRBV, "FrameRateOnOff")
    frame_rate_auto_mode = ADComponent(EpicsSignalWithRBV, "FrameRateAutoMode")

class HDF5Plugin6BM(HDF5Plugin):
    """AD HDF5 plugin customizations (properties)"""
    xml_file_name = ADComponent(EpicsSignalWithRBV, "XMLFileName")

class PointGreyDetector6BM(SingleTrigger, AreaDetector):
    """Point Gray area detector used at 6BM"""
    # cam component
    cam = ADComponent(PointGreyDetectorCam6BM, "cam1:")
    # proc plugin
    proc1 = ADComponent(ProcessPlugin, suffix="Proc1:")
    # tiff plugin
    tiff1 = ADComponent(TIFFPlugin, suffix="TIFF1:")
    # HDF5 plugin
    hdf1 = ADComponent(HDF5Plugin6BM, suffix="HDF1:")

keywords_func['get_detector'] = 'Return a connection to the detector'
def get_detector(mode='debug', ADPV_prefix = "1idPG2"):
    """
    sim det  <-- debug
    PG2      <-- dryrun, production
    """
    if mode.lower() == 'debug':
        det = sim.noisy_det
    elif mode.lower() in ['dryrun', 'production']:
        det = PointGreyDetector6BM(f"{ADPV_prefix}:", name='det')

        # we need to manually setup the PVs to store background and projections
        # separately in a HDF5 archive
        # this is the PV we use as the `SaveDest` attribute
        # check the following page for important information
        # https://github.com/BCDA-APS/use_bluesky/blob/master/notebooks/sandbox/images_darks_flats.ipynb
        #
        epics.caput(f"{ADPV_prefix}:cam1:FrameType.ZRST", "/exchange/data_white_pre")
        epics.caput(f"{ADPV_prefix}:cam1:FrameType.ONST", "/exchange/data")
        epics.caput(f"{ADPV_prefix}:cam1:FrameType.TWST", "/exchange/data_white_post")
        epics.caput(f"{ADPV_prefix}:cam1:FrameType.THST", "/exchange/data_dark")
        # ophyd needs this configuration
        epics.caput(f"{ADPV_prefix}:cam1:FrameType_RBV.ZRST", "/exchange/data_white_pre")
        epics.caput(f"{ADPV_prefix}:cam1:FrameType_RBV.ONST", "/exchange/data")
        epics.caput(f"{ADPV_prefix}:cam1:FrameType_RBV.TWST", "/exchange/data_white_post")
        epics.caput(f"{ADPV_prefix}:cam1:FrameType_RBV.THST", "/exchange/data_dark")
        # set the layout file for cam
        # NOTE: use the __file__ as anchor should resolve the directory issue.
        _current_fp = str(Path(__file__).parent.absolute())
        _attrib_fp = os.path.join(_current_fp, '../../../configs/PG2_attributes.xml')
        det.cam.nd_attributes_file.put(_attrib_fp)
        # set attributes for HDF5 plugin
        _layout_fp = os.path.join(_current_fp, '../../../configs/tomo6bma_layout.xml')
        det.hdf1.xml_file_name.put(_layout_fp)
        # turn off the problematic auto setting in cam
        det.cam.auto_exposure_auto_mode.put(0)  
        det.cam.sharpness_auto_mode.put(0)
        det.cam.gain_auto_mode.put(0)
        det.cam.frame_rate_auto_mode.put(0)
    else:
        raise ValueError(f"🙉: invalide mode, {mode}")

    return det

det = get_detector(mode='debug')
keywords_vars['det'] = 'Area detector instance'

print(f'leaving {__file__}...\n')
