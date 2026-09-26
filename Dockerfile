FROM python:3.12-slim

# Do not write .pyc files; flush logs immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Run as a non-root user for better security
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Use Python for the health check because slim images have no curl
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Gunicorn is a production-grade server, unlike Flask's built-in dev server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]