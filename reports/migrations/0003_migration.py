from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_view_tracking'),
    ]

    operations = [
        # Remove old fields
        migrations.RemoveField(model_name='reportresult', name='median_sale_price'),
        migrations.RemoveField(model_name='reportresult', name='days_on_market'),
        migrations.RemoveField(model_name='reportresult', name='list_to_sale_ratio'),
        migrations.RemoveField(model_name='reportresult', name='price_reductions_pct'),
        migrations.RemoveField(model_name='reportresult', name='new_listings'),
        migrations.RemoveField(model_name='reportresult', name='closed_sales'),

        # Add new fields
        migrations.AddField(
            model_name='reportresult',
            name='avg_dom',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportresult',
            name='median_dom',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportresult',
            name='market_action_index',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reportresult',
            name='market_type',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='reportresult',
            name='price_decreased_pct',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='reportresult',
            name='price_increased_pct',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='reportresult',
            name='median_new_listing_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]