Changelog
=========

Version 0.7.0
-------------

* Fix bug with DateTimeFilter on Django 1.6 and add support for filtering NULLs in ForeignKey filters (contributed by
  Eugene A Brin in PR#9)

Version 0.6.2
-------------

* Add a ``show_counts`` option on filters.
* Add a ``defaults`` option on filterset so you don't have to specify the same options for every filter.

Version 0.6.1
-------------

* Fix broken import / error handling in utils.

Version 0.6
-----------

* Fixed compat with django 1.6 and 1.7
* Fixed handling around NULL values
* Fixed inconsistencies with "display" links
* Add support for filters on forward relations (eg: fk1__fk2__finalfield)

Version 0.5
-----------

* Python 3.3 compatibility :-) Tests are run against Python 2.6, 2.7 and 3.3,
  and Django 1.3 to 1.5

Version 0.4
-----------

* Cleaned up internal ``Filter`` implementation/API

* Added and documented ``Filter.render_choice_object`` which can
  be overridden for easy customization of filters.

* Fixed various bugs with DateTimeFilter. Thanks to psyton for a bug fix.

Version 0.3.2
-------------

* Correction to new ``FilterSet.title`` attribute.

Version 0.3.1
-------------

* Fixed crasher in 0.3

Version 0.3
-----------

* Added the ``FilterSet.title`` attribute, and the ``title_fields`` attribute
  that can be used to control it.

Version 0.2
-----------

* Added NumericRangeFilter

* More docs, and API firmed up.

* Fixed bug with test_settings.py which caused static media not to be served
  with most recent Django.

Version 0.1.1
-------------

Cleaned up the release tarball to remove old files.

Version 0.1
-----------

Initial release
