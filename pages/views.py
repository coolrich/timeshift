from django.shortcuts import render
# from django.http import HttpResponse
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = "home.html"


class AboutPageView(TemplateView):
    template_name = "about.html"

# def home_page_view(request):
#     return HttpResponse("Hello, World!")
