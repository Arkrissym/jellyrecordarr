import requests
from cachetools import cached, TTLCache
import datetime

class Jellyfin:
    def __init__(self, jellyfin_host: str, token: str):
        self.jellyfin_host = jellyfin_host
        self.token = f'MediaBrowser Token="{token}"'

    @cached(cache=TTLCache(maxsize=1, ttl=60))
    def get_movies(self):
        result = self.get_local_movies()
        titles = [r["title"] for r in result]

        for scheduled_movie in self.get_scheduled_movies():
            if scheduled_movie["title"] not in titles:
                result.append(scheduled_movie)
                titles.append(scheduled_movie["title"])

        for epg_movie in self.get_movies_from_epg():
            if epg_movie["title"] not in titles:
                result.append(epg_movie)
                titles.append(epg_movie["title"])

        return result


    # local files
    def get_local_movies(self):
        return self.get_local_media("movie")

    def get_local_series(self):
        return self.get_local_media("series")

    @cached(cache=TTLCache(maxsize=2, ttl=60))
    def get_local_media(self, media_type: str):
        params = {"IncludeItemTypes": media_type, "Recursive": True, "enableImages": False, "fields": "OriginalTitle,ProviderIds", "hasTmdbId": True}
        result = requests.get(self.jellyfin_host + "/Items", params, headers={"Authorization": self.token})
        if result.status_code != 200:
            raise ValueError(result.content)
        data = result.json()
        print(f"local media contains {data["TotalRecordCount"]} items of type {media_type}")
        return [{"id": item["Id"], "title": item["Name"], "originalTitle": item["OriginalTitle"] if "OriginalTitle" in item else item["Name"], "tmdbId": item["ProviderIds"]["Tmdb"], "status": "downloading" if "Status" in item and item["Status"] == "InProgress" else "completed", "hasFile": True, "monitored": False} for item in data["Items"]]


    # EPG data
    def get_movies_from_epg(self):
        return self.get_epg(False)

    def get_series_from_epg(self):
        return self.get_epg(True)

    @cached(cache=TTLCache(maxsize=2, ttl=1800))
    def get_epg(self, series: bool):
        result = requests.get(self.jellyfin_host + "/LiveTv/Programs", {"isSeries": series, "minStartDate": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}, headers={"Authorization": self.token})
        if result.status_code != 200:
            raise ValueError(result.content)
        data = result.json()
        print(f"EPG returned {data["TotalRecordCount"]} items (series: {series})")
        return [{"id": item["Id"], "title": item["Name"], "StartDate": item["StartDate"], "EndDate": item["EndDate"], "hasFile": False, "monitored": False} for item in data["Items"]]


    # scheduled recordins
    @cached(cache=TTLCache(maxsize=1, ttl=60))
    def get_scheduled_movies(self):
        result = requests.get(self.jellyfin_host + "/LiveTv/Timers", {"isActive": True}, headers={"Authorization": self.token})
        if result.status_code != 200:
            raise ValueError(result.content)
        data = result.json()
        print(f"Jellyfin returned {data["TotalRecordCount"]} active recordings")
        active_movies = data["Items"]

        result = requests.get(self.jellyfin_host + "/LiveTv/Timers", {"isScheduled": True}, headers={"Authorization": self.token})
        if result.status_code != 200:
            raise ValueError(result.content)
        data = result.json()
        print(f"Jellyfin returned {data["TotalRecordCount"]} scheduled recordings")
        scheduled_movies = data["Items"]

        movies = filter(lambda m: "IsSeries" not in m["ProgramInfo"] or not m["ProgramInfo"]["IsSeries"], active_movies + scheduled_movies)
        return [{"id": item["Id"], "title": item["Name"], "StartDate": item["StartDate"], "EndDate": item["EndDate"], "hasFile": False, "monitored": True} for item in movies]


    def schedule_movie_recording(self, id: str):
        data = {"ProgramId": id,
                "ServiceName": "Emby",
                "PrePaddingSeconds": 0,
                "PostPaddingSeconds": 300,
                "KeepUntil":"UntilDeleted"
                }
        result = requests.post(self.jellyfin_host + "/LiveTv/Timers", json=data, headers={"Authorization": self.token, "Content-Type": "application/json"})
        if result.status_code != 204:
            raise ValueError(result.content)

    def create_series_timer(self, id: str, name: str):
        data = {"RecordAnyTime":true,
                "SkipEpisodesInLibrary":true,
                "RecordAnyChannel":true,
                "RecordNewOnly":false,
                "ProgramId": id,
                "Name": name,
                "ServiceName":"Emby",
                "PrePaddingSeconds":0,
                "PostPaddingSeconds":300,
                "KeepUntil":"UntilDeleted"
                }
        result = requests.post(self.jellyfin_host + "/LiveTv/SeriesTimers", json=data, headers={"Authorization": self.token, "Content-Type": "application/json"})
        if result.status_code != 204:
            raise ValueError(result.content)
