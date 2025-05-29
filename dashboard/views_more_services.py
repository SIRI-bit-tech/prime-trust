from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

@login_required
def more_services(request):
    """
    View for the More Services page
    """
    context = {
        'title': 'More Services',
    }
    
    if request.htmx:
        template_name = 'dashboard/partials/more_services_content.html'
    else:
        template_name = 'dashboard/more_services.html'
    
    return render(request, template_name, context)
