# Exopy_qm

Exopy_qm is an exopy plugin to interface with Quantum Machine hardware.

## Installation

In order to install this plugin, you can simply run

```shell script
pip install .
```
inside the root folder.

If you want your changes in the code to work without reinstalling
exopy_qm after each change, you need to install exopy_qm in edit mode
by running

```shell script
pip install -e .
```

## Special note for Windows developers

Please set autocrlf to true in your git configuration if you want to work on the code with CRLF endlines. Please don't commit files with CRLF endings if you don't have that option enabled. See [this](https://stackoverflow.com/questions/1967370/git-replacing-lf-with-crlf) for more information.
