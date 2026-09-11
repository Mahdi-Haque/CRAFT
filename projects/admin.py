from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'status', 'budget', 'deadline', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('title', 'description', 'client__username')
