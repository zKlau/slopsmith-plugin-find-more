"""Find More Songs plugin – search CustomsForge for more songs by an artist."""

import json
import urllib.parse
import urllib.request


def setup(app, context):
    meta_db = context["meta_db"]

    @app.get("/api/plugins/find_more/search")
    def search(query: str, mode: str = "artist"):
        # Fetch songs from RSPlaylist
        url = ("https://rsplaylist.com/api/search.php?search="
               + urllib.parse.quote(query))
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            remote_songs = json.loads(resp.read())

        # Filter based on search mode
        query_lower = query.strip().lower()
        if mode == "song":
            # Search by song title
            remote_songs = [
                s for s in remote_songs
                if query_lower in s.get("title", "").lower()
            ]
        else:
            # Default: search by artist (exact match)
            remote_songs = [
                s for s in remote_songs
                if s.get("artist", "").lower() == query_lower
            ]

        # Get local songs to compare ownership
        local_results = meta_db.conn.execute(
            "SELECT LOWER(title), LOWER(artist) FROM songs"
        ).fetchall()
        local_songs = {(row[0], row[1]) for row in local_results}

        # Build results: mark each remote song as owned or not
        results = []
        for s in remote_songs:
            title_lower = s.get("title", "").lower()
            artist_lower = s.get("artist", "").lower()
            results.append({
                "title": s.get("title", ""),
                "artist": s.get("artist", ""),
                "album": s.get("album", ""),
                "tuning": s.get("tuning_name", ""),
                "paths": s.get("paths_string", ""),
                "creator": s.get("creator", ""),
                "dd": s.get("dd", False),
                "downloads": s.get("downloads", 0),
                "cdlc_id": s.get("cdlc_id"),
                "updated": s.get("updated"),
                "owned": (title_lower, artist_lower) in local_songs,
            })

        # Sort: not-owned first, then by newest updated
        results.sort(key=lambda r: (r["owned"], -(r["updated"] or 0)))

        return {
            "query": query.strip(),
            "mode": mode,
            "total": len(results),
            "owned": sum(1 for r in results if r["owned"]),
            "available": sum(1 for r in results if not r["owned"]),
            "results": results,
        }
