"""
Django views for fairdatacenter web interface
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import MonitoringDataset, DataFile, ComputeNode
from pathlib import Path
import os


def index(request):
    """Homepage"""
    datasets = MonitoringDataset.objects.all()
    compute_nodes = ComputeNode.objects.all()
    
    context = {
        'datasets': datasets,
        'compute_nodes': compute_nodes,
    }
    return render(request, 'index.html', context)


def dataset_list(request):
    """Redirect to the first (or only) dataset detail page"""
    # Get the first dataset (there should only be one)
    dataset = MonitoringDataset.objects.first()
    
    if dataset:
        # Redirect to the dataset detail page
        return redirect('dataset_detail', dataset_id=dataset.dataset_id)
    else:
        # No datasets available
        context = {
            'datasets': [],
        }
    return render(request, 'dataset_list.html', context)


def dataset_detail(request, dataset_id):
    """Dataset detail page"""
    dataset = get_object_or_404(MonitoringDataset, dataset_id=dataset_id)
    data_files = dataset.data_files.all()
    activities = dataset.activities.all()
    
    # Split keywords into list and create Wikipedia URL mapping
    keyword_list = [k.strip() for k in dataset.keywords.split(',') if k.strip()] if dataset.keywords else []
    
    # Map keywords to custom URLs
    keyword_url_map = {
        'IPMI': 'https://en.wikipedia.org/wiki/Intelligent_Platform_Management_Interface',
        'InfiniBand': 'https://en.wikipedia.org/wiki/InfiniBand',
        'QuestDB': 'https://questdb.com/',
        'Telegraf': 'https://github.com/influxdata/telegraf',
        'monitoring': 'https://en.wikipedia.org/wiki/System_monitor',
        'network': 'https://en.wikipedia.org/wiki/Computer_network',
        'disk': 'https://en.wikipedia.org/wiki/Disk_storage',
        'memory': 'https://en.wikipedia.org/wiki/Random-access_memory',
    }
    
    # Create list of (keyword, url) tuples
    keywords = []
    for kw in keyword_list:
        if kw in keyword_url_map:
            url = keyword_url_map[kw]
        else:
            # Default: use keyword as-is for Wikipedia search
            from urllib.parse import quote
            url = f"https://en.wikipedia.org/wiki/{quote(kw.replace(' ', '_'))}"
        keywords.append({'text': kw, 'url': url})
    
    context = {
        'dataset': dataset,
        'data_files': data_files,
        'activities': activities,
        'keywords': keywords,
    }
    return render(request, 'dataset_detail.html', context)


def serve_catalog(request):
    """Serve the DCAT catalog in Turtle format"""
    catalog_path = settings.CATALOG_PATH
    
    if os.path.exists(catalog_path):
        return FileResponse(
            open(catalog_path, 'rb'),
            content_type='text/turtle',
            as_attachment=False,
            filename='catalog.ttl'
        )
    else:
        return HttpResponse(
            "Catalog file not found",
            status=404
        )


def serve_ontology(request):
    """Serve the datacenter monitoring ontology file"""
    catalog_path = Path(settings.BASE_DIR).parent / 'datacenter-ontology.ttl'
    
    if catalog_path.exists():
        with open(catalog_path, 'r') as f:
            content = f.read()
        return HttpResponse(
            content,
            content_type='text/turtle; charset=utf-8',
            headers={
                'Content-Disposition': 'inline; filename="datacenter-ontology.ttl"'
            }
        )
    else:
        return HttpResponse(
            "Ontology file not found",
            status=404
        )


def download_file(request, dataset_id, filename):
    """Download a CSV data file"""
    # Verify dataset exists
    dataset = get_object_or_404(MonitoringDataset, dataset_id=dataset_id)
    
    # Verify file belongs to this dataset
    data_file = get_object_or_404(DataFile, dataset=dataset, filename=filename)
    
    # Construct file path
    datasets_dir = Path(settings.BASE_DIR).parent / 'datasets'
    file_path = datasets_dir / filename
    
    # Check file exists
    if not file_path.exists():
        return HttpResponse(
            f"File {filename} not found on disk",
            status=404
        )
    
    # Serve file
    response = FileResponse(
        open(file_path, 'rb'),
        content_type='text/csv',
        as_attachment=True,
        filename=filename
    )
    
    # Add content length header
    response['Content-Length'] = file_path.stat().st_size
    
    return response


@api_view(['GET'])
def query_observations(request, dataset_id, table_name):
    """
    Query observations from a specific table/file with filtering.
    
    Query parameters:
    - limit: Maximum number of rows to return (default: 100, max: 10000)
    - offset: Number of rows to skip for pagination (default: 0)
    - format: Response format - 'json' (default) or 'csv'
    - Any column name: Filter by column value (partial match, case-insensitive)
    
    Examples:
    - ?limit=50 - Get first 50 rows
    - ?limit=100&offset=200 - Get rows 200-300
    - ?host=thin001 - Filter by host
    - ?format=csv - Download as CSV
    """
    import pandas as pd
    
    # Verify dataset exists
    dataset = get_object_or_404(MonitoringDataset, dataset_id=dataset_id)
    
    # Construct filename (add .csv if not present)
    filename = table_name if table_name.endswith('.csv') else f'{table_name}.csv'
    
    # Verify file belongs to this dataset
    data_file = get_object_or_404(DataFile, dataset=dataset, filename=filename)
    
    # Construct file path
    datasets_dir = Path(settings.BASE_DIR).parent / 'datasets'
    file_path = datasets_dir / filename
    
    # Check file exists
    if not file_path.exists():
        return Response(
            {'error': f'File {filename} not found on disk'},
            status=404
        )
    
    # Get query parameters
    limit = int(request.GET.get('limit', 100))
    offset = int(request.GET.get('offset', 0))
    limit = min(limit, 10000)  # Max 10k rows
    
    try:
        # Read CSV with pandas
        df = pd.read_csv(file_path)
        
        # Apply filters from query parameters
        for key, value in request.GET.items():
            if key not in ['limit', 'offset', 'format'] and key in df.columns:
                # Simple equality filter
                df = df[df[key].astype(str).str.contains(value, case=False, na=False)]
        
        # Apply pagination
        total_rows = len(df)
        df = df.iloc[offset:offset+limit]
        
        # Format response
        format_type = request.GET.get('format', 'json')
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{table_name}_query.csv"'
            df.to_csv(response, index=False)
            return response
        else:
            # Convert to JSON-safe format (replace NaN with None)
            import numpy as np
            import json
            
            # Convert DataFrame to records, replacing NaN/inf with None
            records = []
            for record in df.to_dict('records'):
                clean_record = {}
                for key, value in record.items():
                    if pd.isna(value) or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
                        clean_record[key] = None
                    else:
                        clean_record[key] = value
                records.append(clean_record)
            
            # JSON response with DRF Response for browsable API
            data = {
                'file': filename,
                'dataset': dataset.dataset_id,
                'dataset_title': dataset.title,
                'total_rows': total_rows,
                'returned_rows': len(df),
                'offset': offset,
                'limit': limit,
                'columns': list(df.columns),
                'data': records,
                'links': {
                    'self': f'/datasets/{dataset_id}/{table_name}?limit={limit}&offset={offset}',
                    'next': f'/datasets/{dataset_id}/{table_name}?limit={limit}&offset={offset+limit}' if offset+limit < total_rows else None,
                    'prev': f'/datasets/{dataset_id}/{table_name}?limit={limit}&offset={max(0, offset-limit)}' if offset > 0 else None,
                    'download_csv': f'/datasets/{dataset_id}/files/{filename}',
                    'dataset': f'/api/datasets/{dataset_id}/'
                }
            }
            return Response(data)
            
    except Exception as e:
        return Response(
            {'error': f'Error reading file: {str(e)}'},
            status=500
        )
