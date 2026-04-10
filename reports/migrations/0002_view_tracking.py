from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='views_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='report',
            name='last_viewed_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]