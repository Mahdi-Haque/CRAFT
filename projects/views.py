from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
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
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__icontains=query) |
            Q(skills_required__icontains=query)
        )

    selected_category = request.GET.get('category', '').strip()
    if selected_category:
        projects = projects.filter(category__iexact=selected_category)

    # Categories for filter dropdown: distinct non-empty categories from existing projects
    raw_categories = (
        Project.objects.exclude(category__isnull=True)
        .exclude(category='')
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    seen = set()
    categories = []
    for cat in raw_categories:
        cat_clean = cat.strip()
        if cat_clean and cat_clean.lower() not in seen:
            seen.add(cat_clean.lower())
            categories.append(cat_clean)

    # Person B never imports applications.models.Application - only reads the
    # 'applications' related_name that Person C's model contract promises.
    applied_ids = set()
    if request.user.is_student:
        applied_ids = set(
            Project.objects.filter(applications__student=request.user).values_list('id', flat=True)
        )

    # Pagination: 6 projects per page (fits 3-col desktop and 2-col tablet grids)
    paginator = Paginator(projects, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'projects/project_list.html', {
        'projects': page_obj,
        'page_obj': page_obj,
        'query': query,
        'selected_category': selected_category,
        'categories': categories,
        'applied_ids': applied_ids,
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
