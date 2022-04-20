from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from product.models import Product
from utilities.pdf import render_to_pdf, KitPdfCreator
from utilities.utils import get_bytes_and_delete, get_pdf_response_from_file
from custom_user.models import CustomUser
from quote.models import Quote, QuoteArea, QuoteLineItem

data = {
    "company": "Dennnis Ivanov Company",
    "address": "123 Street name",
    "city": "Vancouver",
    "state": "WA",
    "zipcode": "98663",

    "phone": "555-555-2345",
    "email": "youremail@dennisivy.com",
    "website": "dennisivy.com",
}


@login_required(redirect_field_name='next', login_url='login')
@csrf_exempt
def test_view(request):
    if request.method == 'POST':
        d = request.POST.copy()
        job_name = request.POST['job-name'] if request.POST['job-name'] else 'Random-Job'
        product_list = []
        area_list = []
        qty_list = []
        for x, y in d.items():
            if x not in ['csrfmiddlewaretoken', 'job-name']:
                if 'product' in str(x):
                    product_list.append(y)
                elif 'area' in str(x):
                    area_list.append(y)
                elif 'qty' in str(x):
                    qty_list.append(y)
        user = CustomUser.objects.first()
        quote = Quote.objects.create(job_name=job_name, created_by=user)
        quote.save()
        quote_inline_list = []
        for p, a, q in zip(product_list, area_list, qty_list):
            print(f'--------{p}')
            product = Product.objects.filter(id=p).first()
            area = QuoteArea.objects.filter(id=a).first()
            quote_inline = QuoteLineItem.objects.create(product=product, area=area, quote=quote, qty=q,
                                                        list_price=product.list_price)
            quote_inline.save()
            quote_inline_list.append(quote_inline)

        dc = dict()
        for item in quote_inline_list:
            print(item.area)
            if item.area in dc:
                dc[item.area].append(item)
            else:
                dc[item.area] = [item]

        all_area_summary = dict()
        all_area_summary_total = 0
        for quote_inline in quote_inline_list:
            if quote_inline.area in all_area_summary:
                all_area_summary[quote_inline.area] = all_area_summary[quote_inline.area] + (
                            int(quote_inline.list_price) * int(quote_inline.qty))
            else:
                all_area_summary[quote_inline.area] = int(quote_inline.list_price)

            all_area_summary_total += (int(quote_inline.list_price) * int(quote_inline.qty))
        pdf_creator = KitPdfCreator(template_name="pdf_template.html",
                                    context_data={'all_area_summary': all_area_summary,
                                                  'all_area_summary_total': all_area_summary_total,
                                                  'line_items': dc,
                                                  'quote': quote
                                                  })
        pdf_file = pdf_creator.get_file()
        download_name = "xyz"
        pdf = get_bytes_and_delete(pdf_file.name)
        return get_pdf_response_from_file(pdf, download_name)

    products = Product.objects.values('id', 'model_no')
    areas = QuoteArea.objects.values('id', 'area')
    return render(request, template_name='just.html', context={'products': products, 'areas': areas})
