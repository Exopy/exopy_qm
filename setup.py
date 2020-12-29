#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import os.path
import sys

sys.path.insert(0, os.path.abspath('.'))

PROJECT_NAME = 'exopy_qm'
with open("VERSION", "r") as f:
    version = f.readline()

if len(version) < 1:
    raise Exception("No version specified")

print("Building version {}".format(version))


setup(
    name=PROJECT_NAME,
    description='QM Exopy package',
    version=version,
    long_description="",
    author='Michael Greenbaum',
    author_email='mgtk77@gmail.com',
    url="https://quantum-machines.co",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: Physics',
        'Programming Language :: Python :: 3.6'
        ],
    zip_safe=False,
    packages=find_packages(exclude=['tests', 'tests.*']),
    data_files=["VERSION", "LICENSE"],
    package_data={'': ['*.enaml']},
    install_requires=['exopy', 'matplotlib'],
    entry_points={
        'exopy_package_extension':
        'exopy_qm = %s:list_manifests' % PROJECT_NAME}
)
