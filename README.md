Documentation is currently being updated. 

Older developer-written docs are available at: http://institutefordiseasemodeling.github.io/dtk-tools
Docs currently under construction are available at: https://institutefordiseasemodeling.github.io/Documentation/dtk-tools/index.html

The `dtk` package is intended to strengthen and simplify the interaction between researchers and the [EMOD model](http://idmod.org/docs/general/index.html).

Modules contained in this package are intended to:
- Empower the user to configure diverse simulations and arbitrarily complex campaigns built up from a standardized library of configuration fragments and utility functions;
- Facilitate transparent switching between local and remote HPC commissioning, job-status queries, and output analysis;
- Enable the configuration of arbitrary collections of simulations (e.g. parameteric sweeps) through an extensible library of builder classes;
- Collect a library of post-processing analysis functionality, e.g. filtering, mapping, averaging, plotting.

#### Recommended Installation steps

Make sure you have **Python 3.6 x64** installed (available [here](https://www.python.org/downloads/)).

Install python virtualenv:
```bash
> pip install virtualenv
```

Create a python virtual environment:
```bash
> virtualenv idmtools
```

Activate the virtual environment, on Windows:
```bash
> cd idmtools\Scripts
> activate
```
On unix platform:
```bash
> cd idmtools/bin
> ./activate
```

Create a `pip.ini` file (`pip.conf` if on Unix) in your virtual environment folder (here `idmtools`) with the following content:
```ini
[global]
index-url = https://packages.idmod.org/api/pypi/pypi-production/simple
```

Install dtk-tools:
```bash
> pip install dtk-tools
```

Run the initialization:
```bash
> dtksetup init
```

If you want to access the examples, navigate to the desired folder and run:
```bash
> dtkseup examples
```
It will create an `examples` directory containing all the built-in dtk-tools examples.


#### Installation for development

To install the dtk-tools, first clone the repository:
```
git clone https://github.com/InstituteforDiseaseModeling/dtk-tools.git
```

From a command-prompt, run the following from the **dtk-tools** directory:
```
python setup_manual.py
```

**Note:** If `pip` command is not found on your system, make sure to add the Python scripts directory (by default in Windows: `C:\Python27\Scripts`)
to your `PATH` environment variable.

#### Setup

To configure your user-specific paths and settings for local and HPC job submission, please create a `simtools.ini` file in
the same folder that contains your scripts.

Simulation job management is handled through the various `dtk` command-line options, e.g. `dtk run example_sweep` or `dtk analyze example_plots`.  For a full list of options, execute `dtk --help`. 
