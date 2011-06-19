====================
 Django EasyFilters
====================

Overview
========


Usage
=====



Development
===========

First, ensure the directory containing this README is on your Python path
(virtualenv recommended). Django is a required dependency.

To run the test suite, do::

   ./manage.py test django_easyfilters

To edit the test fixtures, first create an empty db:

   rm tests.db
   ./manage.py syncdb

Then load with current test fixture:

   ./manage.py loaddata django_easyfilters_tests

Then edit in admin at http://localhost:8000/admin/ ::

   ./manage.py runserver

Or from a Python shell.

Then dump data::

  ./manage.py dumpdata tests --format=json --indent=2 > django_easyfilters/tests/fixtures/django_easyfilters_tests.json
