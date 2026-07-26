import requests
import datetime
import os
import pymongo
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import ORJSONResponse, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

from src import chesstools_ui
from src.scraper import fide_scraper
from src.scraper.fide_scraper import FIDEServiceError
from src.scraper.ratinglists import db as ratings_db
from src.scraper.ratinglists.updater import update_all_rating_lists, update_cfc_rating_list, update_fide_rating_list

# Load environment variables
load_dotenv()

# Helper function to get GA tracking ID
def get_ga_tracking_id():
    return os.getenv("GA_TRACKING_ID", "G-JSFHZ4X5YL")

# Google Analytics Middleware
class GoogleAnalyticsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, ga_tracking_id: str = None):
        super().__init__(app)
        self.ga_tracking_id = ga_tracking_id or os.getenv("GA_TRACKING_ID", "G-JSFHZ4X5YL")
        
    async def dispatch(self, request: Request, call_next):
        # Track the request start time
        start_time = datetime.datetime.now()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (datetime.datetime.now() - start_time).total_seconds()
        
        # Log API usage (you can extend this to send to GA4 via Measurement Protocol)
        if (
            not request.url.path.startswith("/static")
            and not request.url.path.startswith("/favicon")
            and not request.url.path.startswith("/chesstools-ui")
        ):
            print(f"API Request: {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        return response

app = FastAPI(
    title=os.getenv("API_TITLE", "Chess Ratings API"),
    version=os.getenv("API_VERSION", "2.0.0"),
    description=os.getenv("API_DESCRIPTION", "Highly reliable, free, chess ratings API for FIDE, CFC, and other rating systems."),
    default_response_class=ORJSONResponse,
    docs_url=None,  # Disable default docs to use custom template
    redoc_url=None
)

# Add Google Analytics middleware
app.add_middleware(GoogleAnalyticsMiddleware)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.mount(
    "/chesstools-ui",
    StaticFiles(directory=str(chesstools_ui.static_dir())),
    name="chesstools_ui",
)


# Custom docs endpoint with Google Analytics
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    ga_id = get_ga_tracking_id()
    nav = chesstools_ui.nav_html()
    footer = chesstools_ui.footer_html()
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{ga_id}');
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chess Ratings API - ChessTools</title>
    <link type="text/css" rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.25.3/swagger-ui.css">
    <link rel="icon" href="https://chesstools.org/chesstools.svg" type="image/svg+xml" sizes="any">
    <link rel="stylesheet" href="/chesstools-ui/theme.css">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="/chesstools-ui/tailwind-shell.js"></script>
</head>
<body class="bg-background text-foreground antialiased flex min-h-screen flex-col">
{nav}
<main class="flex-1">
<div class="container mx-auto px-4 py-8">
<div class="bg-card rounded-lg shadow-sm border border-border p-6 mb-6">
<h1 class="text-3xl font-bold text-foreground mb-2">Chess Ratings API Documentation</h1>
<p class="text-muted-foreground">Highly reliable, free, chess ratings API for FIDE, CFC, and other rating systems.</p>
</div>
<div id="swagger-ui" class="bg-card rounded-lg shadow-sm border border-border"></div>
</div>
</main>
{footer}
<script src="/chesstools-ui/shell.js" defer></script>
<script src="https://unpkg.com/swagger-ui-dist@5.25.3/swagger-ui-bundle.js"></script>
<script src="https://unpkg.com/swagger-ui-dist@5.25.3/swagger-ui-standalone-preset.js"></script>
<script>
SwaggerUIBundle({{
  url: '/openapi.json',
  dom_id: '#swagger-ui',
  presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
  layout: "StandaloneLayout",
  deepLinking: true,
  showExtensions: true,
  showCommonExtensions: true
}});
gtag('event', 'page_view', {{
  page_title: 'Chess Ratings API - Documentation',
  page_location: window.location.href
}});
</script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

# Custom landing HTML with Google Analytics embedded
@app.get("/", include_in_schema=False)
def home():
    ga_id = get_ga_tracking_id()
    nav = chesstools_ui.nav_html()
    footer = chesstools_ui.footer_html()
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{ga_id}');
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="https://chesstools.org/chesstools.svg" type="image/svg+xml" sizes="any">
    <title>Chess Ratings API - ChessTools</title>
    <meta name="description" content="Highly reliable, free, chess ratings API for FIDE, CFC, and other rating systems.">
    <link rel="stylesheet" href="/chesstools-ui/theme.css">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="/chesstools-ui/tailwind-shell.js"></script>
</head>
<body class="bg-background text-foreground antialiased flex min-h-screen flex-col">
{nav}
<main class="flex-1">

        <!-- Hero Section -->
        <section class="relative overflow-hidden bg-gradient-to-b from-primary/10 to-background py-20">
            <div class="container mx-auto px-4 relative z-10">
                <div class="text-center max-w-4xl mx-auto">
                    <h1 class="text-4xl md:text-6xl font-bold text-foreground mb-6">
                        Chess Ratings API
                    </h1>
                    <p class="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
                        Highly reliable, free, chess ratings API for FIDE, CFC, and other rating systems. 
                        Access comprehensive chess player ratings data through our RESTful API.
                    </p>
                    <div class="flex flex-col sm:flex-row gap-4 justify-center">
                        <a href="/docs" class="bg-primary text-primary-foreground hover:bg-primary/90 px-8 py-3 rounded-lg font-semibold transition-colors inline-flex items-center gap-2">
                            📚 API Documentation
                        </a>
                        <a href="/health" class="bg-secondary text-secondary-foreground hover:bg-secondary/90 px-8 py-3 rounded-lg font-semibold transition-colors inline-flex items-center gap-2">
                            🔍 Health Check
                        </a>
                    </div>
                </div>
            </div>
        </section>

        <!-- Features Section -->
        <section class="py-20 bg-background">
            <div class="container mx-auto px-4">
                <div class="text-center mb-12">
                    <h2 class="text-3xl font-bold text-foreground mb-4">API Features</h2>
                    <p class="text-muted-foreground max-w-2xl mx-auto">
                        Access comprehensive chess ratings data with our reliable and fast API
                    </p>
                </div>
                
                <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                    <div class="bg-card border border-border rounded-lg p-6">
                        <div class="h-12 w-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <span class="text-2xl">🏆</span>
                        </div>
                        <h3 class="text-xl font-semibold text-foreground mb-3">FIDE Ratings</h3>
                        <p class="text-muted-foreground">Get top active players, detailed player information, and rating history from FIDE's official data.</p>
                    </div>
                    
                    <div class="bg-card border border-border rounded-lg p-6">
                        <div class="h-12 w-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <span class="text-2xl">🇨🇦</span>
                        </div>
                        <h3 class="text-xl font-semibold text-foreground mb-3">CFC Ratings</h3>
                        <p class="text-muted-foreground">Access Canadian chess ratings data with search capabilities and comprehensive player information.</p>
                    </div>
                    
                    <div class="bg-card border border-border rounded-lg p-6">
                        <div class="h-12 w-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <span class="text-2xl">🇺🇸</span>
                        </div>
                        <h3 class="text-xl font-semibold text-foreground mb-3">USCF Ratings</h3>
                        <p class="text-muted-foreground">Query US Chess Federation ratings with fast lookups and detailed player statistics.</p>
                    </div>
                    
                    <div class="bg-card border border-border rounded-lg p-6">
                        <div class="h-12 w-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <span class="text-2xl">⚡</span>
                        </div>
                        <h3 class="text-xl font-semibold text-foreground mb-3">Fast & Reliable</h3>
                        <p class="text-muted-foreground">Redis caching and MongoDB integration ensure quick responses and high availability.</p>
                    </div>
                    
                    <div class="bg-card border border-border rounded-lg p-6">
                        <div class="h-12 w-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <span class="text-2xl">🔍</span>
                        </div>
                        <h3 class="text-xl font-semibold text-foreground mb-3">Search Players</h3>
                        <p class="text-muted-foreground">Find players by name across all rating systems with powerful search capabilities.</p>
                    </div>
                    
                    <div class="bg-card border border-border rounded-lg p-6">
                        <div class="h-12 w-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                            <span class="text-2xl">📊</span>
                        </div>
                        <h3 class="text-xl font-semibold text-foreground mb-3">Health Monitoring</h3>
                        <p class="text-muted-foreground">Real-time system status and health checks to ensure optimal API performance.</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- CTA Section -->
        <section class="py-20 bg-primary/5">
            <div class="container mx-auto px-4 text-center">
                <h2 class="text-3xl font-bold text-foreground mb-4">Ready to Get Started?</h2>
                <p class="text-muted-foreground mb-8 max-w-2xl mx-auto">
                    Explore our comprehensive API documentation and start integrating chess ratings data into your applications today.
                </p>
                <div class="flex flex-col sm:flex-row gap-4 justify-center">
                    <a href="/docs" class="bg-primary text-primary-foreground hover:bg-primary/90 px-8 py-3 rounded-lg font-semibold transition-colors">
                        View API Documentation
                    </a>
                    <a href="https://chesstools.org" class="bg-secondary text-secondary-foreground hover:bg-secondary/90 px-8 py-3 rounded-lg font-semibold transition-colors">
                        Explore ChessTools
                    </a>
                </div>
            </div>
        </section>

</main>
{footer}
<script src="/chesstools-ui/shell.js" defer></script>
<script>
gtag('event', 'page_view', {{
  page_title: 'Chess Ratings API - ChessTools',
  page_location: window.location.href
}});
</script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.get("/fide/top_active/", tags=["FIDE"])
async def top_players(limit: int = 100, history: bool = False):
    try:
        response = fide_scraper.get_top_players(limit=limit, history=history)
        return response
    except FIDEServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))

