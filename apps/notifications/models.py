from django.conf import settings
from django.db import models


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        NEW_MESSAGE = 'new_message', 'New message'
        NEW_APPLICATION = 'new_application', 'New application'
        APPLICATION_ACCEPTED = 'application_accepted', 'Application accepted'
        APPLICATION_REJECTED = 'application_rejected', 'Application rejected'
        TEAM_ADDED = 'team_added', 'Added to team'
        PROJECT_STARTED = 'project_started', 'Project started'
        PROJECT_COMPLETED = 'project_completed', 'Project completed'
        PROJECT_CLOSED = 'project_closed', 'Project closed'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"
