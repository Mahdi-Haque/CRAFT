from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Job Portal Info', {'fields': ('role', 'skills', 'bio', 'company_name')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Job Portal Info', {'fields': ('role', 'email')}),
    )
