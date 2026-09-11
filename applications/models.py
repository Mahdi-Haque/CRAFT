from django.conf import settings
from django.db import models


class Application(models.Model):
    """
    Owned by Person C.
    Depends on Person B's Project model (imported directly, since an
    Application cannot exist without knowing which project it targets)
    and on accounts.User via settings.AUTH_USER_MODEL. The 'applications'
    related_name here is the contract Person B's dashboard/detail code
    relies on - keep it stable.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'

    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, related_name='applications'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='applications', limit_choices_to={'role': 'student'}
    )
    cover_letter = models.TextField(help_text="Why are you a good fit for this project?")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-applied_at']
        unique_together = ('project', 'student')

    def __str__(self):
        return f"{self.student.username} -> {self.project.title}"
