from django.db import models
from locations.models import County, City, Farm


class Property(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Closed', 'Closed'),
        ('Pending', 'Pending'),
        ('Cancelled', 'Cancelled'),
        ('Expired', 'Expired'),
    ]

    parcel_number = models.CharField(max_length=100, blank=True)
    use_code_description = models.CharField(max_length=255, blank=True)
    sold_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    close_date = models.DateTimeField(null=True, blank=True)
    street_address = models.CharField(max_length=255, blank=True)
    full_address = models.CharField(max_length=500, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.FloatField(null=True, blank=True)
    sqft = models.IntegerField(null=True, blank=True)
    price_per_sqft = models.FloatField(null=True, blank=True)
    list_price = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    listing_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, blank=True)
    owner_occupied = models.CharField(max_length=5, blank=True)
    full_mail_address = models.CharField(max_length=500, blank=True)

    # Foreign keys
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, blank=True)
    farm = models.ForeignKey(Farm, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'properties'
        managed = False  # Table already exists in PostgreSQL

    def __str__(self):
        return self.full_address or self.street_address