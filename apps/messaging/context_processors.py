from django.db.models import Q

from .models import Message


def unread_message_count(request):
    """Expose only the authenticated user's received unread message count."""
    unread_count = 0
    if request.user.is_authenticated:
        unread_count = Message.objects.filter(
            Q(conversation__participant1=request.user)
            | Q(conversation__participant2=request.user),
            is_read=False,
        ).exclude(sender=request.user).count()
    return {'unread_message_count': unread_count}
