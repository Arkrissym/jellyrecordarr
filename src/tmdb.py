import requests
from cachetools import cached, TTLCache

class Tmdb:
    def __init__(self, api_key: str, language: str, country: str):
        self.api_key = api_key
        self.language = language
        self.country = country

    @cached(cache=TTLCache(maxsize=4096, ttl=86400))
    def get_by_id(self, id: str):
        params = {"api_key": self.api_key, "language": self.language}
        result = requests.get("https://api.themoviedb.org/3/movie/" + id, params)
        if result.status_code != 200:
            raise result.content
        data = result.json()
        print(f"Found '{data["title"]}' for id {data["id"]}")
        return {"id": data["id"], "title": data["title"], "originalTitle": data["original_title"], "tmdbId": data["id"]}

    @cached(cache=TTLCache(maxsize=4096, ttl=86400))
    def get_titles_by_id(self, id: str):
        params = {"api_key": self.api_key, "country": self.country}
        result = requests.get("https://api.themoviedb.org/3/movie/" + str(id) + "/alternative_titles", params)
        if result.status_code != 200:
            raise result.content
        data = result.json()
        if not "titles" in data:
            return []
        result = [x["title"] for x in data["titles"]]
        print(f"Found {len(result)} titles for id {data["id"]}")
        return result
