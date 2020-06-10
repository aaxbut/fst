import aiohttp.web

from config import settings

from apps.filesearch import views, models

app = aiohttp.web.Application()


app.add_subapp('/files/', views.file_search)


async def db_engine(app):
    app.engine = models.db.connect()
    models.db.create_tables([models.FilesModel, models.FilesIndex])
    models.db.execute_sql('''
            CREATE TRIGGER IF NOT EXISTS filesmodel_insert AFTER INSERT ON filesmodel BEGIN
                INSERT INTO filesindex(rowid, title, description, path) VALUES (new.id, new.title, new.description, new.path);
            END;
   ''')
    models.db.execute_sql('''CREATE TRIGGER IF NOT EXISTS files_model_delete AFTER DELETE ON filesmodel BEGIN
                DELETE FROM filesindex WHERE rowid=old.id;
            END;
    ''')
    models.db.execute_sql('''CREATE TRIGGER IF NOT EXISTS filesmodel_update AFTER UPDATE ON filesmodel BEGIN
                DELETE FROM filesindex WHERE rowid=old.id;
                INSERT INTO filesindex(rowid, title, description, path) VALUES (new.id, new.title, new.description, new.path);
            END;
    ''')
    yield
    models.db.close()


app.cleanup_ctx.append(db_engine)


aiohttp.web.run_app(app, port=settings.SERVER_API_PORT)
