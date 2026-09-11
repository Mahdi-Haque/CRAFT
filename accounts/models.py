from django.contrib.auth.models import AbstractUser
from django.db import models


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

    # Student-specific
    skills = models.CharField(max_length=255, blank=True, help_text="Comma separated skills")
    bio = models.TextField(blank=True)

    # Client-specific
    company_name = models.CharField(max_length=150, blank=True)

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
