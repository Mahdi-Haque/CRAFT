from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.shortcuts import render, redirect, get_object_or_404

from .forms import ProjectForm
from .models import Project, ProjectTeam, ProjectMembership

SORT_OPTIONS = [
    ('newest', 'Newest first'),
    ('oldest', 'Oldest first'),
    ('budget_high', 'Budget: High to Low'),
    ('budget_low', 'Budget: Low to High'),
    ('deadline', 'Deadline: Nearest first'),
]

SORT_ORDERING = {
    'newest': ('-created_at',),
    'oldest': ('created_at',),
    'budget_high': ('-budget', '-created_at'),
    'budget_low': ('budget', '-created_at'),
    'deadline': (F('deadline').asc(nulls_last=True), '-created_at'),
}



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

    # Sorting
    raw_sort = request.GET.get('sort', '').strip().lower()
    if raw_sort in SORT_ORDERING:
        selected_sort = raw_sort
        sort_query = raw_sort
    else:
        selected_sort = 'newest'
        sort_query = ''

    projects = projects.order_by(*SORT_ORDERING[selected_sort])

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
        'selected_sort': selected_sort,
        'sort': selected_sort,
        'sort_query': sort_query,
        'sort_options': SORT_OPTIONS,
        'applied_ids': applied_ids,
    })


@login_required
def project_detail(request, pk):
    """
    Owned by Person B. Shows project info and handles CTA state.
    Queries user's application status via related_name contract if student.
    """
    project = get_object_or_404(Project, pk=pk)
    is_owner = request.user.is_authenticated and project.client_id == request.user.id
    user_application = None
    if request.user.is_authenticated and request.user.is_student and not is_owner:
        user_application = project.applications.filter(student=request.user).first()

    return render(request, 'projects/project_detail.html', {
        'project': project,
        'is_owner': is_owner,
        'user_application': user_application,
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
    projects = (
        Project.objects.filter(client=request.user)
        .annotate(app_count=Count('applications'))
        .prefetch_related('team__members')
        .order_by('-created_at')
    )
    total_applicants = sum(p.app_count for p in projects)
    return render(request, 'projects/client_dashboard.html', {
        'projects': projects,
        'open_count': projects.filter(status='open').count(),
        'in_progress_count': projects.filter(status='in_progress').count(),
        'completed_count': projects.filter(status='completed').count(),
        'closed_count': projects.filter(status='closed').count(),
        'total_applicants': total_applicants,
    })


@login_required
def project_start(request, pk):
    if request.method != 'POST':
        raise PermissionDenied("Invalid request method.")
    project = get_object_or_404(Project, pk=pk)
    if project.client_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only manage lifecycle for your own projects.")
    if project.status != Project.Status.OPEN:
        messages.error(request, f"Cannot start project in '{project.get_status_display()}' state. Only open projects can be started.")
        return redirect('projects:project_detail', pk=project.pk)
    project.status = Project.Status.IN_PROGRESS
    project.save()
    messages.success(request, "Project has been moved to In Progress.")
    return redirect('projects:project_detail', pk=project.pk)


@login_required
def project_complete(request, pk):
    if request.method != 'POST':
        raise PermissionDenied("Invalid request method.")
    project = get_object_or_404(Project, pk=pk)
    if project.client_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only manage lifecycle for your own projects.")
    if project.status != Project.Status.IN_PROGRESS:
        messages.error(request, f"Cannot complete project in '{project.get_status_display()}' state. Only in-progress projects can be completed.")
        return redirect('projects:project_detail', pk=project.pk)
    project.status = Project.Status.COMPLETED
    project.save()
    messages.success(request, "Project has been marked as Completed.")
    return redirect('projects:project_detail', pk=project.pk)


@login_required
def project_cancel(request, pk):
    if request.method != 'POST':
        raise PermissionDenied("Invalid request method.")
    project = get_object_or_404(Project, pk=pk)
    if project.client_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only manage lifecycle for your own projects.")
    if project.status in (Project.Status.COMPLETED, Project.Status.CLOSED):
        messages.error(request, f"Project is already {project.get_status_display().lower()} and cannot be closed.")
        return redirect('projects:project_detail', pk=project.pk)
    project.status = Project.Status.CLOSED
    project.save()
    messages.success(request, "Project has been closed.")
    return redirect('projects:project_detail', pk=project.pk)


@login_required
def project_workspace(request, pk):
    project = get_object_or_404(Project, pk=pk)

    # Object-level authorization: owner, admin, or accepted student team member
    is_owner = (project.client_id == request.user.id) or request.user.is_admin_role
    is_team_member = False

    if hasattr(project, 'team') and project.team.members.filter(id=request.user.id).exists():
        is_team_member = True
    elif project.applications.filter(student=request.user, status='accepted').exists():
        is_team_member = True
        team, _ = ProjectTeam.objects.get_or_create(project=project)
        ProjectMembership.objects.get_or_create(team=team, user=request.user)

    if not (is_owner or is_team_member):
        raise PermissionDenied("You must be an active project team participant to access this workspace.")

    team, _ = ProjectTeam.objects.get_or_create(project=project)
    team_members = team.members.all()

    return render(request, 'projects/workspace.html', {
        'project': project,
        'team': team,
        'team_members': team_members,
        'is_owner': is_owner,
    })


