from django.db import models


class County(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.TextField(unique=True)

    class Meta:
        db_table = 'counties'
        managed = False  # Table already exists in PostgreSQL

    def __str__(self):
        return self.name


class City(models.Model):
    county = models.ForeignKey(County, on_delete=models.RESTRICT, related_name='cities')
    name = models.CharField(max_length=255)
    city_code = models.TextField(unique=True)

    class Meta:
        db_table = 'cities'
        managed = False  # Table already exists in PostgreSQL

    def __str__(self):
        return self.name


class Farm(models.Model):
    name = models.CharField(max_length=100)
    city = models.ForeignKey(City, on_delete=models.RESTRICT, related_name='farms', null=True)

    class Meta:
        db_table = 'farms'
        managed = False  # Table already exists in PostgreSQL

    def __str__(self):
        return self.name