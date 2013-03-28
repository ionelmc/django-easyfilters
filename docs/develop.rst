===========
Development
===========

Tests
-----

To run the test suite, do::

   ./manage.py test django_easyfilters

This requires that the directory containing the ``django_easyfilters`` directory
is on your Python path (virtualenv recommended), and Django is installed.

Alternatively, to run it on all supported platforms, install tox and do::

   tox

This will create all the necessary virtualenvs for you, and is the preferred way
of working, but will take longer initially. Once you have run it once, you can
activate a specific virtualenv by doing, for example::

   . .tox/py33-django15/bin/activate


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
