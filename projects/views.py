from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404

from .forms import ProjectForm
from .models import Project


def client_required(user):
    return user.is_authenticated and (user.is_client or user.is_admin_role)


@login_required
def project_list(request):
    projects = Project.objects.filter(status='open')

    query = request.GET.get('q', '').strip()
    if query:
        projects = projects.filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(category__icontains=query)
        )

    # Person B never imports applications.models.Application - only reads the
    # 'applications' related_name that Person C's model contract promises.
    applied_ids = set()
    if request.user.is_student:
        applied_ids = set(
            Project.objects.filter(applications__student=request.user).values_list('id', flat=True)
        )

    return render(request, 'projects/project_list.html', {
        'projects': projects, 'query': query, 'applied_ids': applied_ids,
    })


@login_required
def project_detail(request, pk):
    """
    Owned by Person B. Shows project info only. Application status,
    the Apply button target, and the applicant list all live on pages
    owned by Person C ('applications' app) and are linked to by URL
    name only - this view never touches the Application model.
    """
    project = get_object_or_404(Project, pk=pk)
    is_owner = request.user.is_authenticated and project.client_id == request.user.id
    return render(request, 'projects/project_detail.html', {
        'project': project, 'is_owner': is_owner,
    })


@login_required
def project_create(request):
    if not client_required(request.user):
        raise PermissionDenied("Only clients can post projects.")
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.client = request.user
            project.save()
            messages.success(request, "Project posted successfully.")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Post a New Project'})


@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project.client_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only edit your own projects.")
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated successfully.")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Edit Project'})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project.client_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only delete your own projects.")
    if request.method == 'POST':
        project.delete()
        messages.success(request, "Project deleted.")
        return redirect('accounts:dashboard')
    return render(request, 'projects/project_confirm_delete.html', {'project': project})


@login_required
def client_dashboard(request):
    if not client_required(request.user):
        raise PermissionDenied("Only clients can view this dashboard.")
    projects = Project.objects.filter(client=request.user).annotate(
        app_count=Count('applications')
    ).order_by('-created_at')
    total_applicants = sum(p.app_count for p in projects)
    return render(request, 'projects/client_dashboard.html', {
        'projects': projects,
        'open_count': projects.filter(status='open').count(),
        'closed_count': projects.filter(status='closed').count(),
        'total_applicants': total_applicants,
    })
