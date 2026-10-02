from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Review


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'department', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('role', 'department', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'student_id')
    fieldsets = UserAdmin.fieldsets + (
        ('CRAFT Profile Info', {
            'fields': (
                'role',
                'profile_picture',
                'department',
                'student_id',
                'skills',
                'bio',
                'company_name',
                'portfolio_url',
                'github_url',
                'linkedin_url',
                'website_url',
            )
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('CRAFT Profile Info', {'fields': ('role', 'email')}),
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'reviewer', 'reviewed_user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('reviewer__username', 'reviewed_user__username', 'project__title', 'comment')
    ordering = ('-created_at', '-id')
    readonly_fields = ('created_at', 'updated_at')
