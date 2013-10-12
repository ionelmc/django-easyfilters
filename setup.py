#!/usr/bin/env python
from setuptools import setup, find_packages
import os

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name = "django-easyfilters",
    version = '0.6pre',
    packages = find_packages('src'),
    package_dir = {'':'src'},
    include_package_data = True,
    zip_safe = False,
    author = "Luke Plant",
    author_email = "L.Plant.98@cantab.net",
    url = "https://bitbucket.org/spookylukey/django-easyfilters/",
    description = "Easy creation of link-based filtering for a list of Django model objects.",
    long_description = (
        read('README.rst')
        + "\n\n" +
        read('CHANGES.rst')
    ),
    license = "MIT",
    keywords = "django filter autofilter drilldown easy simple",
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Framework :: Django",
        "Topic :: Software Development :: User Interfaces",
    ],
    install_requires = [
        'Django>=1.3',
        'python-dateutil',
        'six'
    ],
)
