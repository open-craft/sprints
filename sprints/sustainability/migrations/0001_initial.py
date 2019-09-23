# Generated by Django 2.2.4 on 2019-09-23 02:12

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Account's key.", max_length=255)),
                ('date', models.DateField(help_text="Year and month of the budget. If not specified, the last month's budget is applied.")),
                ('hours', models.IntegerField(help_text='Number of available hours for this month.')),
            ],
        ),
    ]
