"""
Django admin configuration for the FAIR Data Center application.
Registers models with customized admin interfaces for managing metadata.
"""

from django.contrib import admin
from .models import (
    ComputeNode,
    SensorType,
    ObservableProperty,
    Sensor,
    MonitoringDataset,
    DataFile,
    DataCollectionActivity,
    Agent
)


@admin.register(ComputeNode)
class ComputeNodeAdmin(admin.ModelAdmin):
    """Admin interface for compute nodes."""
    list_display = ('hostname', 'location', 'description')
    list_filter = ('location',)
    search_fields = ('hostname', 'location', 'description')
    ordering = ('hostname',)


@admin.register(SensorType)
class SensorTypeAdmin(admin.ModelAdmin):
    """Admin interface for sensor types."""
    list_display = ('name', 'description')
    list_filter = ('name',)
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(ObservableProperty)
class ObservablePropertyAdmin(admin.ModelAdmin):
    """Admin interface for observable properties."""
    list_display = ('property_name', 'label', 'unit', 'sensor_type')
    list_filter = ('sensor_type', 'data_type')
    search_fields = ('property_name', 'label', 'description')
    ordering = ('property_name',)


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    """Admin interface for sensors."""
    list_display = ('sensor_id', 'sensor_type', 'compute_node', 'device_name')
    list_filter = ('sensor_type', 'compute_node')
    search_fields = ('sensor_id', 'description', 'device_name', 'interface_name')
    ordering = ('sensor_id',)


class DataFileInline(admin.TabularInline):
    """Inline display of data files within dataset admin."""
    model = DataFile
    extra = 0
    fields = ('filename', 'file_format', 'sensor_type', 'file_size', 'row_count')
    readonly_fields = ('file_size', 'row_count')


@admin.register(MonitoringDataset)
class MonitoringDatasetAdmin(admin.ModelAdmin):
    """Admin interface for monitoring datasets."""
    list_display = ('title', 'dataset_id', 'start_date', 'end_date', 'issued', 'modified')
    search_fields = ('title', 'description', 'dataset_id', 'keywords')
    list_filter = ('issued', 'modified')
    ordering = ('-modified',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('dataset_id', 'title', 'description', 'keywords')
        }),
        ('Temporal Coverage', {
            'fields': ('start_date', 'end_date')
        }),
        ('Publication', {
            'fields': ('issued', 'modified', 'version')
        }),
        ('Creator Information', {
            'fields': ('creator_name', 'creator_email')
        }),
        ('Publisher & License', {
            'fields': ('publisher_name', 'publisher_url', 'license_name', 'license_url')
        }),
    )
    
    inlines = [DataFileInline]


@admin.register(DataFile)
class DataFileAdmin(admin.ModelAdmin):
    """Admin interface for data files."""
    list_display = ('filename', 'file_format', 'sensor_type', 'dataset', 'file_size', 'row_count')
    list_filter = ('file_format', 'media_type', 'sensor_type', 'dataset')
    search_fields = ('filename', 'description', 'file_path')
    ordering = ('filename',)


class ActivityAgentInline(admin.TabularInline):
    """Inline display of agents within activity admin."""
    model = DataCollectionActivity.agents.through
    extra = 1
    verbose_name = "Agent"
    verbose_name_plural = "Agents involved in this activity"


@admin.register(DataCollectionActivity)
class DataCollectionActivityAdmin(admin.ModelAdmin):
    """Admin interface for data collection activities."""
    list_display = ('activity_id', 'activity_type', 'dataset', 'start_time', 'end_time')
    list_filter = ('activity_type', 'dataset', 'start_time')
    search_fields = ('activity_id', 'description')
    ordering = ('-start_time',)
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('activity_id', 'activity_type', 'description')
        }),
        ('Association', {
            'fields': ('dataset',)
        }),
        ('Temporal Information', {
            'fields': ('start_time', 'end_time')
        }),
    )
    
    inlines = [ActivityAgentInline]


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    """Admin interface for agents."""
    list_display = ('name', 'agent_type', 'version', 'agent_id')
    list_filter = ('agent_type',)
    search_fields = ('name', 'agent_id', 'description')
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('agent_id', 'name', 'agent_type')
        }),
        ('Details', {
            'fields': ('description', 'version', 'url')
        }),
    )
