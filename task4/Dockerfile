FROM python:3.12-slim

# Do not write .pyc files; flush logs immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY reminder.py .

# Run as a non-root user for better security
RUN useradd --create-home appuser
USER appuser

# Reports are written here; mount a host folder to keep them after the container exits
VOLUME ["/data"]

ENTRYPOINT ["python", "reminder.py"]