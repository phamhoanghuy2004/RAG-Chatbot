# ==============================
# Python Image
# ==============================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ==============================
# System packages
# ==============================
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# ==============================
# Create non-root user
# ==============================
RUN useradd -m -u 1000 user

WORKDIR /app

# ==============================
# Install Python packages
# ==============================
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================
# Copy source
# ==============================
COPY . .

RUN chown -R user:user /app

USER user

# ==============================
# Django
# ==============================
EXPOSE 8000

CMD ["sh","-c","python manage.py migrate && python manage.py collectstatic --noinput && gunicorn RAGchatbot.wsgi:application --bind 0.0.0.0:8000 --workers=2 --timeout=300"]