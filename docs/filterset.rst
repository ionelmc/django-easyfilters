=========
FilterSet
=========

.. currentmodule:: django_easyfilters.filterset

.. class:: FilterSet

   This is meant to be used by subclassing. The only required
   attribute is ``fields``, which must be a list of fields to produce filters
   for. For example, given the following model definition:

   .. code-block:: python

      class Book(models.Model):
          name = models.CharField(max_length=100)
          authors = models.ManyToManyField(Author)
          genre = models.ForeignKey(Genre)
          date_published = models.DateField()

   You could create a BookFilterSet like this:

   .. code-block:: python


       class BookFilterSet(FilterSet):
           fields = [
               'genre',
               'authors',
               'date_published',
           ]

   The items in the fields attribute can also be two-tuples containing first
   the field name and second a dictionary of options to be passed to the
   :doc:`filters <filters>` as keyword arguments.


   To use the BookFilterSet, please see :doc:`the overview instructions
   <overview>`. The public API of ``FilterSet`` for use consists of:

   .. method:: __init__(queryset, params)

      queryset must be a QuerySet, which can already be filtered.

      params must be a QueryDict, normally request.GET.

   .. attribute:: qs

      This attribute contains the input QuerySet filtered according to the data
      in ``params``.


   In addition, there are methods that can be overridden to customise the FilterSet:


   .. method:: get_template(field_name)

      This method can be overriden to render the filterset. It is called for
      each field in the filterset, with the field name being passed in.

      It is expected to return a Django Template instance. This template will
      then be rendered with the following Context data:

      * ``filterlabel`` - the label for the filter (derived from verbose_name of
        the field)
      * ``choices`` - a list of `choices` for the filter. Each one has the
        following attributes:

        * ``link_type``: either ``remove``, ``add`` or ``display``, depending
          on the type of the choice.

        * ``label``: the text to be displayed for this choice.

        * ``url`` for those that are ``remove`` or ``add``, a URL for selecting
          that filter.

        * ``count``: for those that are ``add`` links, the number of items in
          the QuerySet that match that choice.
