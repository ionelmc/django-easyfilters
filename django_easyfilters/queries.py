from django.db import models
from django.db.backends.util import typecast_timestamp
from django.db.models.sql.compiler import SQLCompiler
from django.db.models.sql.constants import MULTI
from django.db.models.sql.datastructures import Date
from django.db.models.sql.subqueries import AggregateQuery
from django.utils.datastructures import SortedDict


# Some fairly brittle, low level stuff, to get the aggregation
# queries we need.


class DateAggregateQuery(AggregateQuery):
    # Need to override to return a compiler not in django.db.models.sql.compiler
    def get_compiler(self, using=None, connection=None):
        return DateAggregateCompiler(self, connection, using)

    def get_counts(self, using):
        from django.db import connections
        connection = connections[using]
        return list(self.get_compiler(using, connection).results_iter())


class DateAggregateCompiler(SQLCompiler):
    def results_iter(self):
        needs_string_cast = self.connection.features.needs_datetime_string_cast

        for rows in self.execute_sql(MULTI):
            for row in rows:
                if needs_string_cast:
                    vals = [typecast_timestamp(str(row[0])),
                            row[1]]
                else:
                    vals = row
                yield vals

    def as_sql(self, qn=None):
        sql = ('SELECT %s, COUNT(%s) FROM (%s) subquery GROUP BY (%s) ORDER BY (%s)' % (
                DateWithAlias.alias, DateWithAlias.alias, self.query.subquery,
                DateWithAlias.alias, DateWithAlias.alias)
               )
        params = self.query.sub_params
        return (sql, params)


class DateWithAlias(Date):
    alias = 'easyfilter_date_alias'
    def as_sql(self, qn, connection):
        return super(DateWithAlias, self).as_sql(qn, connection) + ' as ' + self.alias


def date_aggregation(date_qs):
    """
    Performs an aggregation for a supplied DateQuerySet
    """
    # The DateQuerySet gives us a query that we need to clone and hack
    date_q = date_qs.query.clone()
    date_q.distinct = False

    # Replace 'select' to add an alias
    date_obj = date_q.select[0]
    date_q.select = [DateWithAlias(date_obj.col, date_obj.lookup_type)]

    # Now use as a subquery to do aggregation
    query = DateAggregateQuery(date_qs.model)
    query.add_subquery(date_q, date_qs.db)
    return query.get_counts(date_qs.db)


def value_counts(qs, fieldname):
    """
    Performs a simple query returning the count of each value of
    the field 'fieldname' in the QuerySet, returning the results
    as a SortedDict of value: count
    """
    values_counts = qs.values_list(fieldname).order_by(fieldname).annotate(models.Count(fieldname))
    count_dict = SortedDict()
    for val, count in values_counts:
        count_dict[val] = count
    return count_dict


class NumericAggregateQuery(AggregateQuery):
    # Need to override to return a compiler not in django.db.models.sql.compiler
    def get_compiler(self, using=None, connection=None):
        return  NumericAggregateCompiler(self, connection, using)

    def get_counts(self, using):
        from django.db import connections
        connection = connections[using]
        return list(self.get_compiler(using, connection).results_iter())


class NumericAggregateCompiler(SQLCompiler):
    def results_iter(self):
        for rows in self.execute_sql(MULTI):
            for row in rows:
                yield row

    def as_sql(self, qn=None):
        sql = ('SELECT %s, COUNT(%s) FROM (%s) subquery GROUP BY (%s) ORDER BY (%s)' % (
                NumericValueRange.alias, NumericValueRange.alias, self.query.subquery,
                NumericValueRange.alias, NumericValueRange.alias)
               )
        params = self.query.sub_params
        return (sql, params)


class NumericValueRange(object):
    alias = 'easyfilter_number_range_alias'
    def __init__(self, col, ranges):
        # ranges is list of (lower, upper) bounds we want to find, where 'lower'
        # is inclusive and upper is exclusive.
        self.col = col
        self.ranges = ranges

    # TODO - do we need 'relabel_aliases', like 'Date'?

    def as_sql(self, qn, connection):
        if isinstance(self.col, (list, tuple)):
            col = '%s.%s' % tuple([qn(c) for c in self.col])
        else:
            col = self.col

        # Build up case expression.
        clause = (['CASE '] +
                  ['WHEN %s > %s AND %s <= %s THEN %s ' % (col, val[0], col, val[1], i)
                   for i, val in enumerate(self.ranges)] +
                  # An inclusive lower limit for the first item in ranges:
                  ['WHEN %s = %s THEN 0 ' % (col, self.ranges[0][0])] +
                  ['ELSE %s END ' % len(self.ranges)] +
                  ['as %s' % self.alias])
        return ''.join(clause)


def numeric_range_counts(qs, fieldname, ranges):

    # Build the query:
    query = qs.values_list(fieldname).query.clone()
    query.select[0] = NumericValueRange(query.select[0], ranges)

    agg_query = NumericAggregateQuery(qs.model)
    agg_query.add_subquery(query, qs.db)
    results = agg_query.get_counts(qs.db)

    count_dict = SortedDict()
    for val, count in results:
        try:
            r = ranges[val]
        except IndexError:
            # Include in the top range - this could be a rounding error
            r = ranges[-1]
        count_dict[r] = count
    return count_dict

