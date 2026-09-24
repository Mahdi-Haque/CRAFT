from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import render, redirect, get_object_or_404

from .forms import RegisterForm, ProfileUpdateForm, StyledAuthenticationForm, ReviewForm
from .models import Review
from projects.models import Project
from applications.models import Application

User = get_user_model()


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your {user.role} account was created.")
            return redirect('accounts:dashboard')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    authentication_form = StyledAuthenticationForm


class CustomLogoutView(LogoutView):
    next_page = 'accounts:login'


@login_required
def dashboard_view(request):
    """
    Owned by Person A.
    This is the ONLY place that "knows about" the other two apps, and it
    only references their URL names (strings), never their models or
    views directly - so accounts/ never imports projects/ or applications/.
    Person B and Person C just need to make sure a URL with these names
    exists in their app: 'projects:client_dashboard',
    'applications:student_dashboard', 'applications:admin_dashboard'.
    """
    user = request.user
    if user.is_admin_role:
        return redirect('applications:admin_dashboard')
    if user.is_client:
        return redirect('projects:client_dashboard')
    return redirect('applications:student_dashboard')


@login_required
def profile_view(request):
    """
    View own profile. Also supports direct updates to preserve backwards
    compatibility with existing tests and forms.
    """
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile_user': request.user,
        'is_owner': True,
    })


@login_required
def profile_edit_view(request):
    """
    Dedicated profile edit view. Strictly bounds edits to request.user
    to enforce backend object authorization.
    """
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile_edit.html', {
        'form': form,
        'profile_user': request.user,
    })


@login_required
def public_profile_view(request, pk):
    """
    Public profile view for any community user.
    Read-only presentation with contextual links (Message, Services, Projects).
    """
    target_user = get_object_or_404(User, pk=pk)
    is_owner = (request.user.pk == target_user.pk)

    services = []
    if target_user.is_student and hasattr(target_user, 'services'):
        services = target_user.services.filter(is_active=True)

    projects = []
    if target_user.is_client and hasattr(target_user, 'projects'):
        projects = target_user.projects.exclude(status='closed')

    reviews = target_user.reviews_received.select_related('reviewer', 'project').order_by('-created_at', '-id')

    return render(request, 'accounts/public_profile.html', {
        'profile_user': target_user,
        'is_owner': is_owner,
        'services': services,
        'projects': projects,
        'reviews': reviews,
    })


@login_required
def submit_review_view(request, project_pk, user_pk=None):
    """
    Allows eligible participants of a completed project to review each other:
    - Client reviews an accepted student.
    - Accepted student reviews the project client.
    Enforces strict server-side validation against self-reviews, incomplete projects,
    non-participants, student-student reviews, and duplicate reviews.
    """
    project = get_object_or_404(Project.objects.select_related('client'), pk=project_pk)

    # 1. Project status check: reviews can only be submitted for completed projects
    if project.status != Project.Status.COMPLETED:
        messages.error(request, f"Reviews can only be submitted for completed projects (current status: {project.get_status_display()}).")
        return redirect('projects:project_detail', pk=project.pk)

    # 2. Determine reviewed_user if user_pk was not provided in the URL
    if user_pk is None:
        if request.user.is_student:
            reviewed_user = project.client
        elif project.client_id == request.user.id:
            accepted_students = User.objects.filter(
                applications__project=project,
                applications__status=Application.Status.ACCEPTED
            ).distinct()
            if accepted_students.count() == 1:
                reviewed_user = accepted_students.first()
            elif accepted_students.exists():
                return redirect('projects:project_workspace', pk=project.pk)
            else:
                messages.error(request, "No accepted students found on this project to review.")
                return redirect('projects:project_detail', pk=project.pk)
        else:
            messages.error(request, "Only project participants can submit reviews.")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        reviewed_user = get_object_or_404(User, pk=user_pk)

    # 3. Prevent self-review
    if request.user.pk == reviewed_user.pk:
        messages.error(request, "You cannot review yourself.")
        return redirect('projects:project_detail', pk=project.pk)

    # 4. Check reviewer and reviewed_user eligibility
    is_client = (project.client_id == request.user.id)
    is_student_accepted = (
        project.applications.filter(student=request.user, status=Application.Status.ACCEPTED).exists() or
        (hasattr(project, 'team') and project.team.members.filter(id=request.user.id).exists())
    )

    if not is_client and not is_student_accepted:
        messages.error(request, "You must be an accepted participant on this project to submit a review.")
        return redirect('projects:project_detail', pk=project.pk)

    if is_client:
        target_is_accepted_student = (
            project.applications.filter(student=reviewed_user, status=Application.Status.ACCEPTED).exists() or
            (hasattr(project, 'team') and project.team.members.filter(id=reviewed_user.id).exists())
        )
        if not target_is_accepted_student:
            messages.error(request, f"{reviewed_user.display_name} was not an accepted student on this project.")
            return redirect('projects:project_detail', pk=project.pk)
    else:
        if reviewed_user.pk != project.client_id:
            messages.error(request, "Student participants can only review the project client.")
            return redirect('projects:project_detail', pk=project.pk)

    # 5. Prevent duplicate reviews
    existing_review = Review.objects.filter(
        project=project,
        reviewer=request.user,
        reviewed_user=reviewed_user
    ).first()
    if existing_review:
        messages.info(request, f"You have already reviewed {reviewed_user.display_name} for this project.")
        return redirect('accounts:public_profile', pk=reviewed_user.pk)

    # 6. Form handling
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.project = project
            review.reviewer = request.user
            review.reviewed_user = reviewed_user
            try:
                review.full_clean()
                review.save()
                messages.success(request, f"Your review for {reviewed_user.display_name} has been published successfully.")
                return redirect('accounts:public_profile', pk=reviewed_user.pk)
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = ReviewForm()

    return render(request, 'accounts/submit_review.html', {
        'form': form,
        'project': project,
        'reviewed_user': reviewed_user,
    })
