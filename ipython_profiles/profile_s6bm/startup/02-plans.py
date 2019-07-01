# prefined plans for tomo scan at 6bma
_sep = u"🙊"*30
print(f'{_sep}\nCaching pre-defined scan plans with {__file__}')


import numpy                 as np
import bluesky.plans         as bp
import bluesky.preprocessors as bpp
import bluesky.plan_stubs    as bps
from bluesky.simulators import summarize_plan


def config_output(output_dict, nimages):
    """config output based on given configuration dict"""
    fp = FILE_PATH if output_dict['filepath'] is None else output_dict['filepath']
    fn = FILE_PREFIX if output_dict['fileprefix'] is None else output_dict['fileprefix']
    
    if output_dict['type'].lower() in ['tif', 'tiff']:
        _plg_on = det.tiff1
        _plg_off = det.hdf1
    elif output_dict['type'].lower() in ['hdf', 'hdf1', 'hdf5']:
        _plg_on = det.hdf1
        _plg_off = det.tiff1
    else:
        raise ValueError(f"Unsupported output type {output_dict['type']}")
    
    for k, v in {
        "enable":         1,
        "num_capture":    nimages,
        "file_template":  ".".join([r"%s%s_%06d",output_dict['type'].lower()]),
        #"file_path":      fp,    
        "file_name":      fn,
        "capture":        1,
    }.items(): _plg_on.stage_sigs[k] = v
    _plg_off.stage_sigs = {}

    # disable HDF5 auto_increment so that we have a single archive
    # NOTE:
    # Might not be necessary with current setup where the HDF5 remain open
    # the whole scan...
    # det.hdf1.stage_sigs['auto_increment'] = "No"


def tomo_step(config):
    """read the config file or dict to formulate a step scan plan"""
    config = load_config(config) if type(config) != dict else config

    # step_0: extrat scan related vars
    acquire_time = config['tomo']['acquire_time']
    acquire_period = config['tomo']['acquire_period']
    n_frames = config['tomo']['n_frames']
    n_white = config['tomo']['n_white']
    n_dark = config['tomo']['n_dark']
    angs = np.arange(
        config['tomo']['omega_start'], 
        config['tomo']['omega_end']+config['tomo']['omega_step']/2,
        config['tomo']['omega_step'],
    )
    n_projections = len(angs)
    total_images  = n_white + n_projections + n_white + n_dark
    
    fp = config['output']['filepath']
    
    # set file_path (workaround before we solve "file_path_RBV" timeout issue 
    det.tiff1.file_path.put(fp)
    det.hdf1.file_path.put(fp)
    det.tiff1.file_write_mode.put('Stream')
    det.hdf1.file_write_mode.put('Stream')
    
    
    # step_1: setup output configuration
    config_output(config['output'], total_images)
    
    # step_2: the whole scan
    # NOTE:
    # 1. As of 04/24/2019, the area detector HDF5 plugin does not support
    # appending dataset to existing HDF5 archives.  Therefore, we need
    # to write everything at once to get single archive file...
    # 2. BlueSky use the generator feature to realize delayed execution,
    # so we need to define all the scan related actions in an closure, also
    # known as the inline/nested function.
    @bpp.stage_decorator([det])
    @bpp.run_decorator()
    def scan_closure():
        yield from bps.mv(det.cam.acquire_time, acquire_time)
        yield from bps.mv(det.cam.acquire_period, acquire_period)
        
        # -------------------
        # collect white field
        # -------------------
        # 1-1 monitor shutter status, auto-puase scan if beam is lost
        yield from bps.mv(A_shutter, 'open')
        yield from bps.install_suspender(suspend_A_shutter)

        # 1-2 move sample out of the way
        initial_samx = samx.position
        initial_samy = samy.position
        initial_preci = preci.position
        dx = config['tomo']['sample_out_position']['samx']
        dy = config['tomo']['sample_out_position']['samy']
        r = config['tomo']['sample_out_position']['preci']
        yield from bps.mv(samx,  initial_samx  + dx)
        yield from bps.mv(samy,  initial_samy  + dy)
        yield from bps.mv(preci, r)

        # 1-2.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 0)

        # 1-3 collect front white field images
        yield from bps.mv(det.proc1.enable, 1)
        yield from bps.mv(det.proc1.reset_filter, 1)
        yield from bps.mv(det.proc1.num_filter, n_frames)
        yield from bps.mv(det.cam.trigger_mode, "Internal")
        yield from bps.mv(det.cam.image_mode, "Multiple")
        yield from bps.mv(det.cam.num_images, n_frames*n_white)
        yield from bps.trigger_and_read([det])
        yield from bps.mv(det.hdf1.nd_array_port, 'PROC1')
        yield from bps.mv(det.tiff1.nd_array_port, 'PROC1')   

        # 1-4 move sample back
        yield from bps.mv(samx,  initial_samx )
        yield from bps.mv(samy,  initial_samy )
        #yield from bps.mv(preci, initial_preci)

        # -------------------
        # collect projections
        # -------------------
        # 1-4.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 1)

        # 1-5 quicly reset proc1
        yield from bps.mv(det.proc1.reset_filter, 1)
        yield from bps.mv(det.cam.num_images, n_frames)

        # 1-6 collect projections
        for ang in angs:
            yield from bps.checkpoint()
            yield from bps.mv(preci, ang)
            yield from bps.trigger_and_read([det])

        # ------------------
        # collect back white
        # ------------------
        # 1-7 move the sample out of the way
        # NOTE:
        # this will return ALL motors to starting positions, we need a
        # smart way to calculate a shorter trajectory to move sample
        # out of way
        yield from bps.mv(preci, r)
        yield from bps.mv(samx,  initial_samx  + dx)
        yield from bps.mv(samy,  initial_samy  + dy)
        
        # 1-7.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 2)

        # 1-8 take the back white
        yield from bps.mv(det.cam.num_images, n_frames*n_white)
        yield from bps.trigger_and_read([det])

        # 1-9 move sample back
        yield from bps.mv(samx,  initial_samx )
        yield from bps.mv(samy,  initial_samy )
        #yield from bps.mv(preci, initial_preci)

        # -----------------
        # collect back dark
        # -----------------
        # 1-10 close the shutter
        yield from bps.remove_suspender(suspend_A_shutter)
        yield from bps.mv(A_shutter, "close")

        # 1-10.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 3)

        # 1-11 collect the back dark
        yield from bps.mv(det.cam.num_images, n_frames*n_dark)
        yield from bps.trigger_and_read([det])
        
    return (yield from scan_closure())


