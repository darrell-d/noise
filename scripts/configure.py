import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
env_file = root / '.env'
if not env_file.exists():
    env_file.write_text((root / '.env.example').read_text())
    env_file.chmod(0o600)
if not os.getenv('SECRET_KEY'):
    from dotenv import dotenv_values, set_key
    if not dotenv_values(env_file).get('SECRET_KEY'):
        set_key(env_file, 'SECRET_KEY', secrets.token_urlsafe(64))
