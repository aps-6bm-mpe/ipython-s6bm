print(f'Enter {__file__}...')
# ----- prefined plans for 6bma ----- #
# NOTE:
#  The signal staging does not work well with the CLI based experiment.
#  Therefore all plans are written without any signal staging.

import bluesky.plans         as bp
import bluesky.preprocessors as bpp
import bluesky.plan_stubs    as bps
import time
from bluesky.simulators import summarize_plan

keywords_vars['init_motors_pos'] = 'dict with cached motor position'
init_motors_pos = {
    'samX':  samX.position,
    'samY':  samY.position,
    'preci': preci.position,
}

keywords_func['resume_motors_position'] = 'Move motors back to init position'
def resume_motors_position():
    samX.mv( init_motors_pos['samX' ])
    samY.mv( init_motors_pos['samY' ])
    preci.mv(init_motors_pos['preci'])


# ----- step/fly scan plan ----- #
keywords_func['tomo_scan'] = 'Bluesky scan plans for tomography characterization'
def tomo_scan(config_exp):
    """
    Bluesky scan plans for tomography characterization.
    Read the sample experiment configuration file for more details

    NOTE: the input can be a dictionary or a YAML file
    """
    config = load_config(config_exp) if type(config_exp) != dict else config_exp

    # update the cached motor position in the dict in case exp goes wrong
    init_motors_pos['samX' ] = samX.position
    init_motors_pos['samY' ] = samY.position
    init_motors_pos['preci'] = preci.position

    # step 0: preparation
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
    fn = config['output']['fileprefix']
    
    # calculate slew speed for fly scan
    # https://github.com/decarlof/tomo2bm/blob/master/flir/libs/aps2bm_lib.py
    # TODO: considering blue pixels, use 2BM code as ref
    if config['tomo']['type'].lower() == 'fly':
        scan_time = (acquire_time+config['tomo']['readout_time'])*n_projections
        slew_speed = np.around((angs.max() - angs.min())/scan_time, decimals=4)
    
    # step 1: define the scan generator
    @bpp.stage_decorator([det])
    def scan_closure():
        # -------------------
        # collect white field
        # -------------------
        # 1-1 monitor shutter status, auto-puase scan if beam is lost
        yield from bps.open_run()
        yield from bps.mv(A_shutter, 'open')
        yield from bps.install_suspender(suspend_A_shutter)

        #1-1.5 configure output plugins     edited by Jason 07/19/2019
        for me in [det.tiff1, det.hdf1]:
            yield from bps.mv(me.file_path, fp)
            yield from bps.mv(me.file_name, fn)
            yield from bps.mv(me.file_write_mode, 2)
            yield from bps.mv(me.num_capture, total_images)
            yield from bps.mv(me.file_template, ".".join([r"%s%s_%06d",config['output']['type'].lower()]))    

        if config['output']['type'] in ['tif', 'tiff']:
            yield from bps.mv(det.tiff1.enable, 1)
            yield from bps.mv(det.tiff1.capture, 1)
            yield from bps.mv(det.hdf1.enable, 0)
        elif config['output']['type'] in ['hdf', 'hdf1', 'hdf5']:
            yield from bps.mv(det.tiff1.enable, 0)
            yield from bps.mv(det.hdf1.enable, 1)
            yield from bps.mv(det.hdf1.capture, 1)
        else:
            raise ValueError(f"Unsupported output type {output_dict['type']}")

        # 1-2 move sample out of the way
        initial_samx  = samX.position
        initial_samy  = samY.position
        initial_preci = preci.position
        dx = config['tomo']['sample_out_position']['samX']
        dy = config['tomo']['sample_out_position']['samY']
        r = config['tomo']['sample_out_position']['preci']
        yield from bps.mv(samX,  initial_samx  + dx)
        yield from bps.mv(samY,  initial_samy  + dy)
        yield from bps.mv(preci, r)

        # 1-2.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 0)

        # 1-3 collect front white field images
        yield from bps.mv(det.hdf1.nd_array_port, 'PROC1')
        yield from bps.mv(det.tiff1.nd_array_port, 'PROC1')
        yield from bps.mv(det.proc1.enable, 1)
        yield from bps.mv(det.proc1.reset_filter, 1)
        yield from bps.mv(det.proc1.num_filter, n_frames)
        yield from bps.mv(det.cam.trigger_mode, "Internal")
        yield from bps.mv(det.cam.image_mode, "Multiple")
        yield from bps.mv(det.cam.num_images, n_frames*n_white)
        yield from bps.mv(det.cam.acquire_time, acquire_time)
        yield from bps.mv(det.cam.acquire_period, acquire_period)
        yield from bps.trigger_and_read([det])
     

        # 1-4 move sample back
        yield from bps.mv(samX,  initial_samx )
        yield from bps.mv(samY,  initial_samy )
        #yield from bps.mv(preci, initial_preci)

        # -------------------
        # collect projections
        # -------------------
        # 1-5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 1)
        # 1-6 step and fly scan are differnt
        if config['tomo']['type'].lower() == 'step':
            yield from bps.mv(det.proc1.reset_filter, 1)
            yield from bps.mv(det.cam.num_images, n_frames)
            # 1-6 collect projections
            for ang in angs:
                yield from bps.checkpoint()
                yield from bps.mv(preci, ang)
                yield from bps.trigger_and_read([det])
        elif config['tomo']['type'].lower() == 'fly':
            yield from bps.mv(det.proc1.num_filter, 1)
            yield from bps.mv(det.hdf1.nd_array_port, 'PG1')
            yield from bps.mv(det.tiff1.nd_array_port, 'PG1')
            yield from bps.mv(
                psofly.start,           config['tomo']['omega_start'],
                psofly.end,             config['tomo']['omega_end'],
                psofly.scan_delta,      abs(config['tomo']['omega_step']),
                psofly.slew_speed,      slew_speed,
            )
            # taxi
            yield from bps.mv(psofly.taxi, "Taxi")
            # setup detector to overlap for fly scan
            yield from bps.mv(
                det.cam.num_images, n_projections,
                det.cam.trigger_mode, "Overlapped",
            )
            # start the fly scan
            print("before trigger")
            yield from bps.trigger(det, group='trigger')
            print("waiting for trigger")
            # yield from bps.wait(group='trigger')
            print("before plan()")
            try:
                yield from psofly.plan()
            except NotEnoughTriggers as err:
                reason=(f"{err.expected:.0f} were expected but {err.actual:.0f} were received.")
                yield from bps.close_run('fail', reason=reason)
                return  # short-circuit
              
            # fly scan finished. switch image port and trigger_mode back
            yield from bps.mv(det.cam.trigger_mode, "Internal")
            yield from bps.mv(det.hdf1.nd_array_port, 'PROC1')
            yield from bps.mv(det.tiff1.nd_array_port, 'PROC1')     
        else:
            raise ValueError(f"Unknown scan type: {config['tomo']['type']}")

        # ------------------
        # collect back white
        # ------------------
        # 1-7 move the sample out of the way
        # NOTE:
        # this will return ALL motors to starting positions, we need a
        # smart way to calculate a shorter trajectory to move sample
        # out of way
        yield from bps.mv(preci, r)
        yield from bps.mv(samX,  initial_samx  + dx)
        yield from bps.mv(samY,  initial_samy  + dy)
        
        # 1-7.5 set frame type for an organized HDF5 archive
        yield from bps.mv(det.cam.frame_type, 2)

        # 1-8 take the back white
        yield from bps.mv(det.proc1.num_filter, n_frames)
        yield from bps.mv(det.cam.num_images, n_frames*n_white)
        yield from bps.trigger_and_read([det])

        # 1-9 move sample back
        yield from bps.mv(samX,  initial_samx )
        yield from bps.mv(samY,  initial_samy )

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
        yield from bps.close_run('success')

    return (yield from scan_closure())


keywords_func['repeat_exp'] = 'repeat given experiment n times'
def repeat_exp(plan_func, n=1):
    """
    Quick wrapper to repeat certain experiment, e.g.
    >> RE(repeat_exp(tomo_scan('tomo_scan_config.yml')), 2)
    """
    for _ in range(n):
        yield from plan_func


print(f'leaving {__file__}...\n')


def repeat(n): 
    for i in range(n): 
        print(f'Run cycle {i+1} of {n} is about to start, you have 5 sec to abort the scan...')
        print(f'')
        time.sleep(5.0)        
        yield from tomo_scan('tomo_6bma.yml')
        time.sleep(0.1)        
 