# This section is to reset motor position, in case the motor can keep rotating continuously.
#def motor_set_modulo(motor, modulo):
#    if not 0 <= motor.position < modulo:
#        yield from bps.mv(motor.set_use_switch, 1)
#        yield from bps.mv(motor.user_setpoint, motor.position % modulo)
#        yield from bps.mv(motor.set_use_switch, 0)

def tomo_fly(config):
    """
    The master plan pass to RE for
    
    1. pre-white-field background collection
    2. projection collection
    3. post-white-field background collection
    4. post-dark-field background collection

    NOTE:
    see config_tomo_fly for key inputs
    """
    config_tiff1['nd_array_port'] = 'PG1'
    config_hdf1['nd_array_port']  = 'PG1'
    
    
    config = load_config(config) if type(config) != dict else config

    # step0: unpack the configuration dict
    # NOTE: very similar to the step scan...
    acquire_time = config['tomo']['acquire_time']
    acquire_period = config['tomo']['acquire_period']
    config_cam['acquire_time'] = acquire_time
    config_cam['acquire_period'] = acquire_period
    #n_frames = config['tomo']['n_frames']
    n_white = config['tomo']['n_white']
    n_dark = config['tomo']['n_dark']
    angs = np.arange(
        config['tomo']['omega_start'], 
        config['tomo']['omega_end']+config['tomo']['omega_step']/2,
        config['tomo']['omega_step'],
    )
    n_projections = len(angs)
    total_images  = n_white + n_projections + n_white + n_dark
    # get the fly scan related entry
    slew_speed = config['tomo']['slew_speed']
    accl = config['tomo']['accl']
    ROT_STAGE_FAST_SPEED = config['tomo']['ROT_STAGE_FAST_SPEED']
    
    # set file_path (workaround before we solve "file_path_RBV" timeout issue (4/23/2019)
    fp = config['output']['filepath']
    det.tiff1.file_path.put(fp)
    det.hdf1.file_path.put(fp)

    # step_1: setup output configuration
    config_output(config['output'], total_images)

    # step_2: the whole scan
    @bpp.stage_decorator([det])
    @bpp.run_decorator()
    def scan_closure():
        #yield from bps.mv(det.cam.acquire_time, acquire_time)
        #yield from bps.mv(det.cam.acquire_period, acquire_period)
        
        # -------------------
        # collect white field
        # -------------------
        # 1-1 monitor shutter status, auto-puase scan if beam is lost
        yield from bps.mv(A_shutter, 'open')
        yield from bps.install_suspender(suspend_A_shutter)

        # 1-2 move sample out of the way
        initial_samx = samx.position
        initial_samy = samy.position
        initial_preci = preci.position
        dx = config['tomo']['sample_out_position']['samx']
        dy = config['tomo']['sample_out_position']['samy']
        r = config['tomo']['sample_out_position']['preci']
        yield from bps.mv(samx,  initial_samx  + dx)
        yield from bps.mv(samy,  initial_samy  + dy)
        yield from bps.mv(preci, r)

        # 1-2.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 0)

        # 1-3 collect front white field images
        #yield from bps.mv(det.proc1.enable, 1)
        #yield from bps.mv(det.proc1.reset_filter, 1)
        #yield from bps.mv(det.proc1.num_filter, n_frames)
        yield from bps.mv(det.cam.trigger_mode, "Internal")
        yield from bps.mv(det.cam.image_mode, "Multiple")
        yield from bps.mv(det.cam.num_images, n_white)
        yield from bps.trigger_and_read([det])

        # 1-4 move sample back
        yield from bps.mv(samx,  initial_samx )
        yield from bps.mv(samy,  initial_samy )
        #yield from bps.mv(preci, initial_preci)

        # -------------------
        # collect projections
        # -------------------
        # 1-4.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 1)

        # 1-5 get array directly from PG1 port
        yield from bps.mv(det.hdf1.nd_array_port, 'PG1')
        yield from bps.mv(det.tiff1.nd_array_port, 'PG1')

        # 1-6 collect projections

        # configure the psofly interface
        yield from bps.mv(
            psofly.start,           config['tomo']['omega_start'],
            psofly.end,             config['tomo']['omega_end'],
#             psofly.scan_control,    "Standard",
            psofly.scan_delta,      config['tomo']['omega_step'],
#            psofly.slew_speed,      slew_speed,
#            preci.velocity,         ROT_STAGE_FAST_SPEED,
#            preci.acceleration,     accl,
            )
        # taxi
        yield from bps.mv(psofly.taxi, "Taxi")

        # ???
        yield from bps.mv(
            det.cam.num_images, n_projections,
            #det.cam.trigger_mode, "Overlapped",
            det.cam.trigger_mode, "Bulb",
            )
        # start the fly scan
        yield from bps.trigger(det, group='fly')
        yield from bps.abs_set(psofly.fly, "Fly", group='fly')
        yield from bps.wait(group='fly')
                         
        # fly scan finished. switch image port and trigger_mode back
        yield from bps.mv(det.cam.trigger_mode, "Internal")
        #yield from bps.mv(det.hdf1.nd_array_port, 'PROC1')
        #yield from bps.mv(det.tiff1.nd_array_port, 'PROC1')                         

        # ------------------
        # collect back white
        # ------------------
        # 1-7 move the sample out of the way
        # NOTE:
        # this will return ALL motors to starting positions, we need a
        # smart way to calculate a shorter trajectory to move sample
        # out of way
        yield from bps.mv(preci, r)
        yield from bps.mv(samx,  initial_samx  + dx)
        yield from bps.mv(samy,  initial_samy  + dy)
        
        # 1-7.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 2)

        # 1-8 take the back white
        yield from bps.mv(det.cam.num_images, n_white)
        yield from bps.trigger_and_read([det])

        # 1-9 move sample back
        yield from bps.mv(samx,  initial_samx )
        yield from bps.mv(samy,  initial_samy )
        #yield from bps.mv(preci, initial_preci)

        # -----------------
        # collect back dark
        # -----------------
        # 1-10 close the shutter
        yield from bps.remove_suspender(suspend_A_shutter)
        yield from bps.mv(A_shutter, "close")

        # 1-10.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 3)

        # 1-11 collect the back dark
        yield from bps.mv(det.cam.num_images, n_dark)
        yield from bps.trigger_and_read([det])

    return (yield from scan_closure())


print(f"Done with {__file__}\n{_sep}\n")
