import os

from django.shortcuts import render
# from django.http import HttpResponse
from django.views.generic import TemplateView
from dotenv import load_dotenv

load_dotenv()


class HomePageView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["site_name"] = os.getenv("SITE_NAME")
        return context


class AboutPageView(TemplateView):
    template_name = "about.html"
