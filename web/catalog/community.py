"""Credited community works in the existing MOD catalogue; no remote archive proxy."""
import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_GET


@lru_cache(maxsize=1)
def community_data():
    return json.loads((Path(settings.BASE_DIR) / 'content/community-mods.json').read_text(encoding='utf-8'))


def catalogue_items(releases):
    releases = list(releases)
    hosted_sources = {r.metadata.get('source_url') for r in releases if r.metadata.get('source_url')}
    aliases = {r['published_mod_id']: r['english_name'] for r in community_data()['mods'] if r.get('published_mod_id')}
    source_aliases = {r['source_url']: r['english_name'] for r in community_data()['mods']}
    items = [dict(metadata={**r.metadata, 'english_name': aliases.get(str(r.mod_id), source_aliases.get(r.metadata.get('source_url'), ''))}, url=reverse('detail', args=[r.mod_id]),
                  cover_url=reverse('cover', args=[r.id]) if r.cover else '',
                  version=r.version, created_at=r.created_at, source_kind='hosted') for r in releases]
    # Curated hosted works use the normal release visibility rules; never resurrect
    # withdrawn, blocked or draft works as a source-only duplicate.
    for row in community_data()['mods']:
        if row.get('published_mod_id'):
            continue
        if row['source_url'] in hosted_sources:
            continue
        items.append(dict(metadata=row, url=reverse('community_detail', args=[row['slug']]),
                          source_kind='original', version='', cover_url=''))
    return items


def requirement_labels(mod_ids):
    known = {r['mod_id']: r for r in community_data()['mods'] if r.get('mod_id')}
    labels = []
    for value in mod_ids:
        row = known.get(value)
        if row is None:
            labels.append(dict(label=value, url=''))
        else:
            url = (reverse('detail', args=[row['published_mod_id']]) if row.get('published_mod_id')
                   else reverse('community_detail', args=[row['slug']]))
            labels.append(dict(label=row['title'], url=url))
    return labels


@require_GET
def detail(request, slug):
    row = next((r for r in community_data()['mods'] if r['slug'] == slug and not r.get('published_mod_id')), None)
    if row is None:
        raise Http404
    from .services import public_releases
    hosted = public_releases().filter(metadata__source_url=row['source_url']).first()
    if hosted is not None:
        return redirect('detail', mod_id=hosted.mod_id)
    return render(request, 'community_detail.html', {'mod': row, 'track_visit': True})
