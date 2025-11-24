"""
Django management command to populate the database with initial data.

This command loads metadata from the catalog.ttl file and CSV file headers
to populate the Django database with datasets, sensors, nodes, and other metadata.

Usage:
    python manage.py load_metadata
"""

import os
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from rdflib import Graph, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF

from fairdatacenter.models import (
    ComputeNode,
    SensorType,
    ObservableProperty,
    Sensor,
    MonitoringDataset,
    DataFile,
    DataCollectionActivity,
    Agent
)


# Define namespaces
SOSA = Namespace("http://www.w3.org/ns/sosa/")
PROV = Namespace("http://www.w3.org/ns/prov#")
QUDT = Namespace("http://qudt.org/schema/qudt/")
UNIT = Namespace("http://qudt.org/vocab/unit/")
DCM = Namespace("http://areasciencepark.it/datacenter/ns#")
SCHEMA = Namespace("http://schema.org/")
DCT = Namespace("http://purl.org/dc/terms/")


class Command(BaseCommand):
    help = 'Load metadata from catalog.ttl and populate the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--catalog',
            type=str,
            default='catalog.ttl',
            help='Path to the catalog.ttl file (default: catalog.ttl in project root)'
        )
        parser.add_argument(
            '--datasets-dir',
            type=str,
            default='datasets',
            help='Path to the datasets directory (default: datasets in project root)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading'
        )

    def handle(self, *args, **options):
        # Determine paths
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        catalog_path = project_root / options['catalog']
        datasets_dir = project_root / options['datasets_dir']

        if not catalog_path.exists():
            raise CommandError(f"Catalog file not found: {catalog_path}")
        
        if not datasets_dir.exists():
            raise CommandError(f"Datasets directory not found: {datasets_dir}")

        # Clear existing data if requested
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            DataCollectionActivity.objects.all().delete()
            DataFile.objects.all().delete()
            MonitoringDataset.objects.all().delete()
            Sensor.objects.all().delete()
            ObservableProperty.objects.all().delete()
            SensorType.objects.all().delete()
            Agent.objects.all().delete()
            ComputeNode.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared existing data'))

        # Load RDF catalog
        self.stdout.write(f'Loading catalog from {catalog_path}...')
        g = Graph()
        g.parse(catalog_path, format='turtle')
        self.stdout.write(self.style.SUCCESS(f'✓ Loaded {len(g)} triples'))

        # Load data
        self.load_compute_nodes(g)
        self.load_sensor_types(g)
        self.load_observable_properties(g)
        self.load_agents(g)
        self.load_datasets(g, datasets_dir)
        
        self.stdout.write(self.style.SUCCESS('\n✓ All metadata loaded successfully!'))

    def load_compute_nodes(self, g):
        """Load compute nodes from the catalog."""
        self.stdout.write('\nLoading compute nodes...')
        
        # Define known nodes from the datasets
        nodes_data = [
            {
                'hostname': 'thin001.hpc.rd.areasciencepark.it',
                'location': 'Area Science Park HPC Cluster',
                'description': 'Compute node in HPC cluster',
            },
            {
                'hostname': 'area-rob',
                'location': 'Area Science Park',
                'description': 'Development workstation',
            }
        ]
        
        for node_data in nodes_data:
            node, created = ComputeNode.objects.get_or_create(
                hostname=node_data['hostname'],
                defaults=node_data
            )
            if created:
                self.stdout.write(f'  + Created node: {node.hostname}')
            else:
                self.stdout.write(f'  • Node exists: {node.hostname}')

    def load_sensor_types(self, g):
        """Load sensor types from the catalog."""
        self.stdout.write('\nLoading sensor types...')
        
        sensor_types = [
            {'name': 'CPU', 'description': 'CPU usage and performance metrics'},
            {'name': 'LINUX_CPU', 'description': 'Linux CPU frequency and thermal metrics'},
            {'name': 'MEMORY', 'description': 'Memory usage statistics'},
            {'name': 'DISK_IO', 'description': 'Disk read/write operations and throughput'},
            {'name': 'NETWORK', 'description': 'Network interface statistics'},
            {'name': 'INFINIBAND', 'description': 'InfiniBand network performance'},
            {'name': 'SMART_DEVICE', 'description': 'SMART device health metrics'},
            {'name': 'SMART_ATTR', 'description': 'SMART attribute details'},
            {'name': 'IPMI', 'description': 'IPMI sensor readings (temperature, voltage, etc.)'},
            {'name': 'PROCSTAT', 'description': 'Process statistics and resource usage'},
            {'name': 'TURBOSTAT', 'description': 'CPU frequency and power state monitoring'},
        ]
        
        for st_data in sensor_types:
            st, created = SensorType.objects.get_or_create(
                name=st_data['name'],
                defaults=st_data
            )
            if created:
                self.stdout.write(f'  + Created sensor type: {st.name}')

    def load_observable_properties(self, g):
        """Load observable properties from the catalog."""
        self.stdout.write('\nLoading observable properties...')
        
        # Query observable properties from RDF
        query = """
        SELECT ?prop ?name ?unit ?unitLabel
        WHERE {
            ?prop a sosa:ObservableProperty ;
                  rdfs:label ?name .
            OPTIONAL { ?prop qudt:hasUnit ?unit }
            OPTIONAL { ?unit rdfs:label ?unitLabel }
        }
        """
        
        g.bind('sosa', SOSA)
        g.bind('qudt', QUDT)
        
        count = 0
        for row in g.query(query, initNs={'sosa': SOSA, 'rdfs': RDFS, 'qudt': QUDT}):
            prop_id = str(row.prop).split('/')[-1]
            
            # Try to infer sensor type from property name
            sensor_type = None
            name_lower = str(row.name).lower()
            if 'cpu' in name_lower or 'processor' in name_lower:
                sensor_type = SensorType.objects.filter(name='CPU').first()
            elif 'memory' in name_lower or 'mem' in name_lower:
                sensor_type = SensorType.objects.filter(name='MEMORY').first()
            elif 'disk' in name_lower or 'io' in name_lower:
                sensor_type = SensorType.objects.filter(name='DISK_IO').first()
            elif 'network' in name_lower or 'net' in name_lower:
                sensor_type = SensorType.objects.filter(name='NETWORK').first()
            
            # Skip if no sensor type found
            if not sensor_type:
                continue
            
            prop, created = ObservableProperty.objects.get_or_create(
                property_name=prop_id,
                defaults={
                    'label': str(row.name),
                    'description': str(row.name),
                    'unit': str(row.unitLabel) if row.unitLabel else 'dimensionless',
                    'qudt_unit_uri': str(row.unit) if row.unit else '',
                    'data_type': 'FLOAT',
                    'sensor_type': sensor_type,
                }
            )
            if created:
                count += 1
        
        self.stdout.write(f'  + Created {count} observable properties')

    def load_agents(self, g):
        """Load agents (software/systems) from the catalog."""
        self.stdout.write('\nLoading agents...')
        
        # Query agents from RDF
        query = """
        SELECT ?agent ?name ?type
        WHERE {
            ?agent a prov:Agent ;
                   foaf:name ?name .
            OPTIONAL { ?agent a ?type }
            FILTER(?type != prov:Agent)
        }
        """
        
        g.bind('prov', PROV)
        g.bind('foaf', FOAF)
        
        for row in g.query(query, initNs={'prov': PROV, 'foaf': FOAF}):
            agent_id = str(row.agent).split('/')[-1]
            
            # Determine agent type
            agent_type = 'software'
            if row.type:
                type_str = str(row.type).lower()
                if 'software' in type_str:
                    agent_type = 'software'
            
            agent, created = Agent.objects.get_or_create(
                agent_id=agent_id,
                defaults={
                    'name': str(row.name),
                    'agent_type': agent_type,
                }
            )
            if created:
                self.stdout.write(f'  + Created agent: {agent.name}')

    def load_datasets(self, g, datasets_dir):
        """Load datasets and data files from the catalog."""
        self.stdout.write('\nLoading datasets...')
        
        # Query dataset from RDF
        query = """
        SELECT ?dataset ?identifier ?title ?description ?startDate ?endDate ?issued ?modified
               ?creatorName ?creatorEmail ?publisherName ?licenseName
               (GROUP_CONCAT(DISTINCT ?keyword; separator=", ") AS ?keywords)
        WHERE {
            ?dataset a dcat:Dataset ;
                     dct:identifier ?identifier ;
                     dct:title ?title ;
                     dct:description ?description .
            OPTIONAL {
                ?dataset dct:temporal ?temporal .
                ?temporal dcat:startDate ?startDate ;
                          dcat:endDate ?endDate .
            }
            OPTIONAL { ?dataset dct:issued ?issued }
            OPTIONAL { ?dataset dct:modified ?modified }
            OPTIONAL { 
                ?dataset dct:creator ?creator .
                ?creator foaf:name ?creatorName .
                OPTIONAL { ?creator foaf:mbox ?creatorEmail }
            }
            OPTIONAL {
                ?dataset dct:publisher ?publisher .
                ?publisher foaf:name ?publisherName .
            }
            OPTIONAL {
                ?dataset dct:license ?license .
            }
            OPTIONAL { ?dataset dct:keyword ?keyword }
        }
        GROUP BY ?dataset ?identifier ?title ?description ?startDate ?endDate ?issued ?modified
                 ?creatorName ?creatorEmail ?publisherName ?licenseName
        """
        
        g.bind('dcat', DCAT)
        g.bind('dct', DCT)
        g.bind('foaf', FOAF)
        g.bind('schema', SCHEMA)
        
        for row in g.query(query, initNs={'dcat': DCAT, 'dct': DCT, 'foaf': FOAF, 'schema': SCHEMA, 'rdfs': RDFS}):
            # Use dct:identifier (UUID) as dataset_id
            dataset_id = str(row.identifier) if row.identifier else None
            
            # Store dataset URI for finding related resources
            dataset_uri = str(row.dataset)
            
            if not dataset_id:
                # Fallback: extract from URI if identifier is missing
                dataset_id = dataset_uri.split('#')[-1] if '#' in dataset_uri else dataset_uri.split('/')[-1]
            
            # Parse dates
            start_date = self.parse_date(str(row.startDate))
            end_date = self.parse_date(str(row.endDate))
            issued = self.parse_date(str(row.issued)) if row.issued else datetime.now().date()
            modified = datetime.now()
            
            # Extract license URL and name
            license_url = str(row.license) if hasattr(row, 'license') and row.license else 'https://creativecommons.org/licenses/by-nc-sa/4.0/'
            
            # Map license URLs to names
            if 'by-nc-sa/4.0' in license_url:
                license_name = 'CC BY-NC-SA 4.0'
            elif 'by/4.0' in license_url:
                license_name = 'CC BY 4.0'
            else:
                license_name = 'Unknown License'
            
            dataset, created = MonitoringDataset.objects.update_or_create(
                dataset_id=dataset_id,
                defaults={
                    'title': str(row.title),
                    'description': str(row.description),
                    'start_date': start_date,
                    'end_date': end_date,
                    'issued': issued,
                    'modified': modified,
                    'creator_name': str(row.creatorName) if row.creatorName else 'Unknown',
                    'creator_email': str(row.creatorEmail).replace('mailto:', '') if row.creatorEmail else '',
                    'publisher_name': str(row.publisherName) if row.publisherName else 'Area Science Park',
                    'license_name': license_name,
                    'license_url': license_url,
                    'keywords': str(row.keywords) if row.keywords else '',
                }
            )
            
            if created:
                self.stdout.write(f'  + Created dataset: {dataset.title}')
            else:
                self.stdout.write(f'  ✓ Updated dataset: {dataset.title}')
            
            # Load distributions (data files) - pass dataset URI for querying
            self.load_data_files(g, dataset, datasets_dir, dataset_uri)
            
            # Load activities
            self.load_activities(g, dataset)

    def load_data_files(self, g, dataset, datasets_dir, dataset_uri):
        """Load data files (distributions) for a dataset."""
        self.stdout.write(f'\n  Loading data files for dataset: {dataset.dataset_id}')
        
        # Query data files (members) from RDF using the actual dataset URI
        query = f"""
        SELECT ?file ?title ?format ?description
        WHERE {{
            <{dataset_uri}> prov:hadMember ?file .
            ?file dct:title ?title ;
                  dct:format ?format .
            OPTIONAL {{ ?file dct:description ?description }}
        }}
        """
        
        results = list(g.query(query, initNs={'dcat': DCAT, 'dct': DCT, 'prov': PROV}))
        self.stdout.write(f'  Found {len(results)} files in RDF')
        
        for row in results:
            filename = str(row.title)  # title is the filename like "cpu.csv"
            file_path = datasets_dir / filename
            
            # Get file statistics if file exists
            file_size = None
            row_count = None
            if file_path.exists():
                file_size = file_path.stat().st_size
                # Count rows in CSV (excluding header)
                try:
                    with open(file_path, 'r') as f:
                        row_count = sum(1 for _ in f) - 1
                except:
                    pass
            
            # Infer sensor type from filename
            sensor_type = None
            fn_lower = filename.lower()
            if 'cpu' in fn_lower and 'linux' not in fn_lower:
                sensor_type = SensorType.objects.filter(name='CPU').first()
            elif 'linux_cpu' in fn_lower or 'linux-cpu' in fn_lower:
                sensor_type = SensorType.objects.filter(name='LINUX_CPU').first()
            elif 'mem' in fn_lower:
                sensor_type = SensorType.objects.filter(name='MEMORY').first()
            elif 'diskio' in fn_lower or 'disk' in fn_lower:
                sensor_type = SensorType.objects.filter(name='DISK_IO').first()
            elif 'infiniband' in fn_lower:
                sensor_type = SensorType.objects.filter(name='INFINIBAND').first()
            elif 'net' in fn_lower and 'infiniband' not in fn_lower:
                sensor_type = SensorType.objects.filter(name='NETWORK').first()
            elif 'smart_device' in fn_lower or 'smart-device' in fn_lower:
                sensor_type = SensorType.objects.filter(name='SMART_DEVICE').first()
            elif 'smart_attr' in fn_lower or 'smart-attr' in fn_lower:
                sensor_type = SensorType.objects.filter(name='SMART_ATTR').first()
            elif 'ipmi' in fn_lower:
                sensor_type = SensorType.objects.filter(name='IPMI').first()
            elif 'procstat' in fn_lower:
                sensor_type = SensorType.objects.filter(name='PROCSTAT').first()
            elif 'turbostat' in fn_lower:
                sensor_type = SensorType.objects.filter(name='TURBOSTAT').first()
            
            # Extract media type from format
            media_type = str(row.format) if row.format else 'text/csv'
            file_format = 'CSV' if 'csv' in media_type.lower() else 'unknown'
            
            data_file, created = DataFile.objects.get_or_create(
                dataset=dataset,
                filename=filename,
                defaults={
                    'file_path': str(file_path),
                    'file_format': file_format,
                    'media_type': media_type,
                    'description': str(row.description) if row.description else '',
                    'file_size': file_size,
                    'row_count': row_count,
                    'sensor_type': sensor_type,
                }
            )
            
            if created:
                self.stdout.write(f'    • Added file: {filename} ({row_count} rows)')

    def load_activities(self, g, dataset):
        """Load provenance activities for a dataset."""
        # Query activities from RDF - trova tutte le prov:Activity
        query = """
        SELECT ?activity ?label ?startTime ?endTime ?description
        WHERE {
            ?activity a prov:Activity .
            OPTIONAL { ?activity rdfs:label ?label }
            OPTIONAL { ?activity prov:startedAtTime ?startTime }
            OPTIONAL { ?activity prov:endedAtTime ?endTime }
            OPTIONAL { ?activity rdfs:comment ?description }
        }
        """
        
        for row in g.query(query, initNs={'prov': PROV, 'rdfs': RDFS}):
            activity_id = str(row.activity).split('/')[-1]
            activity_uri = str(row.activity)
            
            # Use label as activity type, or default to 'Data Collection'
            activity_type = str(row.label) if row.label else 'Data Collection Activity'
            
            start_time = self.parse_datetime(str(row.startTime)) if row.startTime else None
            end_time = self.parse_datetime(str(row.endTime)) if row.endTime else None
            
            activity, created = DataCollectionActivity.objects.get_or_create(
                activity_id=activity_id,
                defaults={
                    'dataset': dataset,
                    'activity_type': activity_type,
                    'description': str(row.description) if row.description else '',
                    'start_time': start_time,
                    'end_time': end_time,
                }
            )
            
            if created:
                self.stdout.write(f'    • Added activity: {activity_id}')
                
                # Associate agents with activity
                self.load_activity_agents(g, activity)

    def load_activity_agents(self, g, activity):
        """Load agents associated with an activity."""
        query = f"""
        SELECT ?agent
        WHERE {{
            <{DCM}{activity.activity_id}> prov:wasAssociatedWith ?agent .
        }}
        """
        
        for row in g.query(query, initNs={'prov': PROV}):
            agent_id = str(row.agent).split('/')[-1]
            try:
                agent = Agent.objects.get(agent_id=agent_id)
                activity.agents.add(agent)
            except Agent.DoesNotExist:
                pass

    def parse_date(self, date_str):
        """Parse date string to date object."""
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        except:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                return None

    def parse_datetime(self, datetime_str):
        """Parse datetime string to datetime object."""
        try:
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except:
            return None
