from io import BytesIO

from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


def render_to_pdf(template_src, context_data):
    if isinstance(context_data, list):
        context_dict = {"data": context_data}
    elif isinstance(context_data, dict):
        context_dict = context_data
    else:
        raise TypeError("context must be a dict or list.")

    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type="application/pdf")
    return None
