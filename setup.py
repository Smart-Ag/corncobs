import os
from setuptools import setup, find_packages
import corncobs

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "corncobs",
    version = corncobs.__version__,
    author = "Thomas Antony",
    author_email = "tantony@smart-ag.com",
    description = ("Stream communication protocol for structured data"),
    license = "MIT",
    keywords = "struct, communication, protocol, serial, arduino",
    url = "https://github.com/Smart-Ag/corncobs",
    py_modules=['corncobs'],
    install_requires=['pyserial', 'cobs'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    packages=find_packages(exclude=['docs', 'tests']),
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Software Development :: Libraries",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
    ],
)
