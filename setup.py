#!/usr/bin/env python
# encoding: utf8
import io
import os

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    return io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()

setup(
    name="django-easyfilters-ex",
    version='0.7.0',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    author="Luke Plant",
    author_email="L.Plant.98@cantab.net",
    maintainer='Ionel Cristian Mărieș',
    maintainer_email='contact@ionelmc.ro',
    url="https://github.com/ionelmc/django-easyfilters/",
    description="Easy creation of link-based filtering for a list of Django model objects.",
    long_description=read('README.rst') + "\n\n" + read('CHANGES.rst'),
    license="MIT",
    keywords="django filter autofilter drilldown easy simple",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        "Framework :: Django",
        "Topic :: Software Development :: User Interfaces",
    ],
    install_requires=[
        'Django>=1.3',
        'python-dateutil',
        'six'
    ],
)
