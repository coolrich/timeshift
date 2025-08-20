from django.views.generic import TemplateView
from dotenv import load_dotenv

load_dotenv()


class IndexView(TemplateView):
    template_name = "webapp/index.html"

    # def get_context_data(self, **kwargs):
    #     context = super().get_context_data(**kwargs)
    #     context["site_name"] = os.getenv("SITE_NAME")
    #     return context


class DocsPageView(TemplateView):
    template_name = "webapp/docs.html"


class ContactsPageView(TemplateView):
    template_name = "webapp/contacts.html"
