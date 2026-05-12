import requests
from cachetools import cached, LRUCache

class Tmdb:
    def __init__(self, api_key: str, language: str):
        self.api_key = api_key
        self.language = language

    @cached(cache=LRUCache(maxsize=64))
    def get_by_id(self, id: str):
        params = {"api_key": self.api_key, "language": self.language}
        result = requests.get("https://api.themoviedb.org/3/movie/" + id, params)
        if result.status_code != 200:
            raise result.content
        data = result.json()
        print(f"Found '{data["title"]}' for id {data["id"]}")
        return {"id": data["id"], "title": data["title"], "originalTitle": data["original_title"], "tmdbId": data["id"]}
