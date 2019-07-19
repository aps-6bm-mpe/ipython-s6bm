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

## Dev note

* Branch v0.01 was developed using standard signal staging and tested.
