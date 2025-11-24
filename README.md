# FAIR Data Center Monitoring

A FAIR-compliant data system for HPC infrastructure monitoring data, developed at Area Science Park, Trieste, Italy. This project is part of the Advanced Data Management exam held by lecturers at INAF and Area Science Park, respectively: [Andrea Bignamini](linkedin.com/in/andrea-bignamini-aaa2083a?originalSubdomain=it), [Marco Molinaro](https://www.linkedin.com/in/marco-molinaro/), [Marco Frailis](https://www.linkedin.com/in/marco-frailis-2779a9b/) and [Federica Bazzocchi](https://www.linkedin.com/in/federica-bazzocchi-a48b8219/).

## Overview

This project implements a web-based data catalog following FAIR (Findable, Accessible, Interoperable, Reusable) principles for managing time-series monitoring data from high-performance computing infrastructure. 
The system integrates semantic metadata (RDF/Turtle), Django ORM for data management, and REST APIs for data access.

## Features

- **FAIR-Compliant Metadata**: Uses DCAT 2.0 vocabulary for dataset descriptions
- **Semantic Web Standards**: RDF/Turtle format with SPARQL query support
- **Sensor Ontology**: SOSA/SSN ontology for sensor observations and measurements
- **Provenance Tracking**: PROV-O ontology for data generation activities
- **REST API**: RESTful endpoints for programmatic data access
- **Web Interface**: Django-based UI for browsing datasets and files
- **QuestDB Integration**: Time-series database synchronization

## Tech Stack

- **Backend**: Django 5.2.8 with Django REST Framework
- **Database**: SQLite (metadata), QuestDB (time-series data)
- **Semantic Web**: RDFLib for RDF parsing and SPARQL queries
- **Data Processing**: Pandas for CSV manipulation
- **Standards**: DCAT 2.0, SOSA/SSN, PROV-O, Dublin Core, QUDT

## Project Structure

```
FAIR-Data_Center/
├── catalog.ttl                  # RDF catalog with DCAT metadata
├── datacenter-ontology.ttl      # Domain ontology for data center monitoring
├── requirements.txt             # Python dependencies
├── LICENSE                      # MIT License
│
├── fairdatacenter/             # Django application
    ├── manage.py               # Django management script
    ├── db.sqlite3              # SQLite database (gitignored)
    │
    └── fairdatacenter/         # Main Django app
        ├── models.py           # Django ORM models (8 classes)
        ├── views.py            # Web interface views
        ├── rest_views.py       # REST API endpoints
        ├── serializers.py      # DRF serializers
        ├── urls.py             # URL routing
        ├── settings.py         # Django configuration
        │
        ├── management/
        │   └── commands/
        │       └── load_metadata.py        # Import RDF catalog to Django
        │
        ├── templates/          # HTML templates
        │   ├── base.html
        │   ├── index.html
        │   ├── dataset_list.html
        │   └── dataset_detail.html
        │
        └── migrations/         # Database migrations
```

## Data Model

The system uses 8 Django models representing the domain:

### Core Models

- **ComputeNode**: HPC compute nodes (e.g., thin001, thin002)
- **SensorType**: Categories of sensors (CPU, memory, disk, network, etc.)
- **ObservableProperty**: Measurable properties (temperature, usage, bandwidth)
- **Sensor**: Individual sensors deployed on compute nodes

### Metadata Models

- **MonitoringDataset**: Dataset metadata (title, description, keywords, temporal coverage)
- **DataFile**: CSV files containing observations (member of datasets)
- **DataCollectionActivity**: Provenance information (who, when, how data was collected)
- **Agent**: Entities responsible for data collection (Telegraf, humans, organizations)

## RDF Catalog Structure

The `catalog.ttl` file contains:

- **Catalog**: Root container for all datasets
- **Dataset**: Metadata about the monitoring dataset (UUID, title, description, keywords, temporal coverage)
- **Distributions**: Links to CSV files with format information
- **Provenance**: PROV-O activities and agents
- **Sensor Descriptions**: SOSA/SSN sensor and platform definitions


## Setup Instructions

### Prerequisites

- Python 3.12+
- pip package manager
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/FAIR-Data-Center.git
cd FAIR-Data-Center
```

2. Create and activate virtual environment:
```bash
python3 -m venv env
source env/bin/activate  # Linux/macOS
# or
env\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Navigate to Django project:
```bash
cd fairdatacenter
```

5. Run database migrations:
```bash
python manage.py migrate
```

6. Imports metadata from `catalog.ttl` into Django database using SPARQL queries.

```bash
python manage.py load_metadata
```

7. Start development server:
```bash
python manage.py runserver
```

## Management Commands

### load_metadata

Imports metadata from `catalog.ttl` into Django database using SPARQL queries.

```bash
python manage.py load_metadata
```

This command:
- Parses RDF catalog with RDFLib
- Extracts dataset, file, sensor, and provenance information
- Creates/updates Django model instances
- Links relationships between entities

## Data Files

The system manages 12 types of monitoring data:

- `cpu.csv` - CPU metrics 
- `mem.csv` - Memory usage
- `diskio.csv` - Disk I/O statistics
- `net.csv` - Network interface metrics
- `infiniband.csv` - InfiniBand network data
- `linux_cpu.csv` - Linux-specific CPU data
- `smart_device.csv` - SMART disk health
- `smart_attribute.csv` - SMART attributes
- `ipmi_sensor.csv` - IPMI sensor readings
- `procstat.csv` - Process statistics
- `procstat_lookup.csv` - Process lookup table
- `turbostat.csv` - CPU Turbo Boost statistics

All CSV files have not been uploaded as they can't be published yet.

## FAIR Principles Implementation

### Findable
- Unique persistent identifier (UUID) for dataset
- Rich metadata in standardized format (DCAT)
- Keyword-based discovery
- Machine-readable catalog (RDF/Turtle)

### Accessible
- Open REST API with standard HTTP protocols
- Clear access URLs for all resources
- CSV format for maximum compatibility
- Web interface for human access

### Interoperable
- Standard vocabularies (DCAT, Dublin Core, SOSA/SSN, PROV-O)
- RDF/Turtle serialization
- SPARQL query support
- JSON-LD compatible metadata

### Reusable
- Clear MIT license
- Comprehensive provenance (PROV-O)
- Detailed documentation
- Standard data formats (CSV)
- Unit metadata (QUDT ontology)



## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License

Copyright (c) 2025 Roberta Lamberti

See LICENSE file for full license text.

## Author

Roberta Lamberti  
Area Science Park, Trieste, Italy

## Acknowledgments

- DCAT 2.0 specification by W3C
- SOSA/SSN ontologies by W3C
- PROV-O ontology by W3C
- QuestDB time-series database
- Django and Django REST Framework communities
