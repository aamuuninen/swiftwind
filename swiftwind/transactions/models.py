import csv
from io import StringIO
import six
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django_smalluuid.models import SmallUUIDField, uuid_default
from model_utils import Choices
from tablib.core import Dataset

from .utilities import DATE_FORMATS


# TODO: Rename models, as we're importing statement lines not transactions
class TransactionImport(models.Model):
    STATES = Choices(
        ('pending', 'Pending'),
        ('uploaded', 'Uploaded, ready to import'),
        ('done', 'Import complete'),
    )

    uuid = SmallUUIDField(default=uuid_default(), editable=False)
    timestamp = models.DateTimeField(default=timezone.now, editable=False)
    has_headings = models.BooleanField(default=True, verbose_name='First line of file contains headings')
    file = models.FileField(upload_to='transaction_imports', verbose_name='CSV file to import')
    state = models.CharField(max_length=20, choices=STATES, default='pending')
    date_format = models.CharField(choices=DATE_FORMATS, max_length=50, default='%d-%m-%Y', null=False)
    hordak_import = models.ForeignKey('hordak.StatementImport')

    def _get_csv_reader(self):
        # TODO: Refactor to support multiple readers (xls, quickbooks, etc)
        csv_buffer = StringIO(self.file.read().decode())
        return csv.reader(csv_buffer)

    def _get_mapping_dict(self):
        """Get a dict which maps db field name to column number"""
        mappings = {}
        for column in self.columns.all():
            if column.to_field:
                mappings[column.to_field] = column.column_number - 1
        return mappings

    def _parse_row(self, row, mapping):
        """Returns a tuple of (date, amount, description)"""
        F = TransactionImportColumn.TO_FIELDS
        date = row[mapping[F.date]]
        description = row[mapping[F.description]]

        # Do we have in/out columns, or just one amount column?
        if F.amount_out in mapping and F.amount_in in mapping:
            amount_out = row[mapping[F.amount_out]]
            amount_in = row[mapping[F.amount_in]]
            if amount_out:
                amount = abs(Decimal(amount_out)) * -1
            else:
                amount = abs(Decimal(amount_in))
        else:
            amount = Decimal(row[mapping[F.amount]])

        return date, amount, description

    def create_columns(self):
        """For each column in file create a TransactionImportColumn"""
        reader = self._get_csv_reader()
        headings = six.next(reader)
        try:
            examples = six.next(reader)
        except StopIteration:
            examples = []

        for i, value in enumerate(headings):
            if i >= 20:
                break

            TransactionImportColumn.objects.update_or_create(
                transaction_import=self,
                column_number=i + 1,
                column_heading=value if self.has_headings else '',
                to_field='',
                example=examples[i] if examples else '',
            )

    def get_dataset(self):
        reader = self._get_csv_reader()
        if self.has_headings:
            six.next(reader)

        data = []
        mapping = self._get_mapping_dict()
        for row in reader:
            data.append(self._parse_row(row, mapping))

        return Dataset(*data, headers=['date', 'amount', 'description'])


class TransactionImportColumn(models.Model):
    """ Represents a column in an imported file

    Stores information regarding how we map to the data in the column
    to our hordak.StatementLine models.
    """
    TO_FIELDS = Choices(
        ('', '-'),
        ('date', 'Date'),
        ('amount', 'Amount'),
        ('amount_out', 'Amount (money in only)'),
        ('amount_in', 'Amount (money out only)'),
        ('description', 'Description / Notes'),
    )

    transaction_import = models.ForeignKey(TransactionImport, related_name='columns')
    column_number = models.PositiveSmallIntegerField()
    column_heading = models.CharField(max_length=100, default='', blank=True, verbose_name='Column')
    # TODO: Create a constraint to limit to_field to only valid values
    to_field = models.CharField(max_length=20, blank=True, default=None, null=True, choices=TO_FIELDS, verbose_name='Is')
    example = models.CharField(max_length=200, blank=True, default='', null=False)

    class Meta:
        unique_together = (
            ('transaction_import', 'to_field'),
            ('transaction_import', 'column_number'),
        )
        ordering = ['transaction_import', 'column_number']

    def save(self, *args, **kwargs):
        if not self.to_field:
            self.to_field = None
        return super(TransactionImportColumn, self).save(*args, **kwargs)
