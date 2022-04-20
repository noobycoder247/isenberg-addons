from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
import os
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from datetime import datetime
from io import StringIO

import pdfkit
from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
from PyPDF2.generic import NameObject, NumberObject, IndirectObject, BooleanObject
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import formats
from pdfkit.configuration import Configuration
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import resolve1
from xhtml2pdf import pisa

from utilities.utils import get_temp_file_path, get_bytes_and_delete, delete_file, move_file, get_pdf_response_from_file, \
    prepend_project_directory, render_to_string_from_source



def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

class PDFHelper:
    def __init__(self):
        pass

    def extract_pdf_form(self, filename):
        with open(filename, 'rb') as file:
            return self.extract_pdf_from_file(file)

    @staticmethod
    def extract_pdf_from_file(file):
        parser = PDFParser(file)
        doc = PDFDocument(parser)
        # doc.initialize()
        fields = resolve1(doc.catalog['AcroForm'])['Fields']
        form_fields = dict()
        for i in fields:
            field = resolve1(i)
            name, value = field.get('T'), field.get('V')
            form_fields[name] = value
        return form_fields

    @staticmethod
    def merge(files, destination=None, delete_source=False):
        if not destination:
            destination = get_temp_file_path()
        merger = PdfFileMerger()
        for file_path in files:
            merger.append(PdfFileReader(open(file_path, 'rb')), import_bookmarks=False)
        merger.write(open(destination, 'wb'))
        if delete_source:
            for file_path in files:
                delete_file(file_path)
        return destination

    @staticmethod
    def append(base_file, append_file, delete_append_file=False):
        files = [base_file, append_file]
        temp_file = get_temp_file_path()
        PDFHelper.merge(files, temp_file)
        delete_file(base_file)
        move_file(temp_file, base_file)
        if delete_append_file:
            delete_file(append_file)

    @staticmethod
    def _get_fields(obj, tree=None, retval=None, fileobj=None):
        """
        Extracts field data if this PDF contains interactive form fields.
        The *tree* and *retval* parameters are for recursive use.

        :param fileobj: A file object (usually a text file) to write
            a report to on all interactive form fields found.
        :return: A dictionary where each key is a field name, and each
            value is a :class:`Field<PyPDF2.generic.Field>` object. By
            default, the mapping name is used for keys.
        :rtype: dict, or ``None`` if form data could not be located.
        """
        field_attributes = {'/FT': 'Field Type', '/Parent': 'Parent', '/T': 'Field Name', '/TU': 'Alternate Field Name',
                            '/TM': 'Mapping Name', '/Ff': 'Field Flags', '/V': 'Value', '/DV': 'Default Value'}
        if retval is None:
            retval = OrderedDict()
            catalog = obj.trailer["/Root"]
            # get the AcroForm tree
            if "/AcroForm" in catalog:
                tree = catalog["/AcroForm"]
            else:
                return None
        if tree is None:
            return retval

        obj._checkKids(tree, retval, fileobj)
        for attr in field_attributes:
            if attr in tree:
                # Tree is a field
                obj._buildField(tree, retval, fileobj, field_attributes)
                break

        if "/Fields" in tree:
            fields = tree["/Fields"]
            for f in fields:
                field = f.getObject()
                obj._buildField(field, retval, fileobj, field_attributes)

        return retval

    @staticmethod
    def get_form_fields(infile):
        infile = PdfFileReader(open(infile, 'rb'))
        fields = PDFHelper._get_fields(infile)
        return OrderedDict((k, v.get('/V', '')) for k, v in fields.items())

    @staticmethod
    def update_form_values(infile, outfile, data):
        with open(infile, "rb") as f:
            pdf = PdfFileReader(f)

            if "/AcroForm" in pdf.trailer["/Root"]:
                pdf.trailer["/Root"]["/AcroForm"].update(
                    {NameObject("/NeedAppearances"): BooleanObject(True)})

            writer = PdfFileWriter()

            PDFHelper.set_need_appearances_writer(writer)

            if "/AcroForm" in writer._root_object:
                writer._root_object["/AcroForm"].update(
                    {NameObject("/NeedAppearances"): BooleanObject(True)})

            for i in range(pdf.getNumPages()):
                page = pdf.getPage(i)
                try:
                    writer.updatePageFormFieldValues(page, data)
                    PDFHelper.flatten_fields(page, PDFHelper.get_form_fields(infile))
                except Exception as e:
                    print(repr(e))
                finally:
                    writer.addPage(page)

            with open(outfile, 'wb') as out:
                writer.write(out)

    @staticmethod
    def set_need_appearances_writer(writer: PdfFileWriter):
        try:
            catalog = writer._root_object
            # get the AcroForm tree
            if "/AcroForm" not in catalog:
                writer._root_object.update({
                    NameObject("/AcroForm"): IndirectObject(len(writer._objects), 0, writer)})

            need_appearances = NameObject("/NeedAppearances")
            writer._root_object["/AcroForm"][need_appearances] = BooleanObject(True)
            return writer

        except Exception as e:
            print('set_need_appearances_writer() catch : ', repr(e))
            return writer

    @staticmethod
    def flatten_fields(page, fields):
        for j in range(0, len(page['/Annots'])):
            writer_annot = page['/Annots'][j].getObject()
            for field in fields:
                if writer_annot.get('/T') == field:
                    writer_annot.update({
                        NameObject("/Ff"): NumberObject(1)  # make ReadOnly
                    })


