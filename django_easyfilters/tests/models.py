from django.db import models

from django_easyfilters.utils import python_2_unicode_compatible

BINDING_CHOICES = [
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

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


@python_2_unicode_compatible
class Book(models.Model):
    name = models.CharField(max_length=100)
    binding = models.CharField(max_length=2, choices=BINDING_CHOICES)
    authors = models.ManyToManyField(Author)
    genre = models.ForeignKey(Genre)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    date_published = models.DateField()
    edition = models.IntegerField(default=1)
    rating = models.FloatField(null=True)

    def __str__(self):
        return self.name


class Person(models.Model):
    date_of_birth = models.DateField()
    name = models.CharField(max_length=50)

