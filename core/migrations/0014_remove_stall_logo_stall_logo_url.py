# Generated by Django 5.2.4 on 2025-07-16 11:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_order_is_complete"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="stall",
            name="logo",
        ),
        migrations.AddField(
            model_name="stall",
            name="logo_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
