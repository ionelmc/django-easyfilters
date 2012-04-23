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
