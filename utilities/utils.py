import json
import locale
import math
import os
import random
from collections import namedtuple, OrderedDict
from datetime import datetime, timedelta

import requests
# import waffle
# from admin_decorators import short_description, allow_tags
# from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import admin
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.models.fields.files import FieldFile
from django.db.models.fields.files import FileField
from django.http import HttpResponse, JsonResponse
from django.template import engines
from django.urls import resolve
from django.utils import encoding
from django.utils.encoding import Promise, force_text
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView
# from django_countries.fields import Country
# from django_tables2 import Table

# from utilities.constants import FeatureFlag
# from utilities.decorators import exclude_dump

locale.setlocale(locale.LC_ALL, '')

QUARTER_MAP = {}
QUARTER_MAP.update(dict(zip((1, 2, 3), ('Q1',) * 3)))
QUARTER_MAP.update(dict(zip((4, 5, 6), ('Q2',) * 3)))
QUARTER_MAP.update(dict(zip((7, 8, 9), ('Q3',) * 3)))
QUARTER_MAP.update(dict(zip((10, 11, 12), ('Q4',) * 3)))

MONTH_NAMES_ABBREV = [('01', 'Jan'),
                      ('02', 'Feb'),
                      ('03', 'Mar'),
                      ('04', 'Apr'),
                      ('05', 'May'),
                      ('06', 'Jun'),
                      ('07', 'Jul'),
                      ('08', 'Aug'),
                      ('09', 'Sep'),
                      ('10', 'Oct'),
                      ('11', 'Nov'),
                      ('12', 'Dec')]

MONTH_NAMES = [('01', 'January'),
               ('02', 'February'),
               ('03', 'March'),
               ('04', 'April'),
               ('05', 'May'),
               ('06', 'June'),
               ('07', 'July'),
               ('08', 'August'),
               ('09', 'September'),
               ('10', 'October'),
               ('11', 'November'),
               ('12', 'December')]

MONTH_NAMES_DICT = dict(MONTH_NAMES)
MONTH_NAMES_ABBREV_DICT = dict(MONTH_NAMES_ABBREV)
MONTH_INT_NAMES_DICT = dict((int(k), v) for (k, v) in MONTH_NAMES)
MONTH_NAMES_ABBREV_INT_DICT = dict((int(k), v) for (k, v) in MONTH_NAMES_ABBREV)


def get_month_label(month, abbrev=False):
    return MONTH_NAMES_ABBREV_INT_DICT[int(month)] if abbrev else MONTH_INT_NAMES_DICT[int(month)]


def get_year_month_label(year, month, abbrev=False):
    return f'{get_month_label(month, abbrev)} {year}'




def is_int(s):
    try:
        if math.floor(float(s)) == float(s):
            return True
        else:
            return False
    except Exception:
        return False


def is_number(s):
    try:
        float(s)
        return True
    except Exception:
        return False



def truncate(value, digits):
    return int(value * math.pow(10, digits)) / math.pow(10, digits)


def fix_decimal_product_no(value):
    if str(value)[-2:] == '.0':
        return str(value)[:-2]
    else:
        return str(value)


def strip_non_alpha_numeric(string):
    import re
    cleansed_string = re.sub("[^0-9A-Za-z]", "", string)
    return cleansed_string


def to_json(obj):
    return json.dumps(obj, default=lambda o: o.__dict__, sort_keys=True, indent=4)


def _json_object_hook(d): return namedtuple('X', d.keys())(*d.values())


def from_json(data): return json.loads(data, object_hook=_json_object_hook)


def save_and_return_bytes(wb):
    file_path = get_temp_file_path()
    wb.save(file_path)
    return get_bytes_and_delete(file_path)


def get_bytes_and_delete(file_path):
    data = get_bytes(file_path)
    delete_file(file_path)
    return data


def delete_file(file_path):
    try:
        os.remove(file_path)
        return True
    except:
        return False


def rename_file(old_name, new_name):
    os.rename(old_name, new_name)


def move_file(source, destination):
    os.rename(source, destination)


def get_bytes(file_path):
    in_file = open(file_path, "rb")  # opening for [r]eading as [b]inary
    data = in_file.read()  # if you only wanted to read 512 bytes, do .read(512)
    in_file.close()
    return data


def get_temp_file_path(extn=None):
    import uuid
    file_name = str(uuid.uuid4()) + (f'.{extn}' if extn else '')
    file_path = os.path.join(settings.MEDIA_ROOT, "tmp", file_name)
    return file_path


def xstr(s):
    return '' if s is None else str(s)


def prepend_project_directory(directory_name):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), directory_name)


def unicode_to_string(x):
    return encoding.smart_str(x, encoding='ascii', errors='ignore')