# FIDE endpoints
@app.get("/fide/top_by_rating", tags=["FIDE"])
async def get_top_fide_players(limit: int = 100):
  """Get top rated FIDE players from the rating list database."""
  return ratings_db.get_top_rated_fide(limit)

@app.get("/fide/player_history/", tags=["FIDE"])
async def player_history(fide_id: str):
    try:
        response = fide_scraper.get_player_history(fide_id=fide_id)
        return response
    except FIDEServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/fide/{player_id}", tags=["FIDE"])
async def get_fide_player_rating(player_id: str):
  """Get a FIDE player's rating data from the rating list database."""
  player = ratings_db.get_fide_player(player_id)
  if not player:
    raise HTTPException(status_code=404, detail="Player not found")
  return player


@app.get("/fide/player_info/", tags=["FIDE"])
async def player_info(fide_id: str, history: bool = False):
    try:
        response = fide_scraper.get_player_info(fide_id=fide_id, history=history)
        return response
    except FIDEServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/cfc/top_by_rating", tags=["CFC"])
async def get_top_cfc_players(limit: int = 100):
  """Get top rated CFC players from the rating list database."""
  return ratings_db.get_top_rated_cfc(limit)

@app.get("/cfc/{player_id}", tags=["CFC"])
async def get_cfc_player_rating(player_id: str):
  """Get a CFC player's rating data from the rating list database."""
  player = ratings_db.get_cfc_player(player_id)
  if not player:
    raise HTTPException(status_code=404, detail="Player not found")
  return player

