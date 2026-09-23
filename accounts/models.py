from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Avg, F, Q


class User(AbstractUser):
    """
    Owned by Person A.
    Custom user with a role field. This is the one model every other
    app depends on (via settings.AUTH_USER_MODEL) - the 'role' choices
    and the is_student/is_client/is_admin_role helpers are the contract
    other apps are written against.
    """
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        CLIENT = 'client', 'Client'
        ADMIN = 'admin', 'Admin'

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)

    # Profile picture
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    # Student-specific and Academic
    department = models.CharField(max_length=100, blank=True, help_text="Academic department or discipline")
    student_id = models.CharField(max_length=20, blank=True, help_text="e.g. 1903123")
    skills = models.CharField(max_length=255, blank=True, help_text="Comma separated skills")
    bio = models.TextField(blank=True)
    portfolio_url = models.URLField(blank=True, help_text="Personal portfolio or website URL")
    github_url = models.URLField(blank=True, help_text="GitHub profile URL")
    linkedin_url = models.URLField(blank=True, help_text="LinkedIn profile URL")

    # Client-specific
    company_name = models.CharField(max_length=150, blank=True)
    website_url = models.URLField(blank=True, help_text="Organization website URL")

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def display_name(self):
        full = self.get_full_name().strip()
        return full if full else self.username

    @property
    def skills_list(self):
        if not self.skills:
            return []
        return [s.strip() for s in self.skills.split(',') if s.strip()]

    @property
    def average_rating(self):
        result = self.reviews_received.aggregate(avg=Avg('rating'))['avg']
        if result is not None:
            return round(result, 1)
        return None

    @property
    def review_count(self):
        return self.reviews_received.count()


class Review(models.Model):
    """
    Represents a feedback review and star rating submitted for project collaboration.
    Strictly between project client and participating student(s).
    """
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="The completed project this review is associated with."
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_given',
        help_text="User submitting the review."
    )
    reviewed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_received',
        help_text="User receiving the review."
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating score from 1 to 5 stars."
    )
    comment = models.TextField(
        help_text="Review feedback and remarks."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'reviewer', 'reviewed_user'],
                name='unique_project_review_pair'
            ),
            models.CheckConstraint(
                condition=~Q(reviewer=F('reviewed_user')),
                name='prevent_self_review'
            ),
        ]

    def __str__(self):
        return f"Review by {self.reviewer.username} for {self.reviewed_user.username} ({self.rating}★)"

    def clean(self):
        super().clean()
        if self.reviewer_id and self.reviewed_user_id and self.reviewer_id == self.reviewed_user_id:
            raise ValidationError({'reviewed_user': "A user cannot review themselves."})
        if self.rating is not None and (self.rating < 1 or self.rating > 5):
            raise ValidationError({'rating': "Rating must be between 1 and 5 stars."})
        if not self.comment or not self.comment.strip():
            raise ValidationError({'comment': "Review comment cannot be blank."})
