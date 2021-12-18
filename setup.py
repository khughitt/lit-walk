# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Topic :: Scientific/Engineering",
    "Operating System :: Microsoft :: Windows",
    "Operating System :: POSIX",
    "Operating System :: Unix",
    "Operating System :: MacOS",
]

#  with open("README.rst") as f:
#      readme = f.read()
readme = ""

with open("LICENSE") as f:
    license = f.read()

setup(
    name="lit-tool",
    version="0.1.0",
    classifiers=CLASSIFIERS,
    description="science literature exploration tool",
    install_requires=[
        "bibtexparser",
        "pyyaml"
    ],
    long_description=readme,
    author="Keith Hughitt",
    author_email="keith.hughitt@nih.gov",
    url="https://github.com/khughitt/lit-tool",
    license=license,
    scripts=["bin/lit-tool"],
    packages=find_packages(exclude=("tests", "docs")),
)
