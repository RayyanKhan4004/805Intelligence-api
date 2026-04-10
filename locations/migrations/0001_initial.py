from django.db import migrations


class Migration(migrations.Migration):
    """
    Empty migration — County, City, Farm tables already exist in PostgreSQL.
    This file exists only so other apps can declare dependencies on 'locations'.
    """

    initial = True
    dependencies = []
    operations = []