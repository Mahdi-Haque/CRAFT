from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404

from .forms import RegisterForm, ProfileUpdateForm, StyledAuthenticationForm

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

    return render(request, 'accounts/public_profile.html', {
        'profile_user': target_user,
        'is_owner': is_owner,
        'services': services,
        'projects': projects,
    })
