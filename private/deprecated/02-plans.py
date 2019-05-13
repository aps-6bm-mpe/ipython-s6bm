# ------ deprecated below this line -----

def set_output_type(n_images, output='tiff'):
    """config output"""
    # clear the watch list first
    # NOTE:
    #    det.read_attrs is treated as a gloal var, therefore the chnages
    #    made here affect the global workspace
    det.read_attrs = [me for me in det.read_attrs 
                        if me not in ('tiff1', 'hdf1')
                    ]
    if output.lower() in ['tif', 'tiff']:
        for k,v in {
            "enable":      1,
            "num_capture": n_images,
            "capture":     1,
        }.items(): det.tiff1.stage_sigs[k] = v
        det.hdf1.stage_sigs["enable"] = 0
        det.read_attrs.append('tiff1')
    elif output.lower() in ['hdf', 'hdf1', 'hdf5']:
        for k,v in {
            "enable":      1,
            "num_capture": n_images,
            "auto_increment": "No",
            "capture":     1,
        }.items(): det.hdf1.stage_sigs[k] = v
        det.tiff1.stage_sigs["enable"] = 0
        det.read_attrs.append('hdf1')
    else:
        raise ValueError(f"Unknown output format {output}")


# ----
# Dark/White flat field
# NOTE:
#    det is a global var that refers to the detector
def collect_background(n_images, 
                       n_frames,
                       output='tiff',
    ):
    """collect n_images backgrounds with n_frames per take"""

    set_output_type(n_images, output)
    
    for k,v in {
        "reset_filter":     1,
        "num_filter":       n_frames,
    }.items(): det.proc1.stage_sigs[k] = v
        
    for k,v in {
        "trigger_mode": "Internal",
        "image_mode":   "Multiple",
        "num_images":   n_frames*n_images,
    }.items(): det.cam.stage_sigs[k] = v

    @bpp.stage_decorator([det])
    @bpp.run_decorator()
    def scan():
        yield from bps.trigger_and_read([det]) 
    
    return (yield from scan())


# ----
# Projections (step)
def step_scan(n_images, 
              n_frames,
              angs,           # list of angles where images are taken
              output='tiff',
    ):
    """collect proejctions by stepping motors"""
    set_output_type(n_images, output)

    for k, v in {
        "enable":           1,         # toggle on proc1
        "reset_filter":     1,         # reset number_filtered
        "num_filter":       n_frames,
    }.items(): det.proc1.stage_sigs[k] = v
    
    for k, v in {
        "num_images":   n_frames,      
    }.items(): det.cam.stage_sigs[k] = v

    @bpp.stage_decorator([det])
    @bpp.run_decorator()
    def scan_closure():
        for ang in angs:
            yield from bps.checkpoint()
            yield from bps.mv(preci, ang)
            yield from bps.trigger_and_read([det])
    
    return (yield from scan_closure())


# ----
# Projections (fly)
def fly_scan():
    """collect projections using fly scan feature"""
    pass


# ----
# Example bundled tomo characterization scan
config_tomo_step = {
    "n_white"        :  10,
    "n_dark"         :  10,
    "samOutDist"     : -5.00,           # mm
    "omega_step"     :  0.5,           # degrees
    "acquire_time"   :  0.05,           # sec
    # "acquire_period" :  0.05+0.01,      # sec
    # "time_wait"      : (0.05+0.01)*2,   # sec
    "omega_start"    :  0,              # degrees
    "omega_end"      :  5,              # degrees
    "n_frames"       :  5,              # proc.n_filters, cam.n_images
    "output"         : "hdf5",          # output format ['tiff', 'hdf5']
}
def tomo_step(config_dict):
    """
    The master plan pass to RE for
    
    1. pre-white-field background collection
    2. projection collection
    3. post-white-field background collection
    4. post-dark-field background collection

    NOTE:
    see config_tomo_step for key inputs
    """
    _output = config_dict['output']
    _samOutDist = config_dict['samOutDist']

    # monitor shutter status, auto-puase scan if beam is lost
    yield from bps.mv(A_shutter, 'open')
    yield from bps.install_suspender(suspend_A_shutter)

    # first front white field
    current_samx = samx.position
    yield from bps.mv(samx, current_samx + _samOutDist)
    # ??
    yield from bps.mv(det.cam.frame_type, 0)
    yield from collect_background(config_dict['n_white'], 
                                  config_dict['n_frames'],
                                  _output,
                                )
    yield from bps.mv(samx, current_samx)

    # collect projections
    yield from bps.mv(det.cam.frame_type, 1)
    angs =  np.arange(config_dict['omega_start'], 
                      config_dict['omega_end']+config_dict['omega_step']/2,
                      config_dict['omega_step'],
                    )
    yield from step_scan(n_images=len(angs), 
                         n_frames=config_dict['n_frames'],
                         angs=angs,           # list of angles where images are taken
                         output=_output,
                    )

    # collect back white field
    current_samx = samx.position
    yield from bps.mv(samx, current_samx + _samOutDist)
    yield from bps.mv(det.cam.frame_type, 2)
    yield from collect_background(config_dict['n_white'], 
                                  config_dict['n_frames'],
                                  _output,
                                )
    yield from bps.mv(samx, current_samx)

    # collect back dark field
    yield from bps.remove_suspender(suspend_A_shutter)
    yield from bps.mv(A_shutter, "close")
    yield from bps.mv(det.cam.frame_type, 3)
    yield from collect_background(config_dict['n_dark'],
                                  config_dict['n_frames'],
                                  _output,
                                )


# ----
# Fly scan bundle example
config_tomo_fly = {
    "n_white"        :  10,
    "n_dark"         :  10,
}
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

