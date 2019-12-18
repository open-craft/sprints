from django.contrib import admin
from django.db import models

from sprints.sustainability.models import (
    Budget,
    Cell,
    Account,
)
from sprints.sustainability.widgets import MonthYearWidget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    """We want to override datepicker for the `date` field."""
    formfield_overrides = {
        models.DateField: {'widget': MonthYearWidget},
    }
    list_filter = ('name', 'date')
    search_fields = ('name',)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    pass


@admin.register(Cell)
class CellAdmin(admin.ModelAdmin):
    pass
