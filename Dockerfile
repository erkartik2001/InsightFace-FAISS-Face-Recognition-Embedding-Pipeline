FROM python:3.10-slim

WORKDIR /app

# Install system dependencies required by OpenCV
RUN apt-get update && apt-get install -y \
    libxcb1 \
    libxrender1 \
    libxext6 \
    libsm6 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .

# Guarantee only the headless OpenCV variant is present at runtime.
RUN pip install --no-cache-dir --no-deps opencv-python-headless==4.9.0.80 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y opencv-python || true && \
    pip install --no-cache-dir --force-reinstall --no-deps opencv-python-headless==4.9.0.80

# Copy application source
COPY . .

# Create required directories
RUN mkdir -p faiss_index temp uploads

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
