from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django_htmx.http import HttpResponseClientRedirect
import requests
from django.conf import settings

def about(request):
    """View for the About page"""
    return render(request, 'pages/about.html')

def features(request):
    """View for the Features page"""
    return render(request, 'pages/features.html')

def privacy(request):
    """View for the Privacy Policy page"""
    return render(request, 'pages/privacy.html')

def terms(request):
    """View for the Terms of Service page"""
    return render(request, 'pages/terms.html')

@require_http_methods(["GET", "POST"])
def contact(request):
    """View for the Contact page"""
    if request.method == 'POST' and request.htmx:
        # Process the contact form submission
        # In a real application, you would send an email or store the message
        return HttpResponse(
            '<div id="form-response" class="rounded-md bg-green-50 p-4">' +
            '<div class="flex">' +
            '<div class="flex-shrink-0">' +
            '<svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">' +
            '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />' +
            '</svg>' +
            '</div>' +
            '<div class="ml-3">' +
            '<h3 class="text-sm font-medium text-green-800">Message Sent!</h3>' +
            '<div class="mt-2 text-sm text-green-700">' +
            '<p>Thank you for contacting us. We will get back to you as soon as possible.</p>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div>'
        )
    return render(request, 'pages/contact.html')

def news(request):
    """View for the News page fetching real-time headlines from Gnews.io."""
    api_key = settings.NEWS_API_KEY
    url = 'https://gnews.io/api/v4/top-headlines'
    # Include country for valid headlines
    params = {'token': api_key, 'lang': 'en', 'country': 'us', 'max': 10}
    error = None
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if response.status_code == 200:
            articles = data.get('articles', [])
        else:
            articles = []
            error = data.get('message', 'Error fetching news')
    except Exception as ex:
        articles = []
        error = str(ex)
    return render(request, 'pages/news.html', {'articles': articles, 'error': error})
