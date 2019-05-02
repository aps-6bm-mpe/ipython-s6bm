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
        "file_path":      fp,    
        "file_name":      fn,
        "capture":        1,
    }.items(): _plg_on.stage_sigs[k] = v
    _plg_off.stage_sigs['enable'] = 0

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
        current_samx = samx.position
        current_samy = samy.position
        current_preci = preci.position
        dx = config['tomo']['sample_out_position']['samx']
        dy = config['tomo']['sample_out_position']['samy']
        dr = config['tomo']['sample_out_position']['preci']
        yield from bps.mv(samx,  current_samx  + dx)
        yield from bps.mv(samy,  current_samy  + dy)
        yield from bps.mv(preci, current_preci + dr)

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

        # 1-4 move sample back
        yield from bps.mv(samx,  current_samx )
        yield from bps.mv(samy,  current_samy )
        yield from bps.mv(preci, current_preci)

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
        yield from bps.mv(preci, current_preci + dr)
        yield from bps.mv(samx,  current_samx  + dx)
        yield from bps.mv(samy,  current_samy  + dy)
        
        # 1-7.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 2)

        # 1-8 take the back white
        yield from bps.mv(det.cam.num_images, n_frames*n_white)
        yield from bps.trigger_and_read([det])

        # 1-9 move sample back
        yield from bps.mv(samx,  current_samx )
        yield from bps.mv(samy,  current_samy )
        yield from bps.mv(preci, current_preci)

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


def tomo_fly(config_dict):
    """
    The master plan pass to RE for
    
    1. pre-white-field background collection
    2. projection collection
    3. post-white-field background collection
    4. post-dark-field background collection

    NOTE:
    see config_tomo_fly for key inputs
    """
    pass


print(f"Done with {__file__}\n{_sep}\n")
