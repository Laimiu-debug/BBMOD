# Selective overlay: preserve unrelated production code and persistent volumes.
ARG BASE_IMAGE=bbmod-hub:0.4.0
FROM ${BASE_IMAGE} AS compiler
USER root
RUN apt-get update && apt-get install -y --no-install-recommends g++ && rm -rf /var/lib/apt/lists/*
COPY native /build/native
WORKDIR /build/native
RUN g++ -std=c++17 -O2 -DNDEBUG -DBBMOD_SQ32 -DSQ_ALIGNMENT=8 -fpermissive -Wno-cast-function-type -static -Ivendor/include -Ivendor/squirrel runtime.cpp vendor/squirrel/*.cpp vendor/sqstdlib/*.cpp -o /build/worldmap

FROM ${BASE_IMAGE}
USER root
COPY --from=compiler /build/worldmap /srv/worldmap/worldmap
COPY worldmap /srv/worldmap
COPY patch /srv
WORKDIR /srv/web
RUN chmod 755 /srv/worldmap/worldmap && BBMOD_DEBUG=1 python manage.py check && BBMOD_DEBUG=1 python manage.py collectstatic --clear --noinput
USER bbmod