def coalesce(value, replace):
    if value is None:
        return replace
    return value


def query_to_dicts(query_string, params=None):
    """Run a simple query and produce a generator
    that returns the results as a bunch of dictionaries
    with keys for the column values selected.
    """
    cursor = connection.cursor()
    cursor.execute(query_string, params)
    col_names = [desc[0] for desc in cursor.description]
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        row_dict = dict(zip(col_names, row))
        yield row_dict
    cursor.close()
    return


def query_to_lists(query_string, col_index=None, params=None):
    """Run a simple query and produce a generator
    that returns the results as a bunch of dictionaries
    with keys for the column values selected.
    """
    cursor = connection.cursor()
    cursor.execute(query_string, params)
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        yield row[col_index] if col_index is not None else row
    cursor.close()
    return


def field_html(field, name):
    from django import forms

    class TempForm(forms.Form):
        def __init__(self, *args, **kwargs):
            super(TempForm, self).__init__(*args, **kwargs)
            self.fields[name] = field

    form = TempForm()
    from django.template import Context, Template
    t = Template("{{form.%s}}" % name)
    c = Context({'form': form})
    return t.render(c)



class TempFiles(object):
    def __init__(self, *files):
        self.files = files

    def __exit__(self, exc_type, exc_val, exc_tb):
        for f in self.files:
            f.close()

    def __enter__(self):
        return self.files



def render_to_string_from_source(template_source, context_dict=None):
    t = engines['django'].from_string(template_source)
    return t.render(context_dict)


def get_exchange_rates():
    try:
        r = requests.get('http://api.fixer.io/latest?base=USD')
        return json.loads(r.text)
    except:
        return {}


def sum_by_tuple_element_in_list(input_list, decimal_places=None):
    """
    :param input_list: e.g. [('Jan 2015', 1544.4), ('Jan 2015', 200.0), ('May 2016', 499.0)]
    :return: list of tuples with sum of values grouped by first element in tuple
    """
    distinct_group_values = OrderedDict(input_list).keys()
    for group in distinct_group_values:
        sum_of_elements = sum(val for (key, val) in input_list if key == group)
        if decimal_places is not None:
            sum_of_elements = round(sum_of_elements, decimal_places)
        yield (group, sum_of_elements)


def median(input_list):
    quotient, remainder = divmod(len(input_list), 2)
    if remainder:
        return sorted(input_list)[quotient]
    return float(sum(sorted(input_list)[quotient - 1:quotient + 1]) / 2)


def mode(input_list):
    m = max([input_list.count(a) for a in input_list])
    return [x for x in input_list if input_list.count(x) == m][0] if m > 1 else 0


def math_range(input_list):
    return max(input_list) - min(input_list) if input_list else 0


def get_subclasses(classes, level=0):
    """
        Return the list of all subclasses given class (or list of classes) has.
        Inspired by this question:
        http://stackoverflow.com/questions/3862310/how-can-i-find-all-subclasses-of-a-given-class-in-python
    """
    # for convenience, only one class can can be accepted as argument
    # converting to list if this is the case
    if not isinstance(classes, list):
        classes = [classes]

    if level < len(classes):
        classes += classes[level].__subclasses__()
        return get_subclasses(classes, level + 1)
    else:
        return classes


def image(instance, file_name, image_url):
    if image_url:
        urls = [image_url, instance.find_full_image_url(file_name)]
        return mark_safe('<br>Full Image:<br>'.join([
            "<a href='%(image_url)s' target='_blank'><img style='max-width: 100px' src='%(image_url)s' alt='Image 1'"
            " /></a>" % {'image_url': url} for url in urls if url]))


def get_current_quarter():
    current_quarter = QUARTER_MAP[datetime.now().month]
    return current_quarter, list((k for (k, v) in QUARTER_MAP.items() if v == current_quarter))


def get_quarter(quarter_number):
    quarter = 'Q%s' % quarter_number
    return quarter, list((k for (k, v) in QUARTER_MAP.items() if v == quarter))


def get_pdf_response_from_file(pdf, file_name):
    response = HttpResponse(pdf, content_type='application/pdf')
    response["X-Accel-Buffering"] = "no"
    response['Content-Disposition'] = 'inline; filename=%s.pdf' % file_name
    return response


def format_as_currency(value, decimal_precision=2):
    if value is None:
        return value
    if not is_number(value):
        return value
    value = float(value)
    is_negative = value < 0
    display_format = '<span class="text-danger">(%s)</span>' if is_negative else '%s'
    decimal_precision = decimal_precision if is_int(decimal_precision) and decimal_precision >= 0 else 2
    return mark_safe(display_format % ('$%s' % ('{:20,.%sf}' % decimal_precision).format(math.fabs(value)).strip()))














