"""
Django models for Data Center Monitoring FAIR dataset

Author: Roberta Lamberti
Institution: Area Science Park
"""

from django.db import models


class ComputeNode(models.Model):
    """A compute node (server/host) in the data center"""
    hostname = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Fully qualified domain name of the compute node"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Description of the compute node"
    )
    
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Physical location in datacenter"
    )
    
    def __str__(self):
        return self.hostname


class SensorType(models.Model):
    """Type of sensor (CPU, Memory, Disk, Network, etc.)"""
    
    SENSOR_TYPES = [
        ('CPU', 'CPU Usage'),
        ('LINUX_CPU', 'Linux CPU Frequency/Thermal'),
        ('MEMORY', 'Memory'),
        ('DISK_IO', 'Disk I/O'),
        ('NETWORK', 'Network'),
        ('INFINIBAND', 'InfiniBand'),
        ('SMART_DEVICE', 'SMART Device Health'),
        ('SMART_ATTR', 'SMART Attributes'),
        ('IPMI', 'IPMI Sensor'),
        ('PROCSTAT', 'Process Statistics'),
        ('TURBOSTAT', 'Turbostat'),
    ]
    
    name = models.CharField(
        max_length=32,
        choices=SENSOR_TYPES,
        unique=True,
        verbose_name="Sensor type name"
    )
    
    description = models.TextField(
        verbose_name="Description of what this sensor type measures"
    )
    
    sosa_uri = models.URLField(
        blank=True,
        verbose_name="SOSA/SSN ontology URI for this sensor type"
    )
    
    def __str__(self):
        return self.get_name_display()


class ObservableProperty(models.Model):
    """
    An observable property (SOSA/SSN concept)
    Examples: cpu_usage_user, memory_used, disk_reads, etc.
    """
    property_name = models.CharField(
        max_length=128,
        unique=True,
        verbose_name="Name of the observable property"
    )
    
    label = models.CharField(
        max_length=255,
        verbose_name="Human-readable label"
    )
    
    description = models.TextField(
        verbose_name="Description of the property"
    )
    
    unit = models.CharField(
        max_length=64,
        verbose_name="Unit of measurement (e.g., percent, bytes, hertz)"
    )
    
    qudt_unit_uri = models.URLField(
        blank=True,
        verbose_name="QUDT ontology URI for the unit"
    )
    
    data_type = models.CharField(
        max_length=32,
        choices=[
            ('INTEGER', 'Integer'),
            ('FLOAT', 'Float'),
            ('BOOLEAN', 'Boolean'),
            ('STRING', 'String'),
        ],
        verbose_name="Data type of measurements"
    )
    
    sensor_type = models.ForeignKey(
        SensorType,
        on_delete=models.CASCADE,
        related_name='observable_properties',
        verbose_name="Sensor type that observes this property"
    )
    
    def __str__(self):
        return f"{self.label} ({self.unit})"


class Sensor(models.Model):
    """
    A specific sensor instance deployed on a compute node
    Conforms to SOSA/SSN Sensor concept
    """
    sensor_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Unique sensor identifier (UUID or URI)"
    )
    
    sensor_type = models.ForeignKey(
        SensorType,
        on_delete=models.PROTECT,
        verbose_name="Type of sensor"
    )
    
    compute_node = models.ForeignKey(
        ComputeNode,
        on_delete=models.CASCADE,
        related_name='sensors',
        verbose_name="Compute node where sensor is deployed"
    )
    
    device_name = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Device name (e.g., 'sda', 'eth0', 'cpu0')"
    )
    
    interface_name = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="Network interface name (e.g., 'bond0', 'ibp59s0')"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Additional sensor description"
    )
    
    def __str__(self):
        return f"{self.sensor_type} on {self.compute_node.hostname}"


