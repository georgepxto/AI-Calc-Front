"""Círculo trigonométrico interativo, desenhado com QPainter.

Seno: segmento vertical, linha contínua. Cosseno: segmento horizontal, tracejado.
Tangente: segmento na reta tangente (x = 1), pontilhado. Cada um com cor e rótulo.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAccessible, QAccessibleEvent, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..core.trig import (
    TRIG_FUNCTIONS,
    TrigCircleState,
    angle_from_point,
    angle_text,
    circle_values,
    nearest_notable,
    normalize_degrees,
    quadrant,
)
from ..core.trig_input import describe
from .glass import paint_focus_ring, paint_glass, with_alpha
from .theme import DISPLAY_ALPHA, ThemeManager

PANEL_RADIUS = 16
LABEL_MARGIN = 30       # espaço em volta do círculo para os rótulos
KEY_STEP = 1.0          # setas: 1°
KEY_BIG_STEP = 15.0     # Shift + setas: 15°
QUADRANT_LABEL_RADIUS = 0.64   # distância dos números dos quadrantes ao centro (raio = 1)
QUADRANT_LABEL_GAP = 16.0      # se o raio passar a menos disto (graus), o número se afasta

# (chave da cor na paleta, estilo da linha, rótulo) de cada função.
FUNCTION_STYLES = {
    "sin": ("trig_sin", Qt.PenStyle.SolidLine, "sen"),
    "cos": ("trig_cos", Qt.PenStyle.DashLine, "cos"),
    "tan": ("trig_tan", Qt.PenStyle.DotLine, "tan"),
}


def function_pen(theme: ThemeManager, name: str, width: float = 3.0) -> QPen:
    key, style, _ = FUNCTION_STYLES[name]
    pen = QPen(theme.color(key), width, style, Qt.PenCapStyle.RoundCap)
    return pen


class TrigCircleWidget(QWidget):
    """Arrastar o ponto, clicar no círculo ou usar as setas muda o ângulo."""

    angle_changed = Signal()     # mudou pelo usuário (mouse ou teclado)

    def __init__(
        self,
        theme: ThemeManager,
        state: TrigCircleState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self.state = state
        self.mode = "DEG"
        self._dragging = False
        # Ângulo desenhado: igual ao do estado, ou a caminho dele durante a animação do ponto.
        self.shown_angle = state.angle
        self.visible: frozenset[str] = frozenset(TRIG_FUNCTIONS)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 190)
        self.setAccessibleName("Círculo trigonométrico")
        self.setToolTip("Arraste o ponto ou use as setas (Shift: de 15 em 15 graus)")
        theme.changed.connect(self.update)
        self.refresh()

    def sizeHint(self) -> QSize:  # noqa: N802 (nome do Qt)
        return QSize(300, 300)

    # --- geometria ---
    def _geometry(self) -> tuple[QPointF, float]:
        rect = QRectF(self.rect())
        radius = max(20.0, min(rect.width(), rect.height()) / 2 - LABEL_MARGIN)
        return rect.center(), radius

    def _point(self, center: QPointF, radius: float, x: float, y: float) -> QPointF:
        """Ponto do plano matemático (y para cima, raio 1) na tela."""
        return QPointF(center.x() + radius * x, center.y() - radius * y)

    # --- estado ---
    def refresh(self) -> None:
        """Atualiza o desenho e o resumo para leitor de tela."""
        self.setAccessibleDescription(describe(self.state, self.mode))
        QAccessible.updateAccessibility(QAccessibleEvent(self, QAccessible.Event.DescriptionChanged))
        self.update()

    def set_visible(self, visible: frozenset[str]) -> None:
        self.visible = frozenset(visible)
        self.update()

    def set_shown_angle(self, angle: float) -> None:
        self.shown_angle = normalize_degrees(angle)
        self.update()

    def _set_angle(self, angle: float) -> None:
        # Mouse e setas movem o ponto na hora (sem animação).
        self.state.set_angle(angle)
        self.shown_angle = self.state.angle
        self.refresh()
        self.angle_changed.emit()

    # --- mouse ---
    def _angle_at(self, position: QPointF) -> float | None:
        center, _ = self._geometry()
        return angle_from_point(position.x() - center.x(), center.y() - position.y())

    @staticmethod
    def _mouse_angle(angle: float) -> float:
        """Com o mouse: encaixa no notável próximo; senão, arredonda para grau inteiro."""
        return float(round(nearest_notable(angle))) % 360

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (nome do Qt)
        if event.button() == Qt.MouseButton.LeftButton:
            angle = self._angle_at(event.position())
            if angle is not None:
                self._dragging = True
                self._set_angle(self._mouse_angle(angle))
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (nome do Qt)
        if self._dragging:
            angle = self._angle_at(event.position())
            if angle is not None:
                self._set_angle(self._mouse_angle(angle))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (nome do Qt)
        self._dragging = False
        self.update()
        super().mouseReleaseEvent(event)

    # --- teclado ---
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (nome do Qt)
        step = KEY_BIG_STEP if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else KEY_STEP
        key = event.key()
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Up):
            self._set_angle(self.state.angle + step)
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Down):
            self._set_angle(self.state.angle - step)
        elif key == Qt.Key.Key_Home:
            self._set_angle(0)
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    # --- desenho ---
    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        theme = self._theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel = QRectF(self.rect()).adjusted(1, 1, -1, -3)
        paint_glass(painter, panel, PANEL_RADIUS, theme, theme.hex("display_bg"), DISPLAY_ALPHA)
        painter.setClipRect(panel.adjusted(2, 2, -2, -2))

        center, radius = self._geometry()
        muted = theme.color("text_muted")
        shown = self.shown_angle
        theta = math.radians(shown)
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        _, _, tangent = circle_values(shown)
        tip = self._point(center, radius, cos_t, sin_t)

        # Eixos, círculo e reta tangente (x = 1).
        painter.setPen(QPen(with_alpha(muted, 0.75), 1))
        reach = radius + LABEL_MARGIN - 8
        painter.drawLine(QPointF(center.x() - reach, center.y()), QPointF(center.x() + reach, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - reach), QPointF(center.x(), center.y() + reach))
        tangent_x = center.x() + radius
        painter.setPen(QPen(with_alpha(muted, 0.35), 1))
        painter.drawLine(QPointF(tangent_x, panel.top()), QPointF(tangent_x, panel.bottom()))
        painter.setPen(QPen(muted, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

        # Números dos quadrantes; o atual em destaque.
        current = quadrant(shown)
        small = QFont(self.font())
        small.setPointSize(9)
        for number in range(1, 5):
            spot = self._quadrant_spot(center, radius, number, shown)
            small.setBold(number == current)
            painter.setFont(small)
            painter.setPen(theme.color("text") if number == current else muted)
            painter.drawText(QRectF(spot.x() - 14, spot.y() - 9, 28, 18), Qt.AlignmentFlag.AlignCenter, f"{number}º")

        # Arco do ângulo e o texto do ângulo.
        arc = radius * 0.2
        painter.setPen(QPen(theme.color("icon"), 2))
        painter.drawArc(QRectF(center.x() - arc, center.y() - arc, 2 * arc, 2 * arc), 0, int(shown * 16))

        # Tangente: na reta x = 1, de (1, 0) até (1, tan); o raio é prolongado até lá.
        if tangent is not None and "tan" in self.visible:
            # Tangente enorme (perto de 90°): corta na borda, para não desenhar longe demais.
            limit = panel.height() / radius
            tan_point = self._point(center, radius, 1, max(-limit, min(limit, tangent)))
            painter.setPen(QPen(with_alpha(muted, 0.6), 1, Qt.PenStyle.DashDotLine))
            painter.drawLine(center, tan_point)
            painter.setPen(function_pen(theme, "tan"))
            painter.drawLine(self._point(center, radius, 1, 0), tan_point)
            self._label(painter, "tan", QPointF(tangent_x + 6, (center.y() + tan_point.y()) / 2), "left")

        # Cosseno (horizontal, sobre o eixo x) e seno (vertical, do eixo até o ponto).
        foot = self._point(center, radius, cos_t, 0)
        if "cos" in self.visible:
            painter.setPen(function_pen(theme, "cos"))
            painter.drawLine(center, foot)
            self._label(painter, "cos", QPointF((center.x() + foot.x()) / 2,
                                               center.y() + (14 if sin_t >= 0 else -14)), "center")
        if "sin" in self.visible:
            painter.setPen(function_pen(theme, "sin"))
            painter.drawLine(foot, tip)
            # O rótulo do seno fica sempre à esquerda do segmento: à direita do círculo isso o
            # afasta da reta da tangente; à esquerda, dos números dos quadrantes.
            self._label(painter, "sin", QPointF(foot.x() - 8, (foot.y() + tip.y()) / 2), "right")

        # Raio e ponto que se arrasta.
        painter.setPen(QPen(theme.color("text"), 2))
        painter.drawLine(center, tip)
        dot = 9 if self._dragging else 7
        painter.setPen(QPen(theme.color("display_bg"), 2))
        painter.setBrush(theme.color("icon"))
        painter.drawEllipse(tip, dot, dot)

        # Ângulo escrito perto do arco.
        label_font = QFont(self.font())
        label_font.setPointSize(10)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(theme.color("text"))
        middle = math.radians(shown / 2)
        spot = self._point(center, radius, 0.36 * math.cos(middle), 0.36 * math.sin(middle))
        painter.drawText(QRectF(spot.x() - 40, spot.y() - 10, 80, 20), Qt.AlignmentFlag.AlignCenter,
                         angle_text(shown, self.mode))

        painter.setClipping(False)
        if self.hasFocus():
            paint_focus_ring(painter, panel, PANEL_RADIUS, theme.color("focus"))

    def _quadrant_spot(self, center: QPointF, radius: float, number: int, shown: float) -> QPointF:
        """Posição do número do quadrante: no meio do quadrante, afastada do raio se ele passar perto."""
        middle = 45.0 + 90.0 * (number - 1)
        gap = (shown - middle + 180) % 360 - 180          # do meio do quadrante até o raio
        if abs(gap) < QUADRANT_LABEL_GAP:
            # Passa para o lado do eixo vertical (o seno fica do lado do eixo horizontal);
            # se assim sair do quadrante, vai para o outro lado do raio.
            step = QUADRANT_LABEL_GAP + 4
            toward_vertical = 1 if number in (1, 3) else -1
            low, high = 90.0 * (number - 1) + 8, 90.0 * number - 8
            middle = shown + toward_vertical * step
            if not low <= middle <= high:
                middle = shown - toward_vertical * step
        angle = math.radians(middle)
        return self._point(center, radius, QUADRANT_LABEL_RADIUS * math.cos(angle),
                           QUADRANT_LABEL_RADIUS * math.sin(angle))

    def _label(self, painter: QPainter, name: str, spot: QPointF, align: str) -> None:
        key, _, text = FUNCTION_STYLES[name]
        font = QFont(self.font())
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(self._theme.color(key))
        width = 40
        if align == "left":
            rect = QRectF(spot.x(), spot.y() - 10, width, 20)
            flags = Qt.AlignmentFlag.AlignLeft
        elif align == "right":
            rect = QRectF(spot.x() - width, spot.y() - 10, width, 20)
            flags = Qt.AlignmentFlag.AlignRight
        else:
            rect = QRectF(spot.x() - width / 2, spot.y() - 10, width, 20)
            flags = Qt.AlignmentFlag.AlignHCenter
        painter.drawText(rect, flags | Qt.AlignmentFlag.AlignVCenter, text)
