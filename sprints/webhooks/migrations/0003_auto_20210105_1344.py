# Generated by Django 3.1.4 on 2021-01-05 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webhooks', '0002_webhook_extra_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='webhook',
            name='extra_data',
        ),
        migrations.AddField(
            model_name='webhook',
            name='headers',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
