import datetime
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.db import models
from django.db.models import Q, Sum, When, Case, Value, Subquery, OuterRef, Exists
from django.db.models.functions import Cast
from django.test import RequestFactory
from django.urls.base import reverse
from django.views import View
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from djmoney.models.fields import MoneyField

from hordak.models.core import Account, Transaction, Leg
from swiftwind.billing_cycle.models import BillingCycle
from swiftwind.settings.models import Settings
from swiftwind.costs.models import RecurringCostSplit
from swiftwind.housemates.models import Housemate
from swiftwind.utilities.emails import EmailViewMixin
from swiftwind.utilities.site import get_site_root


class OverviewView(LoginRequiredMixin, ListView):
    template_name = 'accounts/overview.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        housemate_income = Account.objects.get(name='Housemate Income')
        expenses = Account.objects.get(name='Expenses')
        current_billing_cycle = BillingCycle.objects.as_of(datetime.date.today())

        return Account.objects.filter(

            # We want any account under 'Housemate Income' or 'Expenses'
            Q(lft__gt=housemate_income.lft, rght__lt=housemate_income.rght, tree_id=housemate_income.tree_id)
            |
            Q(lft__gt=expenses.lft, rght__lt=expenses.rght, tree_id=expenses.tree_id)

        ).filter(
            # We only want leaf accounts (no accounts that contain other accounts)
            children__isnull=True

        ).annotate(
            # Is this an expense or housemate account?
            display_type=Case(
                When(housemate__isnull=True, then=Value('expense')),
                default=Value('housemate'),
                output_field=models.CharField()
            )

        ).annotate(
            # When was the last transaction
            latest_transaction_date=Subquery(
                Transaction.objects.filter(legs__account=OuterRef('pk')).order_by('-date').values('date')[:1]
            )

        ).annotate(
            # Has there been a payment during this billing cycle
            payment_since_last_bill=Exists(
                Transaction.objects.filter(
                    legs__amount__gt=0,
                    legs__account=OuterRef('pk'),
                    date__gte=current_billing_cycle.date_range.lower
                )
            )

        )\
            .order_by('-display_type')\
            .select_related('housemate')


class AbstractHousemateStatementView(DetailView):
    template_name = 'accounts/housemate_statement.html'
    slug_url_kwarg = 'uuid'
    slug_field = 'uuid'
    context_object_name = 'housemate'
    queryset = Housemate.objects.all().select_related('account', 'user')

    def get_context_data(self, **kwargs):
        housemate = self.object
        date = self.kwargs.get('date')

        billing_cycle = BillingCycle.objects.as_of(
            date=datetime.date(*map(int, date.split('-'))) if date else datetime.date.today()
        )

        legs = Leg.objects.filter(
            transaction__recurred_cost__billing_cycle=billing_cycle,
            account=housemate.account,
        ).order_by('-transaction__date', '-pk').select_related(
            'transaction',
            'transaction__recurred_cost__recurring_cost__to_account',
        )
        recurring_legs = [l for l in legs if not l.transaction.recurred_cost.recurring_cost.is_one_off()]
        one_off_legs = [l for l in legs if l.transaction.recurred_cost.recurring_cost.is_one_off()]
        other_legs = Leg.objects.filter(
            transaction__date__gte=billing_cycle.date_range.lower,
            transaction__date__lt=billing_cycle.date_range.upper,
            account=housemate.account,
        ).exclude(
            pk__in=[l.pk for l in legs]
        ).order_by('-transaction__date', '-pk').select_related('transaction')

        recurring_total = sum(l.amount for l in recurring_legs)
        one_off_total = sum(l.amount for l in one_off_legs)

        # Previous & next URLs
        # Not a pretty way to generate URLs, but parsing the date to reverse the
        # historical URL would be pretty onerous.
        previous = billing_cycle.get_previous()
        next = billing_cycle.get_next()

        if previous:
            previous_url = '{}{}/'.format(reverse('accounts:housemate_statement', args=[housemate.uuid]), str(previous.start_date))
        else:
            previous_url = ''

        if next and next.start_date <= datetime.date.today():
            next_url = '{}{}/'.format(reverse('accounts:housemate_statement', args=[housemate.uuid]), str(next.start_date))
        else:
            next_url = ''

        return super().get_context_data(
            billing_cycle=billing_cycle,
            start_date=billing_cycle.date_range.lower,
            end_date=billing_cycle.date_range.upper - timedelta(days=1),
            recurring_legs=recurring_legs,
            one_off_legs=one_off_legs,
            other_legs=other_legs,
            recurring_total=recurring_total,
            one_off_total=one_off_total,
            total=recurring_total + one_off_total,
            payment_history=housemate.account.legs.all().order_by('-transaction__date', '-transaction__pk'),
            payment_information=Settings.objects.get().payment_information,
            next_url=next_url,
            previous_url=previous_url,
            **kwargs
        )


class HousemateStatementView(LoginRequiredMixin, AbstractHousemateStatementView):
    pass


class StatementEmailView(EmailViewMixin, AbstractHousemateStatementView):
    template_name = 'accounts/statement_email.html'


class ReconciliationRequiredEmailView(EmailViewMixin, TemplateView):
    template_name = 'accounts/reconciliation_required_email.html'
