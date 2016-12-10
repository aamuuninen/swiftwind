# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-10-01 17:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_smalluuid.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('hordak', '0003_check_zero_amount_20160907_0921'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecurringCost',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', django_smalluuid.models.SmallUUIDField(default=django_smalluuid.models.UUIDDefault(), editable=False, unique=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('is_active', models.BooleanField(default=True)),
                ('fixed_amount', models.DecimalField(decimal_places=2, max_digits=13)),
                ('total_billing_cycles', models.PositiveIntegerField(blank=True, default=None, help_text='Stop billing after this many billing cycles.', null=True)),
                ('type', models.CharField(choices=[('normal', 'We will not have spent this yet. We will estimate a fixed amount per billing cycle.'), ('arrears_balance', "We will have already spent this in the previous billing cycle, so bill the account's balance."), ('arrears_balance', 'We will have already spent this in the previous cycle, so bill the total amount spent in the previous cycle.')], default='normal', max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='RecurringCostSplit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', django_smalluuid.models.SmallUUIDField(default=django_smalluuid.models.UUIDDefault(), editable=False, unique=True)),
                ('portion', models.DecimalField(decimal_places=2, default=1, max_digits=13)),
                ('from_account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hordak.Account')),
                ('recurring_cost', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='splits', to='costs.RecurringCost')),
            ],
        ),
        migrations.AddField(
            model_name='recurringcost',
            name='from_accounts',
            field=models.ManyToManyField(related_name='outbound_costs', through='costs.RecurringCostSplit', to='hordak.Account'),
        ),
        migrations.AddField(
            model_name='recurringcost',
            name='to_account',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inbound_costs', to='hordak.Account'),
        ),
        migrations.AlterUniqueTogether(
            name='recurringcostsplit',
            unique_together=set([('recurring_cost', 'from_account')]),
        ),
    ]