# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-12-06 01:45
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('costs', '0014_allow_initial_billing_cycle_and_disabled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recurringcost',
            name='initial_billing_cycle',
            field=models.ForeignKey(default=-1, on_delete=django.db.models.deletion.CASCADE, to='billing_cycle.BillingCycle'),
            preserve_default=False,
        ),
    ]
