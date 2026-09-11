from django.conf import settings
from django.db import models
from django.urls import reverse


class Service(models.Model):
    """
    Owned by Contributor 1.
    Represents a specific skill offering or freelance service provided by a
    student or campus community member.

    Only references accounts.User via settings.AUTH_USER_MODEL.
    Maintains zero code coupling with projects or applications.
    """
    class Category(models.TextChoices):
        WEB_DEV = 'Web Development', 'Web Development'
        PROGRAMMING = 'Programming', 'Programming & Software'
        APP_DEV = 'App Development', 'App Development'
        GRAPHIC_DESIGN = 'Graphic Design', 'Graphic Design'
        UI_UX = 'UI/UX Design', 'UI/UX Design'
        EMBEDDED = 'Embedded Systems', 'Embedded Systems & IoT'
        ELECTRONICS = 'Electronics', 'Electronics & Hardware'
        CAD_ENGINEERING = 'CAD & Engineering', 'CAD & Engineering Modeling'
        WRITING = 'Writing', 'Technical Writing & Documentation'
        VIDEO_EDITING = 'Video Editing', 'Video Editing & Media'
        PHOTOGRAPHY = 'Photography', 'Campus Photography'
        TUTORING = 'Tutoring', 'Academic Tutoring'
        RESEARCH = 'Research', 'Research Assistance'
        OTHER = 'Other', 'Other Services'

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='services'
    )
    title = models.CharField(
        max_length=200,
        help_text="e.g. I will design professional event posters for your RUET club"
    )
    description = models.TextField(
        help_text="Describe the scope, deliverables, and what clients should expect."
    )
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.WEB_DEV
    )
    skills = models.CharField(
        max_length=255,
        blank=True,
        help_text="Relevant tools or technologies, comma-separated (e.g. React, Tailwind, Figma)"
    )
    delivery_time_days = models.PositiveIntegerField(
        default=3,
        help_text="Expected delivery time in days"
    )
    price_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional starting price or estimated budget in USD"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Toggle service availability in the marketplace"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.creator.username}"

    def get_absolute_url(self):
        return reverse('services:service_detail', kwargs={'pk': self.pk})

    @property
    def skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]
