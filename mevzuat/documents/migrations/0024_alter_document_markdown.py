from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0023_documenttype_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="document",
            name="markdown",
            field=models.TextField(blank=True, null=True),
        ),
    ]
