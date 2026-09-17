from django.contrib.auth import get_user_model

from .models import Notification

User = get_user_model()


def create_notification(recipient, notification_type, title, message, link=''):
    """
    Create and return a notification.

    Args:
        recipient: User instance who receives the notification
        notification_type: One of Notification.NotificationType choices
        title: Short heading (max 200 chars)
        message: Notification body text
        link: Optional destination URL (max 500 chars)

    Returns:
        Notification instance
    """
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )
