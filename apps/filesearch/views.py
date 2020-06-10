import json
import aiohttp.web_response
from apps.filesearch.models import FilesIndex
from apps.filesearch.scheme import FileSerializer, Files

from apps.utils import create_search_string

file_search = aiohttp.web.Application()


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


file_search.add_routes(
        [
            aiohttp.web.get('/files-list', files),
        ]
)
