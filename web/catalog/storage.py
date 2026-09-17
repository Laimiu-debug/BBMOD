from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class DesktopStorage(FileSystemStorage):
    """Separate, non-public storage for administrator-published EXE files."""
    @property
    def base_location(self):
        return settings.DESKTOP_DOWNLOAD_ROOT

    @property
    def location(self):
        return str(Path(self.base_location).resolve())
