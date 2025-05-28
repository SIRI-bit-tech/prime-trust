from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    """Sitemap for static pages"""
    priority = 0.5
    changefreq = 'weekly'

    def items(self):
        return ['home', 'accounts:login', 'accounts:register', 'pages:about', 
                'pages:features', 'pages:contact', 'pages:privacy', 'pages:terms']

    def location(self, item):
        return reverse(item)

# Dictionary of sitemaps
sitemaps = {
    'static': StaticViewSitemap,
}
