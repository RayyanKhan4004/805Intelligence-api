from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    """
    Uses plain IntegerFields for county/city/farm FKs in the migration.
    The actual FK constraints already exist in PostgreSQL via the unmanaged models.
    """

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('generated', 'Generated')], default='draft', max_length=20)),
                ('metrics', models.JSONField(default=list)),
                ('format', models.CharField(choices=[('pdf', 'PDF'), ('web', 'Web'), ('email', 'Email')], default='pdf', max_length=20)),
                ('visibility', models.CharField(choices=[('private', 'Private'), ('shared', 'Shared'), ('public', 'Public')], default='private', max_length=20)),
                ('schedule', models.CharField(choices=[('one_time', 'One Time'), ('weekly', 'Weekly'), ('monthly', 'Monthly')], default='one_time', max_length=20)),
                ('agent_name', models.CharField(blank=True, max_length=255)),
                ('agent_logo_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to=settings.AUTH_USER_MODEL)),
                # Store location IDs as plain integers — unmanaged tables already have the real FK constraints
                ('county_id', models.IntegerField(null=True, blank=True)),
                ('city_id', models.IntegerField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='ReportFarm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reports.report')),
                ('farm_id', models.IntegerField()),
            ],
            options={
                'db_table': 'reports_report_farms',
            },
        ),
        migrations.CreateModel(
            name='ReportResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('calculated_at', models.DateTimeField(auto_now=True)),
                ('median_list_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('median_sale_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('price_per_sqft', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('days_on_market', models.FloatField(blank=True, null=True)),
                ('inventory', models.IntegerField(blank=True, null=True)),
                ('list_to_sale_ratio', models.DecimalField(blank=True, decimal_places=4, max_digits=6, null=True)),
                ('price_reductions_pct', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('new_listings', models.IntegerField(blank=True, null=True)),
                ('closed_sales', models.IntegerField(blank=True, null=True)),
                ('report', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='result', to='reports.report')),
            ],
        ),
    ]