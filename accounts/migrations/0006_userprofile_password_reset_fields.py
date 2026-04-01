from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_userprofile_email_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='password_reset_token',
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='password_reset_expires',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
