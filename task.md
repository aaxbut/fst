# Задача:

Необходимо реализовать сервис позволяющий осуществить поиск по базе данных(sqlite) по полям `title` и `description` текст может быть как на русском так и на английском, ответ сервиса должен содержать набор подходящих запросу данных `title`, `description` и `path` с учетом морфологии, сервис должен иметь возможность горизонтального масштабирования.

## Подготовительная часть, инструменты, библиотеки, рассуждение…

## Инструменты:


В документации sqlite есть расширение позволяющее производить полнотекстовый поиск([SQLite FTS5 Extension](https://www.sqlite.org/fts5.html), 
так же было бы неплохо использовать ORM для запросов к базе данных, нам подойдёт [peewee](http://docs.peewee-orm.com/en/latest/index.html) так как там уже реализована модель 
[FTS5Model](http://docs.peewee-orm.com/en/latest/peewee/sqlite_ext.html?highlight=FTS5Model#FTS5Model), и для предварительной обработки строки поиска нам понадобится модуль
 [pystemmer](https://github.com/snowballstem/pystemmer/) позволяющий удалить общие морфологические и инфлексивные окончания из слов на русском и английском языке, 
 pystemmer не ограничивается русским и английским, дополнительно можно почитать [тут](https://snowballstem.org/), 
 Что можно придумать для возможности масштабирования, самый просто наверно вариант использовать [nginx balancer](https://docs.nginx.com/nginx/admin-guide/load-balancer/tcp-udp-load-balancer/:))

Подготовка виртуального окружения, для виртуального окружение использую [pyenv](https://github.com/pyenv/pyenv), очень удобная штука.
```pyenv virtualenv 3.7.3 ya```
```pyenv local ya```

В первую очередь нужно проверить включено ли дополнение `FTS5`:

```python
from playhouse.sqlite_ext import FTS5Model
FTS5Model.fts5_installed()
```

Если расширение не установлено, будет выполнена попытка скачать расширение, но если и она завершиться неудачей, нужно будет
переустановить sqlite включив расширение ([Можно использовать докер, а можно и в систему установить](https://stackoverflow.com/a/49288829).

Так как у нас уже есть таблица в которую вводятся данные через админку, надо немного прокачать нашу базу данных, читать будем из fst5 таблицы, её нужно создать:
Если расширение не установлено, будет выполнена попытка скачать расширение, но если и она завершиться неудачей, нужно будет переустановить sqlite включив расширение(Можно использовать докер, а можно и в систему установить).


Для использования расширения, необходимо создать дополнительную виртуальную таблицу, отнаследованную от класса `FTS5Model`.

```python

from playhouse.sqlite_ext import SqliteExtDatabase
from playhouse.sqlite_ext import FTS5Model, Model, CharField, TextField


db = SqliteExtDatabase('my_app.db', pragmas=(
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
db.create_tables([FilesModel, FilesIndex], True) # создаст таблицу если она отсутствует
```

Для автоматической поддержки актуальности в виртуальной таблице, в базе создадим тригире на `INSERT`, `UPDATE` и `DELETE` события.
Для выполнения инструкций можно воспользоватьяся sqlite консолькой

```console

sqlite> open my_app.db
```

Далее в этой же консоли пыполнить команды создания триггеров, или выполнить данные скрипты при старте приложения
используя ```db.execute_sql```
```SQL
-- -- Create a table. And an external content fts5 table to index it.
-- CREATE TABLE tbl(a INTEGER PRIMARY KEY, b, c);
-- CREATE VIRTUAL TABLE fts_idx USING fts5(b, c, content='tbl', content_rowid='a');

-- Triggers to keep the FTS index up to date.
CREATE TRIGGER IF NOT EXISTS filesmodel_insert AFTER INSERT ON filesmodel BEGIN
  INSERT INTO filesindex(rowid, title, description, path) VALUES (new.id, new.title, new.description, new.path);
END;

CREATE TRIGGER IF NOT EXISTS files_model_delete AFTER DELETE ON filesmodel BEGIN
  DELETE FROM filesindex WHERE rowid=old.id;
END;
CREATE TRIGGER IF NOT EXISTS filesmodel_update AFTER UPDATE ON filesmodel BEGIN
  DELETE FROM filesindex WHERE rowid=old.id;
  INSERT INTO filesindex(rowid, title, description, path) VALUES (new.id, new.title, new.description, new.path);
END;
```

Теперь при вводе в основную таблицу дополнительно заполняется fts табличка.

Ну а теперь поиск)

Предварительно будем обрабатывать поисковую строку, что бы быть уверенным что в поисковой запрос, ничего лишнего не попадёт, 
используя [pystemmer](https://github.com/snowballstem/pystemmer)(перед установкой нужно что бы был установлен модуль `pip install cython`) документация [тут](https://github.com/snowballstem/pystemmer/blob/master/docs/quickstart.txt), и да чуть не забыл)))
в задаче указанно, что запросы могут быть на русском и на английском, и для того что бы определить какой использовать стеммер, будем проверять
каких букв больше в слове кирилицы или латинских(Попробуйте найти альтернативные решения) попробуйте библиотеки [polyglot](https://github.com/aboSamoor/polyglot) 
и [langdetect](https://github.com/Mimino666/langdetect), 
и тех кого больше будем пропускать через стаммер.


Устанавливаем

```shell
pip install pystemmer
```

Сделаем функцию предварительной обработки поисковой строки:

```python
import unicodedata as ud

import Stemmer


def create_search_string(search):
    english = Stemmer.Stemmer('english')
    russian = Stemmer.Stemmer('russian')
    select_stammer = {'en': english, 'ru': russian}
    words = []
    if not search:
        return ''
    rus = []
    eng = []
    for word in search.split():
        for letter in word:
            if 'CYRILLIC' in ud.name(letter):
                rus.append(letter)
            else:
                eng.append(letter)
        if len(rus) > len(eng):
            stemmer = select_stammer.get('ru')
        else:
            stemmer = select_stammer.get('en')
        if stemmer:
            words.append(stemmer.stemWord(word))
    return ' '.join(words) if words else ''
```

Теперь когда на наш эндпоинт придёт запрос у нас есть чем предварительно обработать, попробуйте придумать альтернативный вариант решения, или как можно улучшить обработку.

Для того что был подготовленный ответ от эндпоинта используем [pydantic](https://pydantic-docs.helpmanual.io/) простой, лёгкий инструмент сериализации.
Подготовим 2 модели, одна будет содержать элемент ответа, а вторая будет содержать элементы ответов.

```python

from pydantic.utils import GetterDict
from typing import List, Any


class PeeweeGetterDict(GetterDict):
    def get(self, key: Any, default: Any = None):
        res = getattr(self._obj, key, default)
        if isinstance(res, peewee.ModelSelect):
            return list(res)
        return res


class FileSerializer(BaseModel):
    title: str
    description: str
    path: str

    class Config:
        orm_mode = True
        getter_dict = PeeweeGetterDict


class Files(BaseModel):
    items: List[FilesSerializer]
```

Далее сделаем нужен эндпоинт который бы принимал поисковую строку и формировал ответ, будем использовать aiohttp.

```python
async def files(request):
    search_string = request.rel_url.query.get('search_string')
    prepared_search_string = create_search_string(search_string)
    prepared_response = []

    if prepared_search_string:
        result = FilesIndex.search(
            prepared_search_string
        ).execute()
        for item in result:
            prepared_response.append(FileSerializer.from_orm(item))
        return aiohttp.web_response.Response(
            body=Files(items=prepared_response).json(ensure_ascii=False),
            content_type='application/json',
            charset='utf-8'
        )

    if not prepared_search_string:
        return aiohttp.web_response.Response(
            body=json.dumps({}),
            content_type='application/json'
        )
```
Обрадите внимание на подготовку ответа, ```Files(items=prepared_response).json(ensure_ascii=False)``` так как по используется кодировка `utf-8`
кирилица будет отображаться как то так 

```json 
    {"title": "\u0417\u0430\u0433\u043e\u043b\u043e\u0432\u043e\u043a", "description": "Description", "path": "path\to"}
```

Запускаем приложение ```python main.py``` и проверяем что у нас получилось.
Добавим записей в таблицу

```python
FilesModel.create(title='Заголовок', description='Description', path='path\to')
FilesModel.create(title='Title', description='Description', path='path\to')         
```

```http request
   http://0.0.0.0:8000/files/files-list?search_string=title
```

если ответ от эндпоинта будет:
```json
{"items": [{"title": "Title", "description": "Description", "path": "path\to"}]}
``` 
значит всё получилось, напишите тесты проверяющие работу запроса, для подготовки данных можно воспользоваться
[factoryboy](https://factoryboy.readthedocs.io/en/latest/) для создания записей.
