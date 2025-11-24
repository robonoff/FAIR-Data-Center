"""
URL configuration for fairdatacenter project.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from . import views, rest_views

# API Router
router = routers.DefaultRouter()
router.register(r'datasets', rest_views.DatasetViewSet, basename='dataset')
router.register(r'sensors', rest_views.SensorViewSet, basename='sensor')
router.register(r'compute-nodes', rest_views.ComputeNodeViewSet, basename='computenode')
router.register(r'observable-properties', rest_views.ObservablePropertyViewSet, basename='observableproperty')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('datasets/', views.dataset_list, name='dataset_list'),
    path('datasets/<str:dataset_id>/', views.dataset_detail, name='dataset_detail'),
    path('catalog.ttl', views.serve_catalog, name='catalog'),
    path('ontology.ttl', views.serve_ontology, name='ontology'),
    # File downloads
    path('datasets/<str:dataset_id>/files/<str:filename>', views.download_file, name='download_file'),
    # Query observations from specific file
    path('datasets/<str:dataset_id>/<str:table_name>', views.query_observations, name='query_observations'),
    # API endpoints
    path('api/observations/', rest_views.observations_view, name='observations'),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
