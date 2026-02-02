from django.contrib import admin
from .models import SiteSettings, Service, Incident, IncidentUpdate


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('company_name',)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'order')
    list_editable = ('status', 'order')
    list_filter = ('status',)
    search_fields = ('name', 'description')


class IncidentUpdateInline(admin.TabularInline):
    model = IncidentUpdate
    extra = 1
    ordering = ('-created_at',)


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'impact', 'created_at', 'resolved_at')
    list_filter = ('status', 'impact')
    search_fields = ('title',)
    filter_horizontal = ('services',)
    inlines = [IncidentUpdateInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('title', 'status', 'impact', 'services')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
