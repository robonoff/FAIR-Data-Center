"""
Django management command to sync data from QuestDB using REST API

Usage:
    python manage.py sync_from_questdb_rest --start 2025-11-05 --end 2025-11-06

Requirements:
    pip install requests pandas

Author: Roberta Lamberti
Institution: Area Science Park
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import pandas as pd
from pathlib import Path
from datetime import datetime
import requests
from io import StringIO


class Command(BaseCommand):
    help = 'Sync monitoring data from QuestDB to local CSV files using REST API'

    # QuestDB REST API defaults
    QUESTDB_BASE_URL = 'https://timeseriesdb.dev.rd.areasciencepark.it'
    
    # Tables to sync
    TABLES = [
        'cpu', 'mem', 'diskio', 'net', 'infiniband',
        'linux_cpu', 'smart_device', 'smart_attribute',
        'ipmi_sensor', 'procstat', 'procstat_lookup', 'turbostat'
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--start',
            type=str,
            help='Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)',
            required=True
        )
        parser.add_argument(
            '--end',
            type=str,
            help='End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)',
            required=True
        )
        parser.add_argument(
            '--tables',
            type=str,
            nargs='+',
            help='Specific tables to sync (default: all)',
            default=None
        )
        parser.add_argument(
            '--url',
            type=str,
            default=self.QUESTDB_BASE_URL,
            help='QuestDB base URL'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            help='Output directory for CSV files (default: datasets/)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of rows per table (for testing)'
        )

    def parse_date_range(self, start_date, end_date):
        """Parse start and end dates to ISO format."""
        try:
            # Try parsing with time
            start = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            # Parse as date only
            start = datetime.strptime(start_date, '%Y-%m-%d')
        
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Format for QuestDB
        start_ts = start.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
        end_ts = end.strftime('%Y-%m-%dT%H:%M:%S.999999Z')
        
        return start_ts, end_ts

    def query_questdb(self, base_url, query):
        """Execute SQL query via REST API and return DataFrame."""
        # QuestDB REST API endpoint
        exec_url = f'{base_url}/exec'
        
        # Parameters
        params = {
            'query': query,
            'count': 'true',
            'nm': 'false'  # include column names
        }
        
        try:
            # Make request
            response = requests.get(exec_url, params=params, timeout=30, verify=False)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            if 'error' in data:
                raise CommandError(f"QuestDB query error: {data['error']}")
            
            # Convert to DataFrame
            if 'dataset' in data and data['dataset']:
                df = pd.DataFrame(
                    data['dataset'],
                    columns=[col['name'] for col in data['columns']]
                )
                return df
            else:
                # Empty result
                return pd.DataFrame()
                
        except requests.exceptions.RequestException as e:
            raise CommandError(f'HTTP request failed: {e}')
        except Exception as e:
            raise CommandError(f'Error processing response: {e}')

    def format_size(self, size_bytes):
        """Format bytes to human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f'{size_bytes:.1f} {unit}'
            size_bytes /= 1024.0
        return f'{size_bytes:.1f} TB'

    def handle(self, *args, **options):
        start_date = options['start']
        end_date = options['end']
        tables = options['tables'] if options['tables'] else self.TABLES
        base_url = options['url']
        limit = options['limit']

        # Determine output directory
        if options['output_dir']:
            output_dir = Path(options['output_dir'])
        else:
            output_dir = Path(settings.BASE_DIR).parent / 'datasets'

        output_dir.mkdir(exist_ok=True)

        self.stdout.write(self.style.SUCCESS(f'\n🔄 Syncing data from QuestDB (REST API)'))
        self.stdout.write(f'   URL: {base_url}')
        self.stdout.write(f'   Period: {start_date} to {end_date}')
        self.stdout.write(f'   Tables: {", ".join(tables)}')
        self.stdout.write(f'   Output: {output_dir}')
        if limit:
            self.stdout.write(f'   Limit: {limit:,} rows per table')
        self.stdout.write('')

        # Parse dates
        start_ts, end_ts = self.parse_date_range(start_date, end_date)

        # Test connection
        try:
            self.stdout.write('  • Testing connection...')
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Test with a simple query
            test_query = 'SELECT 1'
            response = requests.get(
                f'{base_url}/exec',
                params={'query': test_query},
                timeout=30,
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                raise CommandError(f"QuestDB error: {data['error']}")
            
            self.stdout.write(self.style.SUCCESS('    ✓ QuestDB API is reachable'))
            
        except requests.exceptions.RequestException as e:
            raise CommandError(
                f'\n❌ Cannot reach QuestDB at {base_url}\n'
                f'   Error: {e}\n'
                f'   Please check:\n'
                f'   1. URL is correct\n'
                f'   2. VPN connection (if required)\n'
                f'   3. Server is running'
            )

        success_count = 0
        error_count = 0
        total_rows = 0

        for table in tables:
            try:
                self.stdout.write(f'\n  • Processing {table}...')

                # Build SQL query
                limit_clause = f'LIMIT {limit}' if limit else ''
                query = f"""
                SELECT * FROM {table}
                WHERE timestamp >= '{start_ts}'
                AND timestamp <= '{end_ts}'
                ORDER BY timestamp
                {limit_clause}
                """

                # Fetch data
                self.stdout.write(f'    • Fetching data...')
                df = self.query_questdb(base_url, query)

                if df.empty:
                    self.stdout.write(
                        self.style.WARNING(f'    ⚠️  No data found in date range')
                    )
                    continue

                row_count = len(df)
                total_rows += row_count

                # Save to CSV
                output_file = output_dir / f'{table}.csv'
                df.to_csv(output_file, index=False)

                file_size = output_file.stat().st_size
                self.stdout.write(
                    self.style.SUCCESS(
                        f'    ✓ Saved {table}.csv: {row_count:,} rows, '
                        f'{self.format_size(file_size)}'
                    )
                )

                success_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Failed to sync {table}: {e}')
                )
                error_count += 1
                continue

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n✅ Sync completed!'))
        self.stdout.write(f'   Tables synced: {success_count}/{len(tables)}')
        self.stdout.write(f'   Total rows: {total_rows:,}')
        self.stdout.write(f'   Failed: {error_count}')
        self.stdout.write(f'   Output directory: {output_dir}\n')
