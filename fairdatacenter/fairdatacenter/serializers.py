"""
REST API serializers for fairdatacenter
"""
from rest_framework import serializers
from .models import (
    ComputeNode, SensorType, ObservableProperty, Sensor,
    MonitoringDataset, DataFile, DataCollectionActivity, Agent
)


class ComputeNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComputeNode
        fields = ['id', 'hostname', 'description', 'location']


class SensorTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorType
        fields = ['id', 'name', 'description', 'sosa_uri']


class ObservablePropertySerializer(serializers.ModelSerializer):
    sensor_type_name = serializers.CharField(source='sensor_type.name', read_only=True)
    
    class Meta:
        model = ObservableProperty
        fields = ['id', 'property_name', 'label', 'description', 'unit', 
                  'qudt_unit_uri', 'data_type', 'sensor_type', 'sensor_type_name']


class SensorSerializer(serializers.ModelSerializer):
    sensor_type_name = serializers.CharField(source='sensor_type.name', read_only=True)
    hostname = serializers.CharField(source='compute_node.hostname', read_only=True)
    
    class Meta:
        model = Sensor
        fields = ['id', 'sensor_id', 'sensor_type', 'sensor_type_name',
                  'compute_node', 'hostname', 'device_name', 'interface_name', 'description']


class DataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataFile
        fields = ['id', 'filename', 'file_format', 'media_type', 'file_path',
                  'file_size', 'row_count', 'description']


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ['id', 'agent_id', 'name', 'agent_type', 'version', 'description', 'homepage']


class DataCollectionActivitySerializer(serializers.ModelSerializer):
    agents = AgentSerializer(many=True, read_only=True)
    
    class Meta:
        model = DataCollectionActivity
        fields = ['id', 'activity_id', 'activity_type', 'start_time', 'end_time',
                  'description', 'agents']


class MonitoringDatasetSerializer(serializers.ModelSerializer):
    data_files = DataFileSerializer(many=True, read_only=True)
    activities = DataCollectionActivitySerializer(many=True, read_only=True)
    
    class Meta:
        model = MonitoringDataset
        fields = ['id', 'dataset_id', 'title', 'description', 'start_date', 'end_date',
                  'issued', 'modified', 'license_name', 'license_url', 'creator_name',
                  'creator_email', 'publisher_name', 'keywords', 'data_files', 'activities']
