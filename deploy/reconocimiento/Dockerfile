FROM python:3.11-slim

# Install system dependencies for dlib/face_recognition
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake build-essential libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend source as a package so relative imports resolve
COPY src/backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

COPY src/backend/ ./backend/

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
