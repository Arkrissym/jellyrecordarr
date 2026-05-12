import sqlite3

class RequestsDB:
    def __init__(self):
        self.con = sqlite3.connect("/data/requests.sqlite", check_same_thread=False)
        cursor = self.con.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS requests(tmdb_id PRIMARY KEY, title NOT NULL, original_title NOT NULL, type NOT NULL)")
        self.con.commit()
        cursor.close()

    def get_movie_requests(self):
        cursor = self.con.cursor()
        result = []
        for request in cursor.execute("SELECT tmdb_id, title, original_title FROM requests WHERE type='movie'").fetchall():
            result.append({"id": request[0], "title": request[1], "originalTitle": request[2], "tmdbId": request[0], "hasFile": False, "monitored": True})
        cursor.close()
        return result

    def get_movie_request_by_tmdbid(self, tmdb_id: str):
        cursor = self.con.cursor()
        result = cursor.execute("SELECT tmdb_id, title, original_title FROM requests WHERE type='movie' and tmdb_id=?", (tmdb_id,)).fetchone()
        cursor.close()
        return {"id": result[0], "title": result[1], "originalTitle": result[2], "tmdbId": result[0], "hasFile": False, "monitored": True} if result is not None else None

    def upsert_movie_request(self, request: dict):
        cursor = self.con.cursor()
        existing_request = cursor.execute("SELECT tmdb_id FROM requests WHERE type='movie' and tmdb_id=?", (request["tmdbId"],)).fetchone()
        
        if existing_request is None:        
            cursor.execute("INSERT INTO requests (tmdb_id, title, original_title, type) VALUES(?, ?, ?, 'movie')", (request["tmdbId"], request["title"], request["originalTitle"] if "originalTitle" in request else request["title"]))
        else:
            cursor.execute("UPDATE requests SET title=?, original_title=? WHERE tmdb_id=?", (request["title"], request["originalTitle"], existing_request[0]))

        self.con.commit()
        cursor.close()

        return self.get_movie_request_by_tmdbid(request["tmdbId"])

    def delete_request(self, id: str):
        cursor = self.con.cursor()
        cursor.execute("DELETE FROM requests WHERE tmdb_id=?", (int(id),))
        self.con.commit()
        cursor.close()
