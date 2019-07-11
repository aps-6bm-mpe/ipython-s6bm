# ----- Ipython control config and standard library import ----- #
import os
import socket
import getpass
import yaml
import bluesky
import ophyd
import apstools
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from IPython import get_ipython
# use matplotlib jupyter widget library for interactive
# plots, i.e. %matplotlib widget
# NOTE: more details in the installation guide
# >> conda install -c conda-forge ipympl
# >> conda install -c conda-forge widgetsnbextension
get_ipython().run_line_magic('matplotlib', 'widget')  
plt.ion()
from datetime import datetime
# get system info
HOSTNAME = socket.gethostname() or 'localhost'
USERNAME = getpass.getuser() or '6-BM-A user'
keywords_reserved = []  # list of keywords reseved for beamline setup

print(f'''
🐉: Greetings, {USERNAME}@{HOSTNAME}!
    I, the mighty 🐉, 
    have imported 
        os
        socket
        getpass
        yaml
        matplotlib.pyplot as plt <-- interactive, using widget as backend
        numpy 
        datetime
        bluesky
        ophyd
        apstools
    for you, rejoice.
''')


# ----- Setup base bluesky RunEngine and MongoDB ----- #
# metadata streamed to MongoDB server over the network
from databroker import Broker
metadata_db = Broker.named("mongodb_config")
keywords_reserved.append('metadata_db')

# setup RunEngine
from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback
def getRunEngine(db=None):
    """
    Return an instance of RunEngine.  It is recommended to have only
    one RunEngine per session.
    """
    RE = RunEngine({})
    db = metadata_db if db is None else db
    RE.subscribe(db.insert)
    RE.subscribe(BestEffortCallback())
    RE.md['beamline_id'] = 'APS 6-BM-A'
    RE.md['proposal_id'] = 'internal test'
    RE.md['pid'] = os.getpid()
    RE.md['login_id'] = USERNAME + '@' + HOSTNAME
    RE.md['BLUESKY_VERSION'] = bluesky.__version__
    RE.md['OPHYD_VERSION'] = ophyd.__version__
    RE.md['apstools_VERSION'] = apstools.__version__
    RE.md['SESSION_STARTED'] = datetime.isoformat(datetime.now(), " ")
    return RE
keywords_reserved.append('getRunEngine()')
RE = getRunEngine()
keywords_reserved.append('RE')

print(f"""
🙈: A detault RunEngine, RE:
    >> {RE}
    is created with the default metadata handler, metadata_db.
    >> {metadata_db}
    using function getRunEngine()
""")


# ----- Define utility functions ----- #
def load_config(yamlfile):
    """load yaml to a dict"""
    with open(yamlfile, 'r') as stream:
        _dict = yaml.safe_load(stream)
    return _dict
keywords_reserved.append('load_config()')

def instrument_in_use():
    """check if the soft IOC for 6BM-A"""
    from ophyd import EpicsSignalRO
    tmp = EpicsSignalRO("6bm:instrument_in_use", name="tmp")
    try:
        state = tmp.get()
    except TimeoutError:
        state = False
        print("🙈: cannot find this soft IOC PV, please check the settings.")
    finally:
        print(f"🙈: the instrument is {'' if state else 'not'} in use.")
        return state
keywords_reserved.append('instrument_is_in_use()')

def hutch_light_on():
    """check PV for hutch lighting"""
    calcs = apstools.synApps_ophyd.userCalcsDevice("6bma1:", name="calcs")
    try:
        state = bool(calcs.calc1.val.get())
    except TimeoutError:
        state = None
        print("🙈: cannot find this soft IOC PV, please check the settings.")
    finally:
        print(f"🙈: the hutch is {'' if state else 'not'} on.")
    return state
keywords_reserved.append('hutch_light_on()')
