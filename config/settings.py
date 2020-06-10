import pathlib

SERVER_API_PORT = 8000

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / 'my_app.db'
