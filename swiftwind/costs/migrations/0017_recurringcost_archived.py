# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-02-09 15:39
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('costs', '0016_auto_20171207_1258'),
    ]

    operations = [
        migrations.AddField(
            model_name='recurringcost',
            name='archived',
            field=models.BooleanField(default=False),
        ),
    ]
