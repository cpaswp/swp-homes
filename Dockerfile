FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Build the exact static-file manifest used by production. The build-only key
# is never used by the running application.
RUN DJANGO_ENV=production DJANGO_SECRET_KEY=build-only-not-a-runtime-secret python manage.py collectstatic --noinput

EXPOSE 8000
# Respect the hosting platform's assigned port while keeping local Docker easy.
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 60"]
