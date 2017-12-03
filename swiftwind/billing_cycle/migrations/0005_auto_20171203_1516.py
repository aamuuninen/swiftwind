# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-03 15:16
from __future__ import unicode_literals

import django.contrib.postgres.fields.ranges
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('billing_cycle', '0004_auto_20161001_1707'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billingcycle',
            name='date_range',
            field=django.contrib.postgres.fields.ranges.DateRangeField(db_index=True, help_text='The start and end date of this billing cycle. May not overlay with any other billing cycles.'),
        ),
    ]
