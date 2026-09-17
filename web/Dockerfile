FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BBMOD_DATA_DIR=/srv/data
WORKDIR /srv/web
COPY web/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home bbmod
COPY app/core/archive_safety.py /srv/app/core/archive_safety.py
COPY web /srv/web
RUN BBMOD_DEBUG=1 python manage.py collectstatic --noinput && mkdir -p /srv/data && chown -R bbmod:bbmod /srv/data
USER bbmod
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')"
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn hub.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 180 --access-logfile - --error-logfile -"]
