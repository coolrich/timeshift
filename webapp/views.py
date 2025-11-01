from django.views.generic import TemplateView
from dotenv import load_dotenv

load_dotenv()


class IndexView(TemplateView):
    template_name = "webapp/index.html"


class DocsPageView(TemplateView):
    template_name = "webapp/docs.html"


class ContactsPageView(TemplateView):
    template_name = "webapp/contacts.html"