@app.get("/uscf/top_by_rating", tags=["USCF"])
async def get_top_uscf_players(limit: int = 100):
  """Get top rated USCF players from the rating list database."""
  return ratings_db.get_top_rated_uscf(limit)

@app.get("/uscf/{player_id}", tags=["USCF"])
async def get_uscf_player_rating(player_id: int):
  """Get a USCF player's rating data from the rating list database."""
  player = ratings_db.get_uscf_player(player_id)
  if not player:
    raise HTTPException(status_code=404, detail="Player not found")
  return player

@app.get("/ratinglist/search", tags=["All"])
async def search_players(query: str, list_type: str = "fide"):
  """Search for players by name in either FIDE or CFC rating lists."""
  if list_type.lower() not in ["fide", "cfc"]:
    raise HTTPException(status_code=400, detail="list_type must be 'fide' or 'cfc'")
  
  results = ratings_db.search_player(query, list_type)
  return results

@app.get("/ratinglist/metadata", tags=["All"])
async def get_rating_lists_metadata():
  """Get metadata about the rating lists (last update, etc.)"""
  return ratings_db.get_rating_list_metadata()

# @app.post("/update", tags=["System"])
# async def trigger_rating_lists_update(background_tasks: BackgroundTasks):
#   """Trigger an update of the rating lists (admin only)"""
#   # In a production environment, you would add authentication here
  
