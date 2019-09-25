## Building Source Dist
```shell script
pip setup.py sdist 
```

## Installation

This package has a requirement that cannot be fulfilled by PyPi

In order for this extension to work, you must have the QM package installed in the same
python environment this plugin is installed at.

After building the source dist as specified above, install using
```shell script
pip install dist/exopy_qm-<version>.tar.gz
```