from django.conf import settings
from django.db import models
from django.urls import reverse


class Project(models.Model):
    """
    Owned by Person B.
    Only touches accounts.User through settings.AUTH_USER_MODEL (a
    string reference agreed on up front) - never imports the accounts
    app's models.py directly.
    """
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CLOSED = 'closed', 'Closed'

    # Developer alias for CANCELLED
    Status.CANCELLED = Status.CLOSED

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='projects', limit_choices_to={'role': 'client'}
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    skills_required = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Required skills or technologies, comma-separated (e.g. Python, ROS, Figma)"
    )
    budget = models.DecimalField(max_digits=10, decimal_places=2, help_text="Budget in USD")
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.pk})

    @property
    def applicant_count(self):
        # 'applications' is the related_name Person C's Application model
        # points back at this model with - agreed contract, not a direct import.
        return self.applications.count()

    @property
    def skills_list(self):
        if not self.skills_required:
            return []
        return [s.strip() for s in self.skills_required.split(',') if s.strip()]

    @property
    def can_start(self):
        return self.status == self.Status.OPEN

    @property
    def can_complete(self):
        return self.status == self.Status.IN_PROGRESS

    @property
    def can_cancel(self):
        return self.status in (self.Status.OPEN, self.Status.IN_PROGRESS)

    @property
    def is_open(self):
        return self.status == self.Status.OPEN

