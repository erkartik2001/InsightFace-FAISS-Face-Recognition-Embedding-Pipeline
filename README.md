# Face Recognition Embedding Pipeline

Core microservice for face recognition, embedding generation, indexing, and face matching.

## Architecture

This service was extracted from the AI Face Recognition CRM to serve as a standalone, independent pipeline service. The CRM calls this service's API for:

- **Indexing**: Download images from B2 buckets → detect faces → generate embeddings → store in FAISS index
- **Matching**: Upload a query image → find matching faces in the FAISS index
- **State Management**: Track indexing progress per-bucket in PostgreSQL

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Service info |
| `GET` | `/health` | Health check |
| `POST` | `/start-indexing` | Start batch indexing (body: `{count, bucket_name?}`) |
| `GET` | `/sync-status` | Poll indexing progress |
| `GET` | `/sync-logs` | Per-bucket sync statistics |
| `GET` | `/indexing-state/{bucket_name}` | Get indexing state for a bucket |
| `POST` | `/search-face` | Upload image, get face matches (multipart form) |
| `GET` | `/index-stats` | FAISS index statistics |

## Project Structure

```
app/
├── main.py                 # FastAPI app + lifespan
├── app_state.py            # Global state
├── database.py             # SQLAlchemy config
├── models.py               # IndexingState ORM model
├── matcher.py              # FaceMatcher (FAISS search)
├── services/
│   ├── face_engine.py      # InsightFace wrapper
│   ├── storage_service.py  # B2 storage
│   └── indexing_service.py # Batch indexing
└── routes/
    ├── indexing_routes.py   # Indexing endpoints
    └── matching_routes.py   # Search & stats endpoints
```

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # Edit with your credentials

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `B2_KEY_ID` | Backblaze B2 key ID |
| `B2_APPLICATION_KEY` | Backblaze B2 application key |
| `B2_BUCKET_NAME` | Default B2 bucket name |
| `DATABASE_URL` | PostgreSQL connection string |
| `PORT` | Service port (default: 8001) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (default: *) |

## Docker

```bash
docker build -t face-pipeline .
docker run -p 8001:8001 --env-file .env face-pipeline
```

## Integration with CRM

The AI Face Recognition CRM calls this service's endpoints instead of running face recognition locally. Example:

```python
# CRM calls pipeline service
import httpx

PIPELINE_URL = "http://localhost:8001"

# Start indexing
response = httpx.post(f"{PIPELINE_URL}/start-indexing", json={
    "count": 100,
    "bucket_name": "my-bucket"
})

# Check status
status = httpx.get(f"{PIPELINE_URL}/sync-status")

# Search face
with open("query.jpg", "rb") as f:
    response = httpx.post(
        f"{PIPELINE_URL}/search-face",
        files={"file": ("query.jpg", f, "image/jpeg")}
    )
```
