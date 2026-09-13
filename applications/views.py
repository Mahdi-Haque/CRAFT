from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404

from .forms import ApplicationForm
from .models import Application
from projects.models import Project

User = get_user_model()


def student_required(user):
    return user.is_authenticated and (user.is_student or user.is_admin_role)


@login_required
def apply_to_project(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not student_required(request.user):
        raise PermissionDenied("Only students can apply to projects.")
    if project.client_id == request.user.id:
        raise PermissionDenied("You cannot apply to your own project.")
    if project.status != Project.Status.OPEN:
        messages.error(request, "This project is no longer accepting applications.")
        return redirect('projects:project_detail', pk=project.pk)
    if Application.objects.filter(project=project, student=request.user).exists():
        messages.info(request, "You have already applied to this project.")
        return redirect('projects:project_detail', pk=project.pk)

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.project = project
            application.student = request.user
            application.status = Application.Status.PENDING
            application.save()
            messages.success(request, "Application submitted!")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ApplicationForm()
    return render(request, 'applications/application_form.html', {'form': form, 'project': project})


@login_required
def withdraw_application(request, pk):
    application = get_object_or_404(Application, pk=pk, student=request.user)
    if request.method == 'POST':
        application.delete()
        messages.success(request, "Application withdrawn.")
    return redirect('applications:student_dashboard')


@login_required
def applicants_list(request, pk):
    """
    Owned by Person C. This is its own page (not embedded in Person B's
    project detail template) - linked to from there by URL name only.
    """
    project = get_object_or_404(Project, pk=pk)
    if project.client_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only manage applicants for your own projects.")
    applicants = project.applications.select_related('student').all()
    return render(request, 'applications/applicants_list.html', {
        'project': project, 'applicants': applicants,
    })


@login_required
def update_application_status(request, pk, new_status):
    if request.method != 'POST':
        raise PermissionDenied("Invalid request method.")
    application = get_object_or_404(Application, pk=pk)
    if application.project.client_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only manage applicants for your own projects.")
    if application.status != Application.Status.PENDING:
        messages.warning(request, "This application has already been decided.")
        return redirect('applications:applicants_list', pk=application.project_id)
    if new_status not in (Application.Status.ACCEPTED, Application.Status.REJECTED):
        raise PermissionDenied("Invalid status transition.")
    application.status = new_status
    application.save()
    messages.success(request, f"Application marked as {new_status}.")
    return redirect('applications:applicants_list', pk=application.project_id)


@login_required
def accept_application(request, pk):
    return update_application_status(request, pk, Application.Status.ACCEPTED)


@login_required
def reject_application(request, pk):
    return update_application_status(request, pk, Application.Status.REJECTED)



@login_required
def student_dashboard(request):
    if not student_required(request.user):
        raise PermissionDenied("Only students can view this dashboard.")
    applications = Application.objects.filter(student=request.user).select_related('project').order_by('-applied_at')
    open_projects = Project.objects.filter(status='open').order_by('-created_at')[:6]
    return render(request, 'applications/student_dashboard.html', {
        'applications': applications,
        'open_projects': open_projects,
        'pending_count': applications.filter(status='pending').count(),
        'accepted_count': applications.filter(status='accepted').count(),
    })


@login_required
def admin_dashboard(request):
    if not request.user.is_admin_role:
        raise PermissionDenied("Only admins can view this dashboard.")
    return render(request, 'applications/admin_dashboard.html', {
        'total_students': User.objects.filter(role='student').count(),
        'total_clients': User.objects.filter(role='client').count(),
        'total_projects': Project.objects.count(),
        'total_applications': Application.objects.count(),
        'recent_projects': Project.objects.order_by('-created_at')[:10],
    })
