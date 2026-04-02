FROM python:3.11-slim

WORKDIR /app

# Copy server deps first (layer cache)
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy the server entry point and all Python backend modules it depends on
COPY server/main.py ./server/main.py
COPY part_registry.py coherence_validator.py localization.py \
     extraction_protocols.py mystery_generator.py ./
COPY mystery_database/ ./mystery_database/

ENV PYTHONUNBUFFERED=1

# ANTHROPIC_API_KEY must be injected at runtime (env var or secret manager)
# Never bake it into the image.
EXPOSE 8000

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
