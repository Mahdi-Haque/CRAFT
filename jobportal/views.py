from django.shortcuts import render, redirect
from projects.models import Project


def home_view(request):
    """
    Public landing page for guests.
    Redirects authenticated users to their role-appropriate dashboard.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    recent_projects = Project.objects.filter(status='open').order_by('-created_at')[:3]
    return render(request, 'home.html', {
        'recent_projects': recent_projects
    })
