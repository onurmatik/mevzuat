from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0024_alter_document_markdown"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="markdown_status",
            field=models.CharField(
                blank=True,
                choices=[("success", "Success"), ("failed", "Failed")],
                max_length=20,
                null=True,
            ),
        ),
    ]
