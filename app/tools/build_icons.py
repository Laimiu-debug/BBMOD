"""Package the painted crest as the multi-resolution Windows application icon."""
import io
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QGuiApplication, QImage, QPainter


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication([])
    assets = Path(__file__).resolve().parents[1] / "assets"
    canvas = QImage(256, 256, QImage.Format_ARGB32)
    canvas.fill(0)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.drawImage(canvas.rect(), QImage(str(assets / "crest-painted.png")))
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    canvas.save(buffer, "PNG")
    picture = Image.open(io.BytesIO(bytes(buffer.data())))
    picture.save(assets / "bbmod.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    canvas.save(str(assets / "bbmod.png"))
    print(assets / "bbmod.ico")


if __name__ == "__main__":
    main()
