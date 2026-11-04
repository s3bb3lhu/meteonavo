FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 CHROMIUM_EXECUTABLE=/usr/bin/chromium
WORKDIR /studio
LABEL org.opencontainers.image.source="https://github.com/s3bb3lhu/meteonavo" \
      org.opencontainers.image.title="Meteonavo" \
      org.opencontainers.image.licenses="LicenseRef-Meteonavo-Private-Use"
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends chromium ffmpeg && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir --upgrade pip==26.3
# Only source, tests, tools and public documentation belong in the image.
# Runtime volumes, local environment files and deployment backups are never copied.
COPY app/ ./app/
COPY tests/ ./tests/
COPY tools/ ./tools/
COPY deploy/ ./deploy/
COPY *.md LICENSE compose*.yaml .env.example ./
RUN python tools/collect_licenses.py /studio/third-party-licenses
RUN useradd -m -u 10001 studio && mkdir -p /data /hls /media /run/studio && chown -R studio:studio /data /hls /media /run/studio
USER studio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-proxy-headers", "--no-access-log"]


# Export exact Debian corresponding sources separately, never operator data.
FROM runtime AS source-collector
USER root
RUN python -m tools.collect_system_sources /corresponding-sources
FROM scratch AS corresponding-sources
COPY --from=source-collector /corresponding-sources/ /
# The default target is the application, not the source-only export stage.
FROM runtime AS distribution
