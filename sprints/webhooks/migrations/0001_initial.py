# Generated by Django 3.1.5 on 2021-01-26 00:02

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='WebhookEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Webhook',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payload_url', models.URLField()),
                ('active', models.BooleanField()),
                ('headers', models.JSONField(blank=True, null=True)),
                ('events', models.ManyToManyField(to='webhooks.WebhookEvent')),
            ],
        ),
    ]
