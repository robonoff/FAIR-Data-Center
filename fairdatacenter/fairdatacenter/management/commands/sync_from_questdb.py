"""
Django management command to sync data from QuestDB using PostgreSQL wire protocol

Usage:
    python manage.py sync_from_questdb --start 2025-11-05 --end 2025-11-06

Requirements:
    pip install psycopg2-binary

Author: Roberta Lamberti
Institution: Area Science Park
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    psycopg2 = None


class Command(BaseCommand):
    help = 'Sync monitoring data from QuestDB to local CSV files using PostgreSQL protocol'

    # QuestDB connection defaults
    QUESTDB_HOST = 'timeseriesdb.dev.rd.areasciencepark.it'
    QUESTDB_PORT = 8812
    QUESTDB_DATABASE = 'qdb'
    QUESTDB_USER = 'admin'
    QUESTDB_PASSWORD = 'quest'

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
            '--host',
            type=str,
            default=self.QUESTDB_HOST,
            help='QuestDB host'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=self.QUESTDB_PORT,
            help='QuestDB PostgreSQL port (default: 8812)'
        )
        parser.add_argument(
            '--database',
            type=str,
            default=self.QUESTDB_DATABASE,
            help='QuestDB database name'
        )
        parser.add_argument(
            '--user',
            type=str,
            default=self.QUESTDB_USER,
            help='QuestDB username'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=self.QUESTDB_PASSWORD,
            help='QuestDB password'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default=None,
            help='Output directory for CSV files (default: ../datasets/)'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=50000,
            help='Rows per chunk for large datasets (default: 50000)'
        )

    def handle(self, *args, **options):
        # Check psycopg2 installation
        if psycopg2 is None:
            raise CommandError(
                'psycopg2 is not installed. Run: pip install psycopg2-binary'
            )

        start_date = options['start']
        end_date = options['end']
        tables = options['tables'] or self.TABLES
        chunk_size = options['chunk_size']

        # Connection parameters
        conn_params = {
            'host': options['host'],
            'port': options['port'],
            'database': options['database'],
            'user': options['user'],
            'password': options['password']
        }

        # Determine output directory
        if options['output_dir']:
            output_dir = Path(options['output_dir'])
        else:
            output_dir = Path(settings.BASE_DIR).parent / 'datasets'

        output_dir.mkdir(exist_ok=True)

        self.stdout.write(self.style.SUCCESS(f'\n🔄 Syncing data from QuestDB (PostgreSQL Protocol)'))
        self.stdout.write(f'   Host: {conn_params["host"]}:{conn_params["port"]}')
        self.stdout.write(f'   Period: {start_date} to {end_date}')
        self.stdout.write(f'   Tables: {", ".join(tables)}')
        self.stdout.write(f'   Output: {output_dir}')
        self.stdout.write(f'   Chunk size: {chunk_size:,} rows\n')

        # Parse dates
        start_ts, end_ts = self.parse_date_range(start_date, end_date)

        # Connect to QuestDB
        try:
            self.stdout.write('  • Connecting to QuestDB...')
            self.stdout.write(f'    • Testing connection to {conn_params["host"]}:{conn_params["port"]}...')
            
            # Add connection timeout
            conn_params['connect_timeout'] = 10
            
            import socket
            # First test if host is reachable
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((conn_params['host'], conn_params['port']))
                sock.close()
                
                if result != 0:
                    raise CommandError(
                        f'\n❌ Cannot reach {conn_params["host"]}:{conn_params["port"]}\n'
                        f'   Please check:\n'
                        f'   1. VPN connection to Area Science Park network\n'
                        f'   2. Firewall settings\n'
                        f'   3. QuestDB server is running\n'
                        f'   Socket error code: {result}'
                    )
                else:
                    self.stdout.write(self.style.SUCCESS('    ✓ Host is reachable'))
            except socket.timeout:
                raise CommandError(
                    f'\n❌ Connection timeout to {conn_params["host"]}:{conn_params["port"]}\n'
                    f'   The server is not responding. Please check your VPN connection.'
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'    ⚠️  Socket test failed: {e}'))
            
            # Now try PostgreSQL connection
            self.stdout.write(f'    • Authenticating as {conn_params["user"]}...')
            conn = psycopg2.connect(**conn_params)
            self.stdout.write(self.style.SUCCESS('    ✓ Connected successfully'))
            
            # Test query
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            self.stdout.write(self.style.SUCCESS('    ✓ Database responsive'))
            
        except psycopg2.OperationalError as e:
            raise CommandError(
                f'\n❌ PostgreSQL connection failed: {e}\n'
                f'   Common issues:\n'
                f'   1. Wrong credentials (user/password)\n'
                f'   2. Database name incorrect (current: {conn_params["database"]})\n'
                f'   3. PostgreSQL protocol not enabled on QuestDB\n'
                f'   Try accessing the web console at:\n'
                f'   https://{conn_params["host"]}/index.html'
            )
        except psycopg2.Error as e:
            raise CommandError(f'\n❌ Database error: {e}')

        success_count = 0
        error_count = 0
        total_rows = 0

        try:
            for table in tables:
                try:
                    self.stdout.write(f'\n  • Processing {table}...')

                    # Check if table exists
                    if not self.table_exists(conn, table):
                        self.stdout.write(
                            self.style.WARNING(f'    ⚠️  Table {table} does not exist, skipping')
                        )
                        continue

                    # Build SQL query
                    query = f"""
                    SELECT * FROM {table}
                    WHERE timestamp >= '{start_ts}'
                    AND timestamp <= '{end_ts}'
                    ORDER BY timestamp
                    """

                    # Fetch data using pandas (handles chunking internally)
                    self.stdout.write(f'    • Fetching data...')
                    df = pd.read_sql_query(query, conn)

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

                except psycopg2.Error as e:
                    self.stdout.write(
                        self.style.ERROR(f'    ✗ Database error: {str(e)}')
                    )
                    error_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'    ✗ Error: {str(e)}')
                    )
                    error_count += 1

        finally:
            conn.close()
            self.stdout.write('\n  • Disconnected from QuestDB')

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✓ Sync completed'))
        self.stdout.write(f'  Success: {success_count} tables')
        self.stdout.write(f'  Total rows: {total_rows:,}')
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'  Errors: {error_count} tables'))

        self.stdout.write('\n📋 Next steps:')
        self.stdout.write('  1. Update catalog.ttl temporal coverage:')
        self.stdout.write(f'     dcat:startDate "{start_ts}"')
        self.stdout.write(f'     dcat:endDate "{end_ts}"')
        self.stdout.write('  2. Run: python manage.py load_metadata')
        self.stdout.write('  3. Restart server: python manage.py runserver\n')

    def parse_date_range(self, start_date, end_date):
        """Parse date strings to QuestDB timestamp format"""
        try:
            # Try parsing with time
            if ' ' in start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
            else:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')

            if ' ' in end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            else:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59
                )

        except ValueError as e:
            raise CommandError(f'Invalid date format: {e}')

        # Convert to ISO format
        start_ts = start_dt.strftime('%Y-%m-%dT%H:%M:%S.000000Z')
        end_ts = end_dt.strftime('%Y-%m-%dT%H:%M:%S.999999Z')

        return start_ts, end_ts

    def table_exists(self, conn, table_name):
        """Check if table exists in QuestDB"""
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT table_name FROM tables() WHERE table_name = %s",
                (table_name,)
            )
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except psycopg2.Error:
            return False

    def format_size(self, size_bytes):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f'{size_bytes:.1f} {unit}'
            size_bytes /= 1024.0
        return f'{size_bytes:.1f} TB'
