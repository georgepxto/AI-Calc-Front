"""Ícones desenhados à mão: sol, lua, relógio e o ícone do app."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap


def paint_sun(painter: QPainter, rect: QRectF, color: QColor) -> None:
    center = rect.center()
    unit = min(rect.width(), rect.height()) / 64
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(center, 12 * unit, 12 * unit)
    painter.setPen(QPen(color, 5 * unit, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for step in range(8):
        angle = step * math.pi / 4
        dx, dy = math.cos(angle), math.sin(angle)
        painter.drawLine(
            center + QPointF(dx * 19 * unit, dy * 19 * unit),
            center + QPointF(dx * 27 * unit, dy * 27 * unit),
        )


def paint_moon(painter: QPainter, rect: QRectF, color: QColor) -> None:
    unit = min(rect.width(), rect.height()) / 64
    left, top = rect.center().x() - 32 * unit, rect.center().y() - 32 * unit
    full = QPainterPath()
    full.addEllipse(QRectF(left + 10 * unit, top + 10 * unit, 44 * unit, 44 * unit))
    bite = QPainterPath()
    bite.addEllipse(QRectF(left + 24 * unit, top + 2 * unit, 40 * unit, 40 * unit))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(full.subtracted(bite))


def paint_sidebar(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Janela com barra lateral (ícone do histórico, como no macOS)."""
    unit = min(rect.width(), rect.height()) / 64
    center = rect.center()
    pen = QPen(color, 4.5 * unit, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    box = QRectF(center.x() - 26 * unit, center.y() - 20 * unit, 52 * unit, 40 * unit)
    painter.drawRoundedRect(box, 8 * unit, 8 * unit)
    x = box.left() + 19 * unit
    painter.drawLine(QPointF(x, box.top()), QPointF(x, box.bottom()))


def paint_trash(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Lixeira (limpar histórico)."""
    unit = min(rect.width(), rect.height()) / 64
    c = rect.center()
    pen = QPen(color, 4.5 * unit, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawLine(QPointF(c.x() - 22 * unit, c.y() - 14 * unit), QPointF(c.x() + 22 * unit, c.y() - 14 * unit))
    painter.drawLine(QPointF(c.x() - 8 * unit, c.y() - 14 * unit), QPointF(c.x() - 8 * unit, c.y() - 21 * unit))
    painter.drawLine(QPointF(c.x() - 8 * unit, c.y() - 21 * unit), QPointF(c.x() + 8 * unit, c.y() - 21 * unit))
    painter.drawLine(QPointF(c.x() + 8 * unit, c.y() - 21 * unit), QPointF(c.x() + 8 * unit, c.y() - 14 * unit))
    body = QPainterPath()
    body.moveTo(c.x() - 16 * unit, c.y() - 14 * unit)
    body.lineTo(c.x() - 13 * unit, c.y() + 22 * unit)
    body.lineTo(c.x() + 13 * unit, c.y() + 22 * unit)
    body.lineTo(c.x() + 16 * unit, c.y() - 14 * unit)
    painter.drawPath(body)
    for dx in (-5, 5):
        painter.drawLine(QPointF(c.x() + dx * unit, c.y() - 5 * unit), QPointF(c.x() + dx * unit, c.y() + 13 * unit))


def paint_chevron(painter: QPainter, rect: QRectF, color: QColor) -> None:
    """Seta para baixo (abre a lista de modos)."""
    unit = min(rect.width(), rect.height()) / 64
    c = rect.center()
    pen = QPen(color, 6 * unit, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline([QPointF(c.x() - 14 * unit, c.y() - 7 * unit), QPointF(c.x(), c.y() + 7 * unit),
                          QPointF(c.x() + 14 * unit, c.y() - 7 * unit)])


def paint_app_icon(painter: QPainter, size: int) -> None:
    """Ícone do AI Calc: uma calculadora cujo visor mostra a onda do seno.

    Corpo em degradê roxo → turquesa (as cores do app), visor escuro com a curva em âmbar
    e teclas claras, com a tecla "=" em âmbar. Em tamanhos pequenos, menos teclas.
    """
    s = float(size)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Corpo da calculadora.
    body = QRectF(s * 0.10, s * 0.03, s * 0.80, s * 0.94)
    gradient = QLinearGradient(body.topLeft(), body.bottomRight())
    gradient.setColorAt(0.0, QColor("#5B47C8"))
    gradient.setColorAt(1.0, QColor("#1FA89B"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawRoundedRect(body, s * 0.14, s * 0.14)
    painter.setPen(QPen(QColor(255, 255, 255, 90), max(1.0, s * 0.015)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(body.adjusted(s * 0.01, s * 0.01, -s * 0.01, -s * 0.01), s * 0.13, s * 0.13)

    # Visor com a onda do seno (um período inteiro).
    screen = QRectF(body.left() + s * 0.08, body.top() + s * 0.08, body.width() - s * 0.16, s * 0.30)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#0E1A33"))
    painter.drawRoundedRect(screen, s * 0.05, s * 0.05)
    middle = screen.center().y()
    inner = screen.adjusted(s * 0.05, 0, -s * 0.05, 0)
    if size >= 32:
        painter.setPen(QPen(QColor(255, 255, 255, 70), max(1.0, s * 0.012)))
        painter.drawLine(QPointF(inner.left(), middle), QPointF(inner.right(), middle))
    amplitude = screen.height() * 0.30
    wave = QPainterPath(QPointF(inner.left(), middle))
    steps = 48
    for step in range(1, steps + 1):
        t = step / steps
        wave.lineTo(QPointF(inner.left() + inner.width() * t, middle - amplitude * math.sin(2 * math.pi * t)))
    painter.setPen(QPen(QColor("#FFD166"), max(1.3, s * 0.04), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawPath(wave)

    # Teclas: 3 × 3 (2 × 2 nos ícones pequenos); a última é o "=" em âmbar.
    columns = rows = 3 if size >= 32 else 2
    area = QRectF(screen.left(), screen.bottom() + s * 0.07, screen.width(), body.bottom() - screen.bottom() - s * 0.15)
    gap = s * 0.05 if size >= 32 else s * 0.08
    key_w = (area.width() - gap * (columns - 1)) / columns
    key_h = (area.height() - gap * (rows - 1)) / rows
    painter.setPen(Qt.PenStyle.NoPen)
    for row in range(rows):
        for column in range(columns):
            last = row == rows - 1 and column == columns - 1
            painter.setBrush(QColor("#FFD166") if last else QColor(255, 255, 255, 225))
            key = QRectF(area.left() + column * (key_w + gap), area.top() + row * (key_h + gap), key_w, key_h)
            painter.drawRoundedRect(key, s * 0.035, s * 0.035)


ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def app_icon() -> QIcon:
    """QIcon com o ícone desenhado em vários tamanhos (barra de tarefas, janela, Alt+Tab)."""
    icon = QIcon()
    for size in ICON_SIZES:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        paint_app_icon(painter, size)
        painter.end()
        icon.addPixmap(pixmap)
    return icon
