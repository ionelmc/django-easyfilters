from django.db import models

from django_easyfilters.utils import python_2_unicode_compatible

BINDING_CHOICES = [
    #(None, 'Nothing'),
    ('', 'Empty'),
    ('H', 'Hardback'),
    ('P', 'Paperback'),
    ('C', 'Cloth'),
]


@python_2_unicode_compatible
class Author(models.Model):
    name = models.CharField(max_length=50)
    likes = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class Genre(models.Model):
    name = models.CharField(max_length=50)
    likes = models.IntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField(max_length=100)
    binding = models.CharField(max_length=2,
                               choices=BINDING_CHOICES,
                               null=True,
                               blank=True)
    other = models.CharField(max_length=10, blank=True)
    authors = models.ManyToManyField(Author, blank=True)
    genre = models.ForeignKey(Genre, null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    date_published = models.DateField(null=True, blank=True)
    edition = models.IntegerField(default=1, null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name


class Person(models.Model):
    date_of_birth = models.DateField()
    name = models.CharField(max_length=50)
