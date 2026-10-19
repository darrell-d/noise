import os
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
load_dotenv(root / '.env')
address = os.getenv('BIND_ADDRESS', '127.0.0.1')
port = int(os.getenv('PORT', '8000'))
workers = os.getenv('WEB_CONCURRENCY', '1')
print(f'Noise is starting at http://{address}:{port}/noise/ (Ctrl-C to stop)', flush=True)
os.execv(sys.executable, [
    sys.executable, '-m', 'gunicorn', 'noise_site.wsgi:application',
    '--bind', f'{address}:{port}', '--workers', workers,
    '--timeout', '120', '--access-logfile', '-',
])
