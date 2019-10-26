# Exopy_qm

Exopy_qm is an exopy plugin to interface with Quantum Machine hardware.

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

## Modifying exopy_qm

If you want your changes in the code to work without reinstalling
exopy_qm after each change, you need to install exopy_qm in edit mode
by running

```shell script
pip install -e .
```

## Special note for Windows developers

Please set autocrlf to true in your git configuration if you want to work on the code with CRLF endlines. Please don't commit files with CRLF endings if you don't have that option enabled. See [this](https://stackoverflow.com/questions/1967370/git-replacing-lf-with-crlf) for more information.
