from flask import Flask, request, make_response
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import datetime
import os
from jellyfin import Jellyfin
from tmdb import Tmdb
from db import RequestsDB

app = Flask(__name__)

jellyfin = Jellyfin(os.getenv("JELLYFIN_HOST"), os.getenv("JELLYFIN_API_KEY"))
tmdb = Tmdb(os.getenv("TMDB_API_KEY"), os.getenv("TMDB_LANGUAGE"), os.getenv("TMDB_COUNTRY"))
db = RequestsDB()

@app.route("/api/v3/system/status")
def get_status():
    return {}

@app.route("/api/v3/qualityProfile")
def get_quality_profiles():
    return [{
        "id": 1234,
        "name": "Default"
    }]

@app.route("/api/v3/rootfolder")
def get_root_folder():
    return [{
        "id": "1234",
        "path": "/default"
    }]

@app.route("/api/v3/tag")
def get_tags():
    return []

@app.route("/api/v3/command", methods=["POST"])
def run_command():
    # accept any command, do nothing, return success
    print(f"received command: {request.json}")
    return make_response('', 200)

@app.route("/api/v3/queue")
def get_queue():
    # return requests as 'queued', local media as 'completed'
    movie_requests = [{"id": request["id"], "movieId": request["tmdbId"], "title": request["title"], "status": "queued"} for request in db.get_movie_requests()]
    movie_requests += [{"id": movie["tmdbId"], "movieId": movie["tmdbId"], "title": movie["title"], "status": "completed"} for movie in jellyfin.get_local_movies()]
    return {
        "page": 0,
        "pageSize": len(movie_requests),
        "totalRecords": len(movie_requests),
        "records": movie_requests
    }

@app.route("/api/v3/movie", methods=["GET", "PUT", "POST"])
def movies():
    if request.method == "GET":
        # local files + scheduled recordings + epg + requested movies
        return jellyfin.get_movies() + db.get_movie_requests()
    else:
        print(f"POST/PUT movie: {request.json}")
        # add request to db or update existing request by tmdbId
        return db.upsert_movie_request(request.json)

@app.route("/api/v3/movie/lookup")
def get_movie_lookup():
    term = request.args.get('term')
    if term.startswith("tmdb:"):
        # check existing requests
        movie_request = db.get_movie_request_by_tmdbid(term[5:])
        if movie_request is not None:
            return movie_request
        # fetch tmdb data if id has been requested
        tmdb_movie = tmdb.get_by_id(term[5:])
        titles = [tmdb_movie["title"], tmdb_movie["originalTitle"]]
    
        # check local files, scheduled recordings & epg for requested title
        for movie in jellyfin.get_local_movies():
            if movie["title"] in titles or ("originalTitle" in movie and movie["originalTitle"] in titles):
                print(f"Found movie: {movie}")
                movie["tags"] = []
                movie["id"] = term[5:]
                movie["tmdbId"] = term[5:]
                return [movie]

        # return tmdb data, clients can then send a request
        tmdb_movie["hasFile"] = False
        tmdb_movie["monitored"] = False
        tmdb_movie["tags"] = []
        return [tmdb_movie]

    # nothing found
    return make_response('[]', 404)

@app.route("/api/v3/movie/<id>", methods=["DELETE"])
def delete_movie(id):
    # delete request by id
    db.delete_request(id)
    print(f"Deleted request for tmdb id {id}")
    return make_response('', 200)


# check scheduled recordings, schedule recordings for requested media if found in epg data
def check_scheduled_recordings():
    requests = db.get_movie_requests()
    if not requests:
        print("No requests")
        return

    local_media = [int(movie["tmdbId"]) for movie in jellyfin.get_local_movies()]
    scheduled_movies = jellyfin.get_scheduled_movies()
    scheduled_movie_titles = [movie["title"] for movie in scheduled_movies]
    epg_data = jellyfin.get_movies_from_epg()

    for request in requests:
        # load all alternative titles for the requested movie
        request_titles = []
        try:
            request_titles = tmdb.get_titles_by_id(request["tmdbId"])
        except ValueError as e:
            print(f"Error while fetching alternate titles: {e}")
        request_titles.append(request["title"])
        request_titles.append(request["originalTitle"])
        print(request_titles)

        if int(request["tmdbId"]) in local_media:
            print(f"Local media found for {request["title"]}. Deleting request.")
            db.delete_request(request["tmdbId"])
        elif len(list(filter(lambda x: x in scheduled_movie_titles, request_titles))) > 0:
            print(f"Found existing scheduled recording for '{request["title"]}'")
        else:
            scheduled = False
            schedule_conflicts = 0
            for epg_movie in epg_data:
                if scheduled:
                    break
                if epg_movie["title"] in request_titles:
                    schedule_conflict = False
                    start = datetime.datetime.fromisoformat(epg_movie["StartDate"])
                    end = datetime.datetime.fromisoformat(epg_movie["EndDate"])
                    # check all scheduled recordings to prevent concurrent recordings
                    for scheduled_movie in scheduled_movies:
                        schedule_start = datetime.datetime.fromisoformat(scheduled_movie["StartDate"])
                        schedule_end = datetime.datetime.fromisoformat(scheduled_movie["EndDate"])
                        if (start >= schedule_start and start <= schedule_end) or (end >= schedule_start and end <= schedule_end) or (start <= schedule_start and end >= schedule_end):
                            print(f"Not scheduling '{request["title"]}' at {start}. Conflicting with recording of '{scheduled_movie["title"]}' at {schedule_start}")
                            schedule_conflict = True
                            schedule_conflicts += 1
                    if not schedule_conflict:
                        print(f"Scheduling recording for '{request["title"]}' ('{epg_movie["title"]}')")
                        jellyfin.schedule_movie_recording(epg_movie["id"])
                        scheduled_movies.append(epg_movie)
                        scheduled_movie_titles.append(epg_movie["title"])
                        scheduled = True
            if not scheduled and schedule_conflicts == 0:
                print(f"'{request["title"]}' not scheduled. No match found in epg.")


scheduler = BackgroundScheduler()
scheduler.add_job(func=check_scheduled_recordings, trigger="interval", seconds=300)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


if __name__ == "__main__":
    app.run("0.0.0.0")
