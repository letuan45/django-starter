# syntax=docker/dockerfile:1

# `slim` is Debian with the build toolchain stripped out: ~120MB instead of ~1GB.
# It is enough here because every dependency ships a prebuilt wheel.
FROM python:3.13-slim

# PYTHONUNBUFFERED  — stdout goes straight to `docker compose logs`.
#                     Without it, Python buffers output and logs arrive late,
#                     or not at all when the container is killed.
# PYTHONDONTWRITEBYTECODE — no .pyc files. The source is bind-mounted from the
#                     host, so cached bytecode would be written onto your disk
#                     for no benefit.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies are installed BEFORE any source code is referenced.
# Docker caches one layer per instruction and reuses a layer when its inputs
# are unchanged. Because requirements.txt changes rarely and source code
# changes constantly, this ordering keeps `pip install` out of every rebuild.
# Reverse the two and every edit to a .py file would reinstall Django.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# NOTE: the application source is deliberately NOT copied into the image.
# docker-compose.yml bind-mounts the project directory over /app instead, so an
# edit on the host is visible in the container immediately — no rebuild.
# A production image does the exact opposite: `COPY . .`, no mount, gunicorn.

EXPOSE 8000

# 0.0.0.0, not 127.0.0.1.
# Inside the container, 127.0.0.1 means "this container only" — the published
# port on the host would connect to nothing. Binding 0.0.0.0 listens on every
# interface the container has, which is what makes `ports:` work.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
