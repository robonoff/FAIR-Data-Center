"""
REST API views for fairdatacenter
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
import pandas as pd
import numpy as np
import os

from .models import (
    ComputeNode, SensorType, ObservableProperty, Sensor,
    MonitoringDataset, DataFile
)
from .serializers import (
    ComputeNodeSerializer, SensorTypeSerializer, ObservablePropertySerializer,
    SensorSerializer, MonitoringDatasetSerializer
)


class DatasetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing monitoring datasets with search and filter capabilities.
    
    Search examples (use ?search= for keywords, title, description):
    - /api/datasets/?search=IPMI
    - /api/datasets/?search=CPU
    - /api/datasets/?search=monitoring
    
    Filter examples (exact match on dates):
    - /api/datasets/?start_date=2025-11-05
    - /api/datasets/?end_date=2025-11-06
    - /api/datasets/?issued=2025-11-18
    """
    queryset = MonitoringDataset.objects.all()
    serializer_class = MonitoringDatasetSerializer
    lookup_field = 'dataset_id'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Enable search on these fields (partial match, use ?search=term)
    search_fields = ['title', 'description', 'keywords', 'dataset_id']
    
    # Enable filtering on these fields (exact or range match)
    filterset_fields = ['issued', 'modified', 'start_date', 'end_date']
    
    # Enable ordering on these fields
    ordering_fields = ['issued', 'modified', 'start_date', 'end_date', 'title']
    ordering = ['-issued']  # Default ordering


class ComputeNodeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing compute nodes with search capability.
    
    Search examples:
    - /api/compute-nodes/?search=thin001
    """
    queryset = ComputeNode.objects.all()
    serializer_class = ComputeNodeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['hostname', 'node_id']


class SensorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing sensors with filtering.
    
    Filter examples:
    - /api/sensors/?sensor_type=CPU
    - /api/sensors/?compute_node=thin001
    """
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['sensor_type', 'compute_node']
    search_fields = ['sensor_id', 'sensor_type__name']


class ObservablePropertyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing observable properties
    """
    queryset = ObservableProperty.objects.all()
    serializer_class = ObservablePropertySerializer
    filterset_fields = ['sensor_type']


@api_view(['GET'])
def observations_view(request):
    """
    API endpoint for querying time-series observations from CSV files with dynamic filtering.
    
    Query parameters:
    - file: filename (required, e.g., 'cpu.csv', 'mem.csv', 'ipmi_sensor.csv')
    - limit: number of rows to return (default: 100, max: 10000)
    - offset: skip N rows for pagination
    - <column_name>: filter by any column in the CSV file
      * String columns: partial match (case-insensitive)
      * Numeric columns: exact match
    
    Examples: 
    - /api/observations/?file=mem.csv&host=thin001&limit=50
    - /api/observations/?file=ipmi_sensor.csv&unit=RPM
    - /api/observations/?file=ipmi_sensor.csv&name=Fan&unit=RPM
    - /api/observations/?file=cpu.csv&cpu=cpu0
    - /api/observations/?file=diskio.csv&name=sda
    
    Available columns depend on the file structure. Common columns:
    - host: hostname
    - name: sensor/metric name
    - unit: unit of measurement
    - timestamp: observation time
    """
    filename = request.query_params.get('file', None)
    limit = min(int(request.query_params.get('limit', 100)), 10000)
    offset = int(request.query_params.get('offset', 0))
    
    if not filename:
        return Response(
            {"error": "Missing 'file' parameter. Available files: cpu.csv, mem.csv, diskio.csv, net.csv, ipmi_sensor.csv, etc."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Build file path
    file_path = os.path.join(settings.DATASETS_PATH, filename)
    
    if not os.path.exists(file_path):
        return Response(
            {"error": f"File '{filename}' not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Apply dynamic filters for any column
        # Exclude special parameters (file, limit, offset) from filtering
        exclude_params = {'file', 'limit', 'offset', 'format'}
        
        for param, value in request.query_params.items():
            if param in exclude_params or not value:
                continue
            
            # Check if column exists in dataframe
            if param in df.columns:
                # For string columns, use partial match (case-insensitive)
                if df[param].dtype == 'object':
                    df = df[df[param].astype(str).str.contains(value, case=False, na=False)]
                # For numeric columns, use exact match
                else:
                    try:
                        numeric_value = pd.to_numeric(value)
                        df = df[df[param] == numeric_value]
                    except (ValueError, TypeError):
                        # If conversion fails, skip this filter
                        continue
        
        # Apply offset and limit after filtering
        total_count = len(df)
        df = df.iloc[offset:offset+limit]
        
        # Convert to dict and handle NaN values
        df = df.replace([np.inf, -np.inf], np.nan)
        data = df.to_dict(orient='records')
        
        # Replace NaN with None in the dict for JSON compatibility
        for record in data:
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
        
        response_data = {
            "file": filename,
            "total_matching": total_count,
            "count": len(data),
            "offset": offset,
            "limit": limit,
            "observations": data
        }
        
        return Response(response_data)
        
    except Exception as e:
        return Response(
            {"error": f"Error reading file: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