#   # Run update in the background to avoid blocking the request
#   background_tasks.add_task(update_all_rating_lists)
  
#   return {"status": "update_started", "message": "Rating list update has been started in the background"}

# @app.post("/ratinglist/reset", tags=["System"])
# async def reset_rating_lists_db(background_tasks: BackgroundTasks):
#     """Reset the rating lists database collections (admin only)"""
#     # In a production environment, you would add authentication here
    
#     from src.scraper.ratinglists.db import reset_collections
    
#     success = reset_collections()
#     if not success:
#         raise HTTPException(status_code=500, detail="Failed to reset rating lists database")
    
#     # Start a background task to reinitialize the database
#     background_tasks.add_task(update_all_rating_lists)
    
#     return {"status": "reset_completed", "message": "Rating lists database has been reset and reinitialization started"}

@app.get("/health", tags=["All"])
async def health_check():
    """Health check endpoint for monitoring the API status"""
    health_status = {
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0",
        "services": {}
    }
    
    # Check Redis connection
    try:
        from src.scraper.cache import redis_client
        redis_info = redis_client.info()
        health_status["services"]["redis"] = {
            "status": "ok",
            "version": redis_info.get("redis_version", "unknown")
        }
    except Exception as e:
        health_status["services"]["redis"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check MongoDB connection
    try:
        mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
        mongo_client = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        server_info = mongo_client.server_info()
        fide_count = ratings_db.fide_collection.count_documents({})
        cfc_count = ratings_db.cfc_collection.count_documents({})
        uscf_count = ratings_db.uscf_collection.count_documents({})
        
        health_status["services"]["mongodb"] = {
            "status": "ok",
            "version": server_info.get("version", "unknown"),
            "fide_players": fide_count,
            "cfc_players": cfc_count,
            "uscf_players": uscf_count
        }
    except Exception as e:
        health_status["services"]["mongodb"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Get rating list last refresh dates from metadata
    try:
        metadata = ratings_db.get_rating_list_metadata()
        if metadata:
            rating_lists_status = {}
            
            # FIDE last update
            if "fide_last_updated" in metadata:
                rating_lists_status["fide_last_refreshed"] = metadata["fide_last_updated"]
            
            # CFC last update  
            if "cfc_last_updated" in metadata:
                rating_lists_status["cfc_last_refreshed"] = metadata["cfc_last_updated"]
                
            # USCF last update
            if "uscf_last_updated" in metadata:
                rating_lists_status["uscf_last_refreshed"] = metadata["uscf_last_updated"]
            
            if rating_lists_status:
                health_status["rating_lists"] = rating_lists_status
                
    except Exception as e:
        health_status["rating_lists"] = {
            "status": "error",
            "error": f"Could not retrieve metadata: {str(e)}"
        }
    
    # Check FIDE website accessibility for the web scraper
    try:
        fide_response = requests.get("https://ratings.fide.com", timeout=5)
        health_status["services"]["fide_website"] = {
            "status": "ok" if fide_response.status_code == 200 else "error",
            "status_code": fide_response.status_code
        }
    except Exception as e:
        health_status["services"]["fide_website"] = {
            "status": "error",
            "error": str(e)
        }
    
    return health_status
