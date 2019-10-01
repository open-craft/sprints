import datetime
from typing import Optional

from django.forms.widgets import (
    NumberInput,
    Select,
    Widget,
)
from django.utils.dates import MONTHS
from django.utils.safestring import mark_safe

__all__ = ('MonthYearWidget',)


class MonthYearWidget(Widget):
    """
    A Widget that splits date input into a <select> box for the month and text field for the year,
    with 'day' defaulting to the first of the month.

    Based on SelectDateWidget, in `django/trunk/django/forms/extras/widgets.py`
    """
    none_value = (0, '---')
    month_field = '%s_month'
    year_field = '%s_year'

    def __init__(self, attrs=None, required=True):
        super().__init__(attrs)
        self.attrs = attrs or {}
        self.required = required

    def render(self, name, value, attrs=None, renderer=None) -> str:
        try:
            year_val, month_val = value.year, value.month
        except AttributeError:
            now = datetime.datetime.now()
            year_val = now.year
            month_val = now.month

        output = []

        if 'id' in self.attrs:
            id_ = self.attrs['id']
        else:
            id_ = f'id_{name}'

        month_choices = list(MONTHS.items())
        if not (self.required and value):
            month_choices.append(self.none_value)
        month_choices.sort()
        local_attrs = self.build_attrs(base_attrs=self.attrs)
        s = Select(choices=month_choices)
        select_html = s.render(self.month_field % name, month_val, local_attrs)
        output.append(select_html)

        local_attrs['id'] = self.year_field % id_
        s = NumberInput()
        select_html = s.render(self.year_field % name, year_val, local_attrs)
        output.append(select_html)

        return mark_safe(u'\n'.join(output))

    def id_for_label(cls, id_) -> str:
        return cls.month_field % id_

    id_for_label = classmethod(id_for_label)  # type: ignore

    def value_from_datadict(self, data, files, name) -> Optional[str]:
        y = data.get(self.year_field % name)
        m = data.get(self.month_field % name)
        if y == m == "0":
            return None
        if y and m:
            return '%s-%s-%s' % (y, m, 1)
        return data.get(name, None)