class MonitoringDataset(models.Model):
    """
    A collection of monitoring data (DCAT Dataset concept)
    """
    dataset_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Unique dataset identifier (UUID)"
    )
    
    title = models.CharField(
        max_length=512,
        verbose_name="Dataset title"
    )
    
    description = models.TextField(
        verbose_name="Dataset description"
    )
    
    start_date = models.DateTimeField(
        verbose_name="Start of data collection period"
    )
    
    end_date = models.DateTimeField(
        verbose_name="End of data collection period"
    )
    
    issued = models.DateField(
        auto_now_add=True,
        verbose_name="Publication date"
    )
    
    modified = models.DateTimeField(
        auto_now=True,
        verbose_name="Last modification date"
    )
    
    license_name = models.CharField(
        max_length=255,
        default="Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)",
        verbose_name="License name"
    )
    
    license_url = models.URLField(
        default="https://creativecommons.org/licenses/by-nc-sa/4.0/",
        verbose_name="License URL"
    )
    
    creator_name = models.CharField(
        max_length=255,
        verbose_name="Dataset creator name"
    )
    
    creator_email = models.EmailField(
        verbose_name="Dataset creator email"
    )
    
    publisher_name = models.CharField(
        max_length=255,
        default="Area Science Park",
        verbose_name="Publisher name"
    )
    
    keywords = models.TextField(
        verbose_name="Comma-separated keywords"
    )
    
    def __str__(self):
        return self.title


class DataFile(models.Model):
    """
    A data file containing observations (e.g., cpu.csv, mem.csv)
    Conforms to DCAT Distribution concept
    """
    filename = models.CharField(
        max_length=255,
        verbose_name="Filename"
    )
    
    dataset = models.ForeignKey(
        MonitoringDataset,
        on_delete=models.CASCADE,
        related_name='data_files',
        verbose_name="Parent dataset"
    )
    
    file_format = models.CharField(
        max_length=32,
        choices=[
            ('CSV', 'CSV'),
            ('PARQUET', 'Parquet'),
            ('JSON', 'JSON'),
        ],
        default='CSV',
        verbose_name="File format"
    )
    
    media_type = models.CharField(
        max_length=128,
        default="text/csv",
        verbose_name="MIME type"
    )
    
    file_path = models.CharField(
        max_length=512,
        verbose_name="Path to file"
    )
    
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="File size in bytes"
    )
    
    row_count = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Number of rows"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="File description"
    )
    
    sensor_type = models.ForeignKey(
        SensorType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="Sensor type contained in this file"
    )
    
    def __str__(self):
        return self.filename


# Note: For actual observation data, we don't store it in Django models
# because we have millions of time-series observations.
# Instead, we keep CSV/Parquet files and provide API access to them.


class DataCollectionActivity(models.Model):
    """
    Provenance information about data collection (PROV-O Activity)
    """
    activity_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Activity identifier"
    )
    
    activity_type = models.CharField(
        max_length=128,
        verbose_name="Type of activity (e.g., 'Data Collection')"
    )
    
    start_time = models.DateTimeField(
        verbose_name="Activity start time"
    )
    
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Activity end time"
    )
    
    description = models.TextField(
        verbose_name="Description of the activity"
    )
    
    dataset = models.ForeignKey(
        MonitoringDataset,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name="Associated dataset"
    )
    
    def __str__(self):
        return f"{self.activity_type}: {self.activity_id}"


class Agent(models.Model):
    """
    An agent (software or person) involved in data collection (PROV-O Agent)
    """
    AGENT_TYPES = [
        ('SOFTWARE', 'Software Agent'),
        ('PERSON', 'Person'),
        ('ORGANIZATION', 'Organization'),
    ]
    
    agent_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Agent identifier"
    )
    
    name = models.CharField(
        max_length=255,
        verbose_name="Agent name"
    )
    
    agent_type = models.CharField(
        max_length=32,
        choices=AGENT_TYPES,
        verbose_name="Type of agent"
    )
    
    version = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="Version (for software agents)"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Agent description"
    )
    
    homepage = models.URLField(
        blank=True,
        verbose_name="Homepage URL"
    )
    
    activities = models.ManyToManyField(
        DataCollectionActivity,
        related_name='agents',
        verbose_name="Activities associated with this agent"
    )
    
    def __str__(self):
        return f"{self.name} ({self.get_agent_type_display()})"
