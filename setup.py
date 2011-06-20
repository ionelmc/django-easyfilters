#!/usr/bin/env python
from setuptools import setup, find_packages
import os


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


setup(
    name = "django-easyfilters",
    version = '0.0.1',
    packages = find_packages(),
    include_package_data = True,

    author = "Luke Plant",
    author_email = "L.Plant.98@cantab.net",
    url = "https://bitbucket.org/spookylukey/django-easyfilters/",
    description = "Intelligently add links that filter a list of Django model objects.",
    long_description = (
                        read('README.rst')
                        + "\n\n" +
                        read('CHANGES.rst')
    ),
    license = "MIT",
    keywords = "django filter autofilter drilldown easy simple",
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Framework :: Django",
        "Topic :: Software Development :: User Interfaces",
        ],
    install_requires = ['django >= 1.3'],
)
