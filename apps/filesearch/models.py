from playhouse.sqlite_ext import SqliteExtDatabase
from playhouse.sqlite_ext import FTS5Model, Model, CharField, TextField, SearchField
from config import settings

db = SqliteExtDatabase(settings.DATABASE_FILE, pragmas=(
    ('cache_size', -1024 * 64),  # 64MB page-cache.
    ('journal_mode', 'wal'),  
    ('foreign_keys', 1))
)


class FilesModel(Model):
    title = CharField(max_length=255)
    description = TextField()
    path = TextField()

    class Meta:
        database = db


class FilesIndex(FTS5Model):
    title = SearchField()
    description = SearchField()
    path = SearchField(unindexed=True)

    class Meta:
        database = db
        options = {
            'prefix': [2, 3],
            'tokenize': 'porter unicode61',
        }
