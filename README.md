<h1 align="center">
  Chess Ratings API
</h1>

<h4 align="center">Python FIDE scraper for FIDE Ratings, CFC Ratings, and USCF ratings available in a web-based format</h4>

<p align="center">
   <a href="https://api.chesstools.org">Demo</a> •
   <a href="#about">About</a> •
   <a href="#features">Features</a> •
   <a href="#usage">Usage</a> •
   <a href="#credits">Credits</a> •
   <a href="#license">License</a> •
   <a href="https://api.chesstools.org/health">Health</a>
</p>

<p align="center">
   <a href="https://github.com/Hart-House-Chess-Club/ratings-api/actions/workflows/docker-publish.yml">
      <img src="https://github.com/Hart-House-Chess-Club/ratings-api/actions/workflows/docker-publish.yml/badge.svg" alt="Docker Build and Deploy">
   </a>
</p>


![screenshot](docs/chess-ratings-api.png)

## About

Working with FIDE official data is not simple, mainly because they don't have an API. That's the reason I made a simple API with FastAPI to scrape the data from their own website and provide it as JSON over HTTP requests.

Similarly, no publicly available API is currently available for CFC ratings. We aim to change that with this project.

A Redis cache is implemented to provide faster lookups for common use cases. Additionally, the API now includes MongoDB integration for storing and querying FIDE, CFC, and USCF rating lists, with automatic periodic updates. 

A MongoDB server is used for storing the latest FIDE, CFC, and USCF ratings.

The landing page and `/docs` UI ship with vendored ChessTools chrome: **`static/chesstools/`** (CSS/JS served at `/chesstools-ui/…`) and **`templates/chesstools/`** (`nav.html`, `footer.html`). Override with **`CHESSTOOLS_UI_STATIC`**, **`CHESSTOOLS_UI_TEMPLATES`**, or **`RATINGS_API_ROOT`** if needed. Build the Docker image from this repository root (`docker build -t ratings-api .`).

## Features

Check it on:
[https://api.chesstools.org](https://api.chesstools.org)

### Analytics
- Google Analytics integration for tracking API usage
- Comprehensive request logging and monitoring

### FIDE Web Scraping
- Get top active players list
- Get detailed player information
- Get player rating history

### Rating List Database
- Query FIDE rating list data
- Query CFC rating list data
- Query USCF rating list data
- Search for players by name
- View top-rated players
- Health monitoring

For detailed documentation, see:
- [Rating Lists Documentation](docs/rating_lists.md)
- [System Architecture](docs/system_architecture.md)
- [Monitoring Guide](docs/monitoring_guide.md)

## Usage

### Docker (recommended)

You will need docker and docker-compose installed, from your terminal:

```sh
git clone https://github.com/Hart-House-Chess-Club/ratings-api

cd fide-api

docker compose up -d

# Initialize rating lists (this may take some time on first run)
docker exec fide-api /app/initialize_rating_lists.sh

```

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following configuration:

```bash
# Google Analytics Configuration  
GA_TRACKING_ID=G-JSFHZ4X5YL

# API Configuration
API_TITLE=Chess Ratings API
API_VERSION=2.0.0
API_DESCRIPTION=Highly reliable, free, chess ratings API for FIDE, CFC, and other rating systems.

# Optional: GA4 Measurement Protocol API Secret (for advanced server-side tracking)
# GA_API_SECRET=your_measurement_protocol_api_secret_here
```

The Google Analytics integration will automatically track:
- Page views on the home page and API documentation
- API endpoint usage and response times
- User engagement metrics

## Deployment

### Docker Deployment to Linux Server

This project is configured for easy deployment to any Linux server using Docker:

1. **Automated Deployment with GitHub Actions**:
   - The repository includes a GitHub Actions workflow file for CI/CD
   - Each push to the main branch triggers an automatic build and deployment
   - See `.github/workflows/docker-publish.yml` for workflow details
   - See `.github/workflows/update-rating-lists.yml` for updating the rating lists automatically

2. **Manual Deployment**:
   - Use the included `deploy.sh` script:
   ```sh
   ./deploy.sh
   ```
   - This pulls the latest code, builds the Docker image, and restarts all services

3. **Docker Compose Setup**:
   - The `docker-compose.yml` includes:
     - FIDE API service
     - Redis for caching
     - MongoDB for rating list storage

   - Alternative (with MongoDB Atlas): 
   - The `mongo-docker-compose.yml` includes:
      - Cloud-based MongoDB
   

The MongoDB contains rating lists corresponding to respective ratings files such as cfc_ratings for CFC ratings.

![screenshot](docs/mongo.png)


## Credits

Original FIDE-API available from: [fide-api](https://github.com/cassiofb-dev/fide-api/)

## License

MIT

