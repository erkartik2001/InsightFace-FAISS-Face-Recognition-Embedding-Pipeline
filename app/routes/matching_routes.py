import os
import shutil

from fastapi import APIRouter, UploadFile, File

import app.app_state as app_state

router = APIRouter()


UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================
# SEARCH FACE (upload image, get matches)
# =========================================

@router.post("/search-face")
async def search_face(file: UploadFile = File(...)):
    """
    Upload an image and search for matching faces
    in the FAISS index.
    Called by the CRM service.
    """

    # save uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # search matches
    results = app_state.matcher.search(file_path)

    # cleanup uploaded file
    try:
        os.remove(file_path)
    except OSError:
        pass

    return {
        "success": True,
        "matches": results
    }


# =========================================
# INDEX STATS
# =========================================

@router.get("/index-stats")
def index_stats():
    """
    Return FAISS index statistics.
    """
    m = app_state.matcher

    if m is None:
        return {"success": False, "message": "Matcher not loaded"}

    return {
        "success": True,
        "total_vectors": m.index.ntotal if m.index else 0,
        "total_mappings": len(m.image_mapping)
    }
