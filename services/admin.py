from django.contrib import admin
from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'creator',
        'category',
        'price_estimate',
        'delivery_time_days',
        'is_active',
        'created_at',
    )
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('title', 'description', 'skills', 'creator__username')
    list_editable = ('is_active',)
