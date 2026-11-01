"""Public atlas, using the same headless native rules as the desktop release."""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import timedelta
import gzip
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import threading
import time

from django.conf import settings
from django.db import OperationalError, transaction
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from app.core.io_util import atomic_write_bytes
from app.core.worldmap.atlas import atlas_data
from app.core.worldmap.engine import Components, MapSolver
from app.core.worldmap.model import validate_seed
from app.core.worldmap.routes import RoutePlanner
from .models import SeedUploadBudget
from hub.version import VERSION

logger = logging.getLogger(__name__)
DISPLAY_SCHEMA = 'atlas-1:'+VERSION


class QuotaExceeded(ValueError):
    pass


def solver():
    root = Path(os.environ.get('BBMOD_WORLDMAP_HOME', '/srv/worldmap'))
    if root.is_dir():
        components = Components(root/('worldmap.exe' if os.name == 'nt' else 'worldmap'), root/'runtime.nut', root/'rules')
    else:
        components = Components.locate()
    return MapSolver(components, settings.DATA_DIR/'worldmap-cache'/'native')


@contextmanager
def compute_slot():
    """One expensive computation at a time; OS releases the lock after a crash."""
    directory = settings.DATA_DIR/'worldmap-cache'
    directory.mkdir(parents=True, exist_ok=True)
    with (directory/'compute.lock').open('a+b') as handle:
        acquired = False
        try:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                if not handle.read(1):
                    handle.write(b'0'); handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except (BlockingIOError, OSError):
            pass
        try:
            yield acquired
        finally:
            if acquired:
                if os.name == 'nt':
                    handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def quota(request, operation):
    now = timezone.now()
    ip = request.META.get('REMOTE_ADDR', '')
    if settings.TRUST_PROXY:
        ip = request.META.get('HTTP_X_REAL_IP', ip)
    limits = (20, 100) if operation == 'solve' else (180, 1200)
    with transaction.atomic():
        SeedUploadBudget.objects.filter(since__lt=now-timedelta(days=2)).delete()
        for scope, limit in zip(('ip:'+ip, 'global'), limits):
            token = f'worldmap:{operation}:{now:%Y%m%d%H}:{scope}'
            key = hmac.new(settings.SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()
            SeedUploadBudget.objects.get_or_create(key=key)
            if not SeedUploadBudget.objects.filter(key=key, count__lt=limit).update(count=F('count')+1):
                raise QuotaExceeded('本小时解算次数较多，请稍后再试；已经解算的地图仍可查看。')


def display_cache(service, seed):
    key = hashlib.sha256((DISPLAY_SCHEMA+service.components.fingerprint()+seed).encode()).hexdigest()
    return settings.DATA_DIR/'worldmap-cache'/'display'/(key+'.json.gz')


def cached_display(path):
    try:
        data = json.loads(gzip.decompress(path.read_bytes()))
        if data.get('schema') == 1:
            return data
    except (OSError, EOFError, ValueError, TypeError):
        pass
    return None


def prune_cache():
    # Only disposable files produced by this service, never the site's other data.
    directory = settings.DATA_DIR/'worldmap-cache'
    files = sorted([*directory.rglob('*.json.gz'), *directory.rglob('*.error.json')], key=lambda p: p.stat().st_mtime)
    size = sum(p.stat().st_size for p in files)
    while files and (len(files) > 512 or size > 128*1024*1024):
        path = files.pop(0)
        size -= path.stat().st_size
        path.unlink(missing_ok=True)


def busy():
    response = JsonResponse({'status': 'busy', 'message': '地图或路线正在解算，请稍候。'}, status=202)
    response['Retry-After'] = '3'
    return response


def computation_error(path):
    try:
        error = json.loads(path.with_suffix('.error.json').read_bytes())
        if time.time()-error['time'] < 60:
            return JsonResponse({'message': error['message']}, status=error['status'])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def background_work(work, path, lease, operation):
    try:
        value = work()
        atomic_write_bytes(path, gzip.compress(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()))
        path.with_suffix('.error.json').unlink(missing_ok=True)
        prune_cache()
    except Exception as error:
        if operation == 'route' and isinstance(error, ValueError):
            status, message = 400, str(error)
        else:
            logger.exception('Atlas computation failed')
            status = 504 if isinstance(error, TimeoutError) else 503
            message = '这次解算超时，请稍后重试。' if status == 504 else '地图或路线解算暂时不可用，请稍后重试。'
        atomic_write_bytes(path.with_suffix('.error.json'), json.dumps(dict(time=time.time(), status=status, message=message)).encode())
        prune_cache()
    finally:
        lease.__exit__(None, None, None)


def computed_response(request, path, operation, work):
    value = cached_display(path)
    if value is not None:
        response = JsonResponse(value)
        response['Cache-Control'] = 'no-cache'
        return response
    failure = computation_error(path)
    if failure is not None:
        return failure
    lease = compute_slot()
    if not lease.__enter__():
        lease.__exit__(None, None, None)
        return busy()
    value = cached_display(path)
    if value is not None:
        lease.__exit__(None, None, None)
        return JsonResponse(value)
    # Keep the OS lease alive in the worker until the native child is reaped.
    try:
        quota(request, operation)
        if getattr(settings, 'WORLDMAP_ASYNC', True):
            threading.Thread(target=background_work, args=(work, path, lease, operation), daemon=True).start()
        else:
            background_work(work, path, lease, operation)
            return computation_error(path) or JsonResponse(cached_display(path))
    except Exception:
        lease.__exit__(None, None, None)
        raise
    return busy()


@require_GET
@ensure_csrf_cookie
def atlas(request):
    seed = request.GET.get('seed', '46U2HMOORH')[:32]
    return render(request, 'seed_atlas.html', {'seed_code': seed, 'track_visit': True})


@require_GET
def map_data(request, seed):
    try:
        seed = validate_seed(seed)
    except ValueError as error:
        return JsonResponse({'message': str(error)}, status=400)
    try:
        service = solver()
        path = display_cache(service, seed)
        def work():
            result = service.solve(seed, include_camps=True, timeout=150)
            data = atlas_data(result.world)
            data['generation_seconds'] = round(result.elapsed, 3)
            return data
        return computed_response(request, path, 'solve', work)
    except QuotaExceeded as error:
        return JsonResponse({'message': str(error)}, status=429)
    except TimeoutError:
        return JsonResponse({'message': '这次地图解算超时，请稍后重试。'}, status=504)
    except (ValueError, OSError, RuntimeError, OperationalError):
        logger.exception('Atlas solver unavailable')
        return JsonResponse({'message': '地图解算暂时不可用，请稍后重试。'}, status=503)


@require_POST
def route_data(request, seed):
    try:
        seed = validate_seed(seed)
        if int(request.META.get('CONTENT_LENGTH') or 0) > 4096:
            raise ValueError('路线请求过大。')
        data = json.loads(request.body)
        stops = data['stops']
        road_only = data.get('road_only', False)
        if (not isinstance(stops, list) or len(stops) > 12 or any(type(i) is not int or not 0 <= i < 40 for i in stops)
                or type(road_only) is not bool):
            raise ValueError('请选择至多十二个有效城镇。')
    except (ValueError, KeyError, TypeError, AttributeError):
        return JsonResponse({'message': '路线参数有误，请重新选择城镇。'}, status=400)
    try:
        service = solver()
        if cached_display(display_cache(service, seed)) is None:
            return JsonResponse({'message': '请先解算这张地图。'}, status=409)
        key = hashlib.sha256((DISPLAY_SCHEMA+service.components.fingerprint()+seed+json.dumps([stops, road_only])).encode()).hexdigest()
        path = settings.DATA_DIR/'worldmap-cache'/'routes'/(key+'.json.gz')
        def work():
            world = service.solve(seed, include_camps=True, timeout=150).world
            result = asdict(RoutePlanner(world).plan(stops, road_only=road_only))
            return dict(schema=1, **result)
        return computed_response(request, path, 'route', work)
    except QuotaExceeded as error:
        return JsonResponse({'message': str(error)}, status=429)
    except ValueError as error:
        return JsonResponse({'message': str(error)}, status=400)
    except (OSError, RuntimeError, OperationalError, TimeoutError):
        logger.exception('Atlas route unavailable')
        return JsonResponse({'message': '路线计算暂时不可用，请稍后重试。'}, status=503)