class PdfCreatorMeta(metaclass=ABCMeta):

    def __init__(self,
                 html=None,
                 template_name=None,
                 context_data={},
                 append_tnc=False
                 ):
        if not html and not template_name:
            raise Exception("Either html or template_name is required")
        context_data = context_data or {}
        self.html = html or render_to_string(template_name, context_data)
        self.append_tnc = append_tnc
        self.pdf_helper = PDFHelper()

    @abstractmethod
    def _get_file_path_from_lib(self):
        raise NotImplementedError

    def get_path(self):
        file_path = self._get_file_path_from_lib()
        if self.append_tnc:
            self.pdf_helper.append_tnc(file_path)
        return file_path

    def get_file(self):
        file_path = self.get_path()
        return open(file_path, 'rb')

    def get_bytes(self):
        pdf_file = self.get_file()
        return get_bytes_and_delete(pdf_file.name)

    def get_http_response(self, file_name):
        pdf = self.get_file()
        return get_pdf_response_from_file(pdf, file_name)


class PisaPdfCreator(PdfCreatorMeta):
    def _get_file_path_from_lib(self):
        file_path = get_temp_file_path('pdf')
        with open(file_path, "w+b") as pdf_file:
            pisa.CreatePDF(StringIO(self.html), dest=pdf_file, link_callback=self._fetch_resources)
        return file_path

    @staticmethod
    def _fetch_resources(uri, rel):
        """
        Callback to allow xhtml2pdf/reportlab to retrieve Images,Stylesheets, etc.
        `uri` is the href attribute from the html link element.
        `rel` gives a relative path, but it's not used here.

        """
        if uri.startswith(settings.MEDIA_URL):
            path = os.path.join(settings.MEDIA_ROOT,
                                uri.replace(settings.MEDIA_URL, ""))
        elif uri.startswith(settings.STATIC_URL):
            path = os.path.join(settings.STATIC_ROOT,
                                uri.replace(settings.STATIC_URL, ""))
        elif uri.startswith('http'):
            return uri
        else:
            path = os.path.join(settings.STATIC_ROOT,
                                uri.replace(settings.STATIC_URL, ""))

            if not os.path.isfile(path):
                path = os.path.join(settings.MEDIA_ROOT,
                                    uri.replace(settings.MEDIA_URL, ""))
        return path


class KitPdfCreator(PdfCreatorMeta):
    HEADER_PATH = os.path.join(settings.BASE_DIR,'extra', 'kit-header.html')

    def __init__(self,
                 html=None,
                 template_name=None,
                 context_data={},
                 append_tnc=False,
                 has_header=True,
                 has_footer=True,
                 page_width=None,
                 page_height=None,
                 footer_center=None
                 ):
        html = render_to_string_from_source('''
                        {% extends 'pdf_template.html' %}
                        {% block content %}
                            {{ html|safe }}
                        {% endblock %}
                    ''', dict(html=html)) if html else None
        self.has_header = has_header
        self.has_footer = has_footer
        self.footer_center = footer_center
        self.page_width = page_width
        self.page_height = page_height
        super().__init__(html, template_name, context_data, append_tnc)

    def _get_options(self):
        options = {}
        if self.has_header:
            options.update({
                'header-html': self.HEADER_PATH,
                'header-spacing': 2,
                'margin-top': '32mm',
            })
        if self.has_footer:
            options.update({
                'footer-right': 'Page [page] of [toPage]',
                **({'footer-center': self.footer_center} if self.footer_center else {}),
                'footer-left': f'Generated: {formats.date_format(datetime.today(), "SHORT_DATE_FORMAT")}',
                'footer-font-name': 'Roboto',
                'footer-font-size': 10
            })
        if self.page_width:
            options['page-width'] = self.page_width
        if self.page_height:
            options.update({
                'page-height': self.page_height,
                'margin-top': '0mm',
                'margin-bottom': '0mm'
            })
        if not settings.DEBUG:
            options['quiet'] = ''
        else:
            options.update({
                'debug-javascript': ''
            })
        return options

    def _get_file_path_from_lib(self):
        html = self.html.replace(
            settings.MEDIA_URL, settings.MEDIA_ROOT).replace(
            settings.STATIC_URL, settings.STATIC_ROOT)
        file_path = get_temp_file_path('pdf')
        options = self._get_options()
        pdfkit.from_string(html, file_path,
                           options=options,
                           configuration=Configuration(wkhtmltopdf=settings.WKHTMLTOPDF_PATH))
        return file_path
