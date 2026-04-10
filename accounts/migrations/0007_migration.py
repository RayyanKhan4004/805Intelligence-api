from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_userprofile_password_reset_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_portfolio_admin',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='PortfolioUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=150)),
                ('last_name', models.CharField(max_length=150)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('access_level', models.CharField(choices=[('no_access', 'No Access'), ('read_only', 'Read Only'), ('account_admin', 'Account Admin')], default='no_access', max_length=20)),
                ('is_portfolio_admin', models.BooleanField(default=False)),
                ('invite_token', models.UUIDField(default=uuid.uuid4, unique=True)),
                ('invite_sent_at', models.DateTimeField(blank=True, null=True)),
                ('invite_accepted', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('portfolio_admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='managed_users', to=settings.AUTH_USER_MODEL)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='portfolio_membership', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]