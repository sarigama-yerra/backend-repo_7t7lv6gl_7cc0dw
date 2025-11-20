import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI(title="UNBEQUEM/BEQUEM Site Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Backend running", "services": ["/api/youtube/channel_stats?handle=@handle_or_id"]}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/api/youtube/channel_stats")
def youtube_channel_stats(
    handle: str | None = Query(default=None, description="YouTube channel handle, e.g. @UNBEQUEM-o2w"),
    id: str | None = Query(default=None, description="YouTube channel ID, e.g. UC..."),
):
    """
    Returns live subscriber statistics for a YouTube channel via YouTube Data API v3.
    Provide either `handle` (preferred) or `id`.

    Requires env var YOUTUBE_API_KEY to be set.
    """
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return {
            "status": "unconfigured",
            "message": "YOUTUBE_API_KEY not set on server",
            "subscriberCount": None,
            "viewCount": None,
            "videoCount": None,
            "channelId": id,
            "handle": handle,
        }

    if not handle and not id:
        raise HTTPException(status_code=400, detail="Provide either 'handle' or 'id'")

    params = {
        "part": "statistics,snippet,customUrl",
        "key": api_key,
    }

    # Prefer handle lookup if provided
    if handle:
        # YouTube API supports forHandle param to resolve a channel by handle
        params_with_handle = params | {"forHandle": handle}
        url = "https://www.googleapis.com/youtube/v3/channels"
        r = requests.get(url, params=params_with_handle, timeout=10)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text[:200])
        data = r.json()
        if not data.get("items"):
            # Fallback: try as ID if a handle didn't resolve
            if handle.startswith("UC"):
                id = handle
            else:
                raise HTTPException(status_code=404, detail="Channel not found for handle")
        else:
            item = data["items"][0]
            stats = item.get("statistics", {})
            return {
                "status": "ok",
                "channelId": item.get("id"),
                "title": item.get("snippet", {}).get("title"),
                "subscriberCount": int(stats.get("subscriberCount", 0)) if stats.get("subscriberCount") is not None else None,
                "viewCount": int(stats.get("viewCount", 0)) if stats.get("viewCount") is not None else None,
                "videoCount": int(stats.get("videoCount", 0)) if stats.get("videoCount") is not None else None,
            }

    # ID path
    if id:
        url = "https://www.googleapis.com/youtube/v3/channels"
        params_with_id = params | {"id": id}
        r = requests.get(url, params=params_with_id, timeout=10)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text[:200])
        data = r.json()
        if not data.get("items"):
            raise HTTPException(status_code=404, detail="Channel not found for id")
        item = data["items"][0]
        stats = item.get("statistics", {})
        return {
            "status": "ok",
            "channelId": item.get("id"),
            "title": item.get("snippet", {}).get("title"),
            "subscriberCount": int(stats.get("subscriberCount", 0)) if stats.get("subscriberCount") is not None else None,
            "viewCount": int(stats.get("viewCount", 0)) if stats.get("viewCount") is not None else None,
            "videoCount": int(stats.get("videoCount", 0)) if stats.get("videoCount") is not None else None,
        }

    raise HTTPException(status_code=400, detail="Invalid request")


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        # Try to import database module
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
