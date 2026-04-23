from __future__ import annotations

from io import BytesIO

from PIL import Image
from PyQt6.QtGui import QImage, QPixmap


def pil_to_qimage(pil_image: Image.Image) -> QImage:
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    data = pil_image.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
    return qimg.copy()


def pil_to_qpixmap(pil_image: Image.Image) -> QPixmap:
    return QPixmap.fromImage(pil_to_qimage(pil_image))


def qimage_to_pil(qimage: QImage) -> Image.Image:
    qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
    buffer = qimage.constBits()
    buffer.setsize(qimage.sizeInBytes())
    return Image.frombytes(
        "RGBA",
        (qimage.width(), qimage.height()),
        bytes(buffer),
    )


def qimage_to_png_bytes(qimage: QImage) -> bytes:
    from PyQt6.QtCore import QBuffer, QByteArray, QIODeviceBase

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODeviceBase.OpenModeFlag.WriteOnly)
    qimage.save(buf, "PNG")
    buf.close()
    return bytes(ba)
