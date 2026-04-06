from django.db import models
from django.contrib.auth.models import User


class Report(models.Model):

    FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('web', 'Web'),
        ('email', 'Email'),
    ]

    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('shared', 'Shared'),
        ('public', 'Public'),
    ]

    SCHEDULE_CHOICES = [
        ('one_time', 'One Time'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generated', 'Generated'),
    ]

    METRIC_CHOICES = [
        ('median_list_price', 'Median List Price'),
        ('median_sale_price', 'Median Sale Price'),
        ('price_per_sqft', 'Price Per Sq. Ft.'),
        ('days_on_market', 'Days on Market'),
        ('inventory', 'Inventory / Active Listings'),
        ('list_to_sale_ratio', 'List-to-Sale Price Ratio'),
        ('price_reductions', 'Price Reductions %'),
        ('new_vs_closed', 'New Listings vs. Closed Sales'),
    ]

    # Core
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Location stored as plain IDs (unmanaged tables handle real FK constraints)
    county_id = models.IntegerField(null=True, blank=True)
    city_id = models.IntegerField(null=True, blank=True)

    # Metrics
    metrics = models.JSONField(default=list)

    # Settings
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='pdf')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    schedule = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default='one_time')

    # Branding
    agent_name = models.CharField(max_length=255, blank=True)
    agent_logo_url = models.URLField(blank=True)

    # Helper properties to access location objects
    @property
    def county(self):
        if self.county_id:
            from locations.models import County
            return County.objects.filter(id=self.county_id).first()
        return None

    @property
    def city(self):
        if self.city_id:
            from locations.models import City
            return City.objects.filter(id=self.city_id).first()
        return None

    @property
    def farms(self):
        from locations.models import Farm
        farm_ids = ReportFarm.objects.filter(report=self).values_list('farm_id', flat=True)
        return Farm.objects.filter(id__in=farm_ids)

    def set_farms(self, farm_ids):
        ReportFarm.objects.filter(report=self).delete()
        ReportFarm.objects.bulk_create([
            ReportFarm(report=self, farm_id=fid) for fid in farm_ids
        ])

    def __str__(self):
        return f"{self.name} ({self.user.email})"


class ReportFarm(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    farm_id = models.IntegerField()

    class Meta:
        db_table = 'reports_report_farms'


class ReportResult(models.Model):
    report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='result')
    calculated_at = models.DateTimeField(auto_now=True)

    median_list_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    median_sale_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_per_sqft = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    days_on_market = models.FloatField(null=True, blank=True)
    inventory = models.IntegerField(null=True, blank=True)
    list_to_sale_ratio = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    price_reductions_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    new_listings = models.IntegerField(null=True, blank=True)
    closed_sales = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Results for {self.report.name}"