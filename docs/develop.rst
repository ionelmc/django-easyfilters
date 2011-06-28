===========
Development
===========

Python 2.6 is required for running the test suites and demo app.

First, ensure the directory containing the ``django_easyfilters`` directory is
on your Python path (virtualenv recommended). Django is a required dependency.

Tests
-----

To run the test suite, do::

   ./manage.py test django_easyfilters

Editing test fixtures
---------------------

To edit the test fixtures, you can edit the fixtures in
django_easyfilters/tests/fixtures/, or you can do it via an admin interface:

First create an empty db::

   rm tests.db
   ./manage.py syncdb

Then load with current test fixture::

   ./manage.py loaddata django_easyfilters_tests

Then edit in admin at http://localhost:8000/admin/ ::

   ./manage.py runserver

Or from a Python shell.

Then dump data::

  ./manage.py dumpdata tests --format=json --indent=2 > django_easyfilters/tests/fixtures/django_easyfilters_tests.json


Demo
----

Once the test fixtures have been loaded into the DB, and the devserver is
running, as above, you can view a test page at http://localhost:8000/books/
