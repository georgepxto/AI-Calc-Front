"""Desenho do "vidro líquido" simulado: degradê, translucidez, reflexos e sombra.

Sem blur real: a superfície é semitransparente sobre um fundo com brilhos de
cor. O efeito de vidro líquido vem dos reflexos: um brilho na metade de cima,
uma borda especular (forte no alto, quase sumindo no meio e voltando de leve
embaixo), um reflexo fino na borda de baixo e uma sombra difusa em camadas.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from .theme import (
    GLINT_ALPHA,
    GLOW_ALPHA,
    HOVER_ALPHA,
    RIM_ALPHA,
    SHADOW_ALPHA,
    SHEEN_ALPHA,
    TOP_TINT,
    ThemeManager,
    mix,
)


def with_alpha(color: QColor | str, alpha: float) -> QColor:
    result = QColor(color)
    result.setAlphaF(max(0.0, min(1.0, alpha)))
    return result


def capsule_radius(rect: QRectF) -> float:
    """Raio que transforma o retângulo numa cápsula (pílula)."""
    return min(rect.width(), rect.height()) / 2


def paint_shadow(painter: QPainter, rect: QRectF, radius: float, theme: ThemeManager) -> None:
    """Sombra difusa: camadas cada vez maiores e mais fracas (imitando um desfoque)."""
    color = theme.hex("shadow")
    for dy, grow, weight in ((1.0, 0.0, 1.0), (2.0, 0.6, 0.45), (3.0, 1.2, 0.2)):
        layer = QPainterPath()
        shifted = rect.translated(0, dy).adjusted(-grow, -grow / 2, grow, grow)
        layer.addRoundedRect(shifted, radius + grow, radius + grow)
        painter.fillPath(layer, with_alpha(color, SHADOW_ALPHA * weight))


def paint_glass(
    painter: QPainter,
    rect: QRectF,
    radius: float,
    theme: ThemeManager,
    fill: str,
    alpha: float,
    hover: float = 0.0,
    shadow: bool = True,
) -> None:
    """Pinta uma superfície de vidro com a cor "fill" (hex) e a opacidade dada."""
    radius = min(radius, capsule_radius(rect))
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)

    if shadow:
        paint_shadow(painter, rect, radius, theme)

    # Corpo: degradê do topo (mais claro) para baixo, semitransparente.
    rim = theme.hex("glass_rim")
    body = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    body.setColorAt(0.0, with_alpha(mix(fill, rim, TOP_TINT), alpha))
    body.setColorAt(1.0, with_alpha(fill, alpha))
    painter.fillPath(path, QBrush(body))

    if hover > 0:
        painter.fillPath(path, with_alpha(rim, HOVER_ALPHA * hover))

    # Brilho na metade de cima.
    sheen = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.top() + rect.height() * 0.5))
    sheen.setColorAt(0.0, with_alpha(rim, SHEEN_ALPHA))
    sheen.setColorAt(1.0, with_alpha(rim, 0.0))
    painter.fillPath(path, QBrush(sheen))

    # Borda especular: forte no alto, discreta no meio, volta de leve embaixo.
    edge = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    edge.setColorAt(0.0, with_alpha(rim, RIM_ALPHA))
    edge.setColorAt(0.35, with_alpha(rim, RIM_ALPHA * 0.25))
    edge.setColorAt(0.65, with_alpha(theme.hex("glass_edge"), 0.30))
    edge.setColorAt(1.0, with_alpha(rim, RIM_ALPHA * 0.45))
    painter.setPen(QPen(QBrush(edge), 1.0))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)

    # Reflexo fino na borda de baixo, como a luz atravessando o vidro.
    inset = max(radius, rect.width() * 0.18)
    if rect.width() > 2 * inset:
        y = rect.bottom() - 1.0
        glint = QLinearGradient(QPointF(rect.left() + inset, y), QPointF(rect.right() - inset, y))
        glint.setColorAt(0.0, with_alpha(rim, 0.0))
        glint.setColorAt(0.5, with_alpha(rim, GLINT_ALPHA))
        glint.setColorAt(1.0, with_alpha(rim, 0.0))
        painter.setPen(QPen(QBrush(glint), 1.0))
        painter.drawLine(QPointF(rect.left() + inset, y), QPointF(rect.right() - inset, y))


def paint_focus_ring(painter: QPainter, rect: QRectF, radius: float, color: QColor) -> None:
    radius = min(radius, capsule_radius(rect))
    painter.setPen(QPen(color, 2.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    inner = rect.adjusted(1.5, 1.5, -1.5, -1.5)
    painter.drawRoundedRect(inner, max(0.0, radius - 1.5), max(0.0, radius - 1.5))


class Backdrop(QWidget):
    """Fundo da janela: degradê neutro com dois brilhos suaves que aparecem através do vidro."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        theme = self._theme

        base = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        base.setColorAt(0.0, theme.color("window_top"))
        base.setColorAt(1.0, theme.color("window_bottom"))
        painter.fillRect(rect, QBrush(base))

        size = max(rect.width(), rect.height())
        for key, cx, cy in (("glow_a", 0.08, 0.15), ("glow_b", 0.95, 0.92)):
            center = QPointF(rect.width() * cx, rect.height() * cy)
            glow = QRadialGradient(center, size * 0.5)
            glow.setColorAt(0.0, with_alpha(theme.hex(key), GLOW_ALPHA))
            glow.setColorAt(1.0, with_alpha(theme.hex(key), 0.0))
            painter.fillRect(rect, QBrush(glow))


def set_text_color(widget: QWidget, color: QColor) -> None:
    """Cor do texto de um QLabel (sem folha de estilo, para acompanhar a transição)."""
    palette = widget.palette()
    palette.setColor(QPalette.ColorRole.WindowText, color)
    widget.setPalette(palette)
