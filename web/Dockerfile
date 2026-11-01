FROM python:3.12-slim-bookworm AS map-builder
RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*
COPY app/build/offline-map/vendor /build/vendor
COPY app/native/worldmap/runtime.cpp /build/runtime.cpp
WORKDIR /build
RUN g++ -std=c++17 -O2 -DNDEBUG -DBBMOD_SQ32 -DSQ_ALIGNMENT=8 -fpermissive -Wno-cast-function-type -static -Ivendor/include -Ivendor/squirrel runtime.cpp vendor/squirrel/*.cpp vendor/sqstdlib/*.cpp -o /build/worldmap

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BBMOD_DATA_DIR=/srv/data
WORKDIR /srv/web
COPY web/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home bbmod
COPY app/core/archive_safety.py /srv/app/core/archive_safety.py
COPY app/core/profile_protocol.py /srv/app/core/profile_protocol.py
COPY app/core/save_protocol.py /srv/app/core/save_protocol.py
COPY app/core/paths.py app/core/gamelog.py /srv/app/core/
COPY app/core/modinfo.py app/core/l10n_identity.py /srv/app/core/
COPY app/core/item_inspector.py /srv/app/core/item_inspector.py
COPY app/core/io_util.py /srv/app/core/io_util.py
COPY app/core/worldmap /srv/app/core/worldmap
COPY app/core/seedgen/weapon_rating.py /srv/app/core/seedgen/weapon_rating.py
COPY app/core/seedgen/config_emitter.py app/core/seedgen/log_watcher.py app/core/seedgen/presentation.py app/core/seedgen/brother_rating.py app/core/seedgen/protocol.py app/core/seedgen/traits.py app/core/seedgen/weapons.py app/core/seedgen/mod_origins.py /srv/app/core/seedgen/
COPY app/data/seed_traits.json /srv/app/data/seed_traits.json
COPY app/data/item_inspector/catalog.json /srv/app/data/item_inspector/catalog.json
COPY app/build/offline-map/web-labels.json /srv/app/data/worldmap/labels.json
COPY --from=map-builder /build/worldmap /srv/worldmap/worldmap
COPY app/build/offline-map/package/runtime.nut app/build/offline-map/package/camps.nut /srv/worldmap/
COPY app/build/offline-map/package/SQUIRREL-COPYRIGHT /srv/worldmap/SQUIRREL-COPYRIGHT
COPY app/build/offline-map/package/rules /srv/worldmap/rules
COPY app/tests/fixtures/worldmap /srv/app/tests/fixtures/worldmap
COPY web /srv/web
RUN BBMOD_DEBUG=1 python manage.py check && BBMOD_DEBUG=1 python manage.py collectstatic --noinput && mkdir -p /srv/data /srv/desktop && chown -R bbmod:bbmod /srv/data /srv/desktop
USER bbmod
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://localhost:8000/health/', headers={'X-Forwarded-Proto': 'https'}))"]
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn hub.wsgi:application --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 180 --access-logfile - --error-logfile -"]
