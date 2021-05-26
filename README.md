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

## Known problems
The OPX can generate very large amount of data and displaying such large amounts of data in the text monitor of exopy can cause slowdowns or even memory leaks. To fix that issue, you should use a very recent version of exopy (because of a bug that was fixed in a [recent commit](https://github.com/Exopy/exopy/commit/b5bd74fd720b6d2888d971a21a8474a99d513432)) and remove the entries containing large amount of data from the list of displayed entries in the "edit tools" menu.  

## Special note for Windows developers

Please set autocrlf to true in your git configuration if you want to work on the code with CRLF endlines. Please don't commit files with CRLF endings if you don't have that option enabled. See [this](https://stackoverflow.com/questions/1967370/git-replacing-lf-with-crlf) for more information.
