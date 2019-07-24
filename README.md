# ipython-s6bm

User account for 6-BM-A using ipython

## Installation of BlueSky control system

It is __highly recommended__ to deploy this control system in a virtual environemnt. For example:

```bash
conda create -n bluesky
```

Switch to the new env 

```bash
conda activate bluesky
```

to install `BlueSky` core packages with

```bash
conda install -c conda-forge bluesky
```

then the `apstools` packages for APS devices.

```
pip install apstools
```

> Due to the hybrid installation source, some packages might be installed via both `conda` and `pip`.
This is typically not an issue as the latest version should be the same regardless the source.
However, it is recommended to check the acutal packages being used via `IPython` session should any issue occur.

Some supplementary packages recommended:

```bash
conda install jupyter jupyterlab
```

## Config Meta-data handler (MongoDB)

Copy the configuration file `configs/mongodb_config.yml` to `HOME/.config/databroker/mongodb_config.yml` to enable meta-data handler backed by a MongoDB server.

> The entry __host__ need to be changed to the IP of the machine that hosts the MongoDB service.

## Ipython based control

### Profile

The environment var `IPYTHONDIR` needs to be set where the profile folder is, or simply create symbolic link of the deisred profile to `~/.ipython/`, which is the default location to store all IPython profiles.

```bash
>> export IPYTHONDIR=ipython_profiles/
```

### Startup

Issue the following command in the terminal to run IPython with pre-configured environment for Tomo-characterization at 6-BM-A:

```bash
>> ipython --profile=s6bm
```

By default, all devices are initialized to 'debug' mode where only simulated devices are connected.
To check the current mode, simply do

```bash
>> mode
```

or switch to different model with

```bash
>> mode.set('production')
```

Currently there are three modes available:

|     |     |
| --- | --- |
|__debug__| only connect to simulated ophyd devices |
|__dryrun__| connect to real devices (PVs) and a simulated shutter |
|__production__| production mode, ready for data collection|

### Run tomo experiment

The details of a tomography experiment should be specified in a YAML file (see configs/tomo_6bma.yml) for example.
To run the experiment once, one can simply type

```bash
>> RE(tomo_scan('my_tomo_exp.yml'))
```

If you would like to modify certain field on the fly, you can also load the YAML as dictionary using 

```bash
>> tomo_exp = load_config('my_tomo_exp.yml')
```

and directly modify different entries in the dict.
Then you can pass the dict to _RE_ to run.

For example, let's say that we want the first experiment to be a step scan using _tiff_ as output and the second one using fly scan with _HDF5_ as output.
The following code should work

```bash
>> mode.set('production')
>> tomo_exp = load_config('my_tomo_exp.yml')
>> tomo_exp['tomo']['type'] = 'step'
>> tomo_exp['output']['type'] = 'tiff'
>> RE(tomo_scan(tomo_exp))
...
>> tomo_exp['tomo']['type'] = 'fly'
>> tomo_exp['output']['type'] = 'hdf'
>> RE(tomo_scan(tomo_exp))
```

## Dev note

* Branch v0.01 was developed using standard signal staging and tested.
