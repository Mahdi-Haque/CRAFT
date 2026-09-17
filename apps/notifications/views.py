from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Notification


@login_required
def notification_list(request):
    """Display notifications for the authenticated user."""
    notifications = Notification.objects.filter(recipient=request.user)
    has_unread = notifications.filter(is_read=False).exists()
    context = {
        'notifications': notifications,
        'has_unread': has_unread,
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
@require_http_methods(['POST'])
def mark_notification_as_read(request, pk):
    """Mark a notification as read and redirect to its link if present."""
    notification = get_object_or_404(
        Notification, pk=pk, recipient=request.user
    )
    notification.is_read = True
    notification.save()

    if notification.link:
        return redirect(notification.link)
    return redirect('notifications:notification_list')


@login_required
@require_http_methods(['POST'])
def mark_all_notifications_as_read(request):
    """Mark all unread notifications as read for the authenticated user."""
    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return redirect('notifications:notification_list')
