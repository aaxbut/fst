import peewee
from pydantic import BaseModel
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
    items: List[FileSerializer]
