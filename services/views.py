from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import ServiceForm
from .models import Service


def service_list(request):
    """
    Public marketplace for browsing campus services.
    Supports keyword search, category filtering, and personal service view.
    """
    queryset = Service.objects.select_related('creator').all()

    # Filter by user's own services if requested and logged in
    show_mine = request.GET.get('mine') == '1' and request.user.is_authenticated
    if show_mine:
        queryset = queryset.filter(creator=request.user)
    else:
        # Default: show active services (or all if admin)
        if not (request.user.is_authenticated and request.user.is_admin_role):
            queryset = queryset.filter(is_active=True)

    # Search keyword filter
    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(skills__icontains=query) |
            Q(creator__username__icontains=query)
        )

    # Category filter
    selected_category = request.GET.get('category', '').strip()
    if selected_category:
        queryset = queryset.filter(category=selected_category)

    # Ordering
    queryset = queryset.order_by('-created_at')

    # Pagination: 9 services per page
    paginator = Paginator(queryset, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'services/service_list.html', {
        'services': page_obj,
        'page_obj': page_obj,
        'query': query,
        'selected_category': selected_category,
        'categories': Service.Category.choices,
        'show_mine': show_mine,
        'total_count': queryset.count(),
    })


def service_detail(request, pk):
    """
    Detailed showcase of a student service with creator information and contact details.
    """
    service = get_object_or_404(Service.objects.select_related('creator'), pk=pk)
    
    is_owner = request.user.is_authenticated and (
        service.creator_id == request.user.id or request.user.is_admin_role
    )

    # Inactive services only viewable by creator or admin
    if not service.is_active and not is_owner:
        messages.warning(request, "This service is currently paused or inactive.")
        return redirect('services:service_list')

    return render(request, 'services/service_detail.html', {
        'service': service,
        'is_owner': is_owner,
    })


@login_required
def service_create(request):
    """
    Allows authenticated campus users to publish a new service.
    """
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.creator = request.user
            service.save()
            messages.success(request, f"Service '{service.title}' created and published successfully!")
            return redirect('services:service_detail', pk=service.pk)
    else:
        form = ServiceForm()

    return render(request, 'services/service_form.html', {
        'form': form,
        'title': 'Offer a New Campus Service',
        'is_edit': False,
    })


@login_required
def service_update(request, pk):
    """
    Allows service creators to update their offering.
    Server-side authorization ensures only the owner or an admin can edit.
    """
    service = get_object_or_404(Service, pk=pk)
    if service.creator_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only edit services that you created.")

    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service details updated successfully.")
            return redirect('services:service_detail', pk=service.pk)
    else:
        form = ServiceForm(instance=service)

    return render(request, 'services/service_form.html', {
        'form': form,
        'service': service,
        'title': f"Edit: {service.title}",
        'is_edit': True,
    })


@login_required
def service_delete(request, pk):
    """
    Allows service creators to remove their offering.
    Server-side authorization ensures only the owner or an admin can delete.
    """
    service = get_object_or_404(Service, pk=pk)
    if service.creator_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only delete services that you created.")

    if request.method == 'POST':
        service_title = service.title
        service.delete()
        messages.success(request, f"Service '{service_title}' was successfully deleted.")
        return redirect('services:service_list')

    return render(request, 'services/service_confirm_delete.html', {
        'service': service,
    })


@login_required
@require_POST
def service_toggle_active(request, pk):
    """
    Quickly toggle service availability between Active and Paused.
    """
    service = get_object_or_404(Service, pk=pk)
    if service.creator_id != request.user.id and not request.user.is_admin_role:
        raise PermissionDenied("You can only update availability for your own services.")

    service.is_active = not service.is_active
    service.save(update_fields=['is_active', 'updated_at'])

    status_str = "active and available" if service.is_active else "paused"
    messages.info(request, f"Service is now {status_str}.")
    return redirect('services:service_detail', pk=service.pk)
