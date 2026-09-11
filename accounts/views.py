from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import RegisterForm, ProfileUpdateForm, StyledAuthenticationForm


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
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('accounts:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})
