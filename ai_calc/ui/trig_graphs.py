"""Gráficos de seno, cosseno e tangente de 0° a 360°, com a marca do ângulo atual."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..core.limits import GRAPH_LIMIT
from ..core.trig import TRIG_FUNCTIONS, circle_values, graph_points, normalize_degrees, radians_text
from .glass import paint_glass, with_alpha
from .theme import DISPLAY_ALPHA, ThemeManager
from .trig_circle import FUNCTION_STYLES, function_pen

PANEL_RADIUS = 16
MARGIN_LEFT = 34
MARGIN_RIGHT = 14
MARGIN_TOP = 30         # espaço para a legenda
MARGIN_BOTTOM = 26
X_TICKS = (0, 90, 180, 270, 360)


class TrigGraphsWidget(QWidget):
    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.mode = "DEG"
        self.marker = 30.0
        self.visible: frozenset[str] = frozenset(TRIG_FUNCTIONS)
        self._segments = {name: graph_points(name) for name in ("sin", "cos", "tan")}
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 160)
        self.setAccessibleName("Gráficos de seno, cosseno e tangente, de 0 a 360 graus")
        theme.changed.connect(self.update)

    def sizeHint(self) -> QSize:  # noqa: N802 (nome do Qt)
        return QSize(320, 260)

    def set_visible(self, visible: frozenset[str]) -> None:
        self.visible = frozenset(visible)
        self.update()

    def set_marker(self, angle: float) -> None:
        self.marker = normalize_degrees(angle)
        self.update()

    def plot_rect(self) -> QRectF:
        rect = QRectF(self.rect())
        return rect.adjusted(MARGIN_LEFT, MARGIN_TOP, -MARGIN_RIGHT, -MARGIN_BOTTOM)

    def to_screen(self, degrees: float, value: float) -> QPointF:
        plot = self.plot_rect()
        x = plot.left() + plot.width() * degrees / 360
        y = plot.center().y() - (plot.height() / 2) * value / GRAPH_LIMIT
        return QPointF(x, y)

    def _tick_text(self, degrees: int) -> str:
        if self.mode == "RAD":
            return "2π" if degrees == 360 else radians_text(degrees)
        return f"{degrees}°"

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        theme = self._theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        panel = QRectF(self.rect()).adjusted(1, 1, -1, -3)
        paint_glass(painter, panel, PANEL_RADIUS, theme, theme.hex("display_bg"), DISPLAY_ALPHA)
        plot = self.plot_rect()
        muted = theme.color("text_muted")
        small = QFont(self.font())
        small.setPointSize(9)
        painter.setFont(small)

        # Grade: linhas em -1, 0 e 1 e nos múltiplos de 90°, com os números.
        for value in (-1, 0, 1):
            y = self.to_screen(0, value).y()
            painter.setPen(QPen(with_alpha(muted, 0.75 if value == 0 else 0.3), 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(muted)
            label = "−1" if value == -1 else str(value)
            painter.drawText(QRectF(0, y - 9, MARGIN_LEFT - 6, 18),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)
        for degrees in X_TICKS:
            x = self.to_screen(degrees, 0).x()
            painter.setPen(QPen(with_alpha(muted, 0.3), 1))
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            painter.setPen(muted)
            painter.drawText(QRectF(x - 24, plot.bottom() + 4, 48, 18), Qt.AlignmentFlag.AlignCenter,
                             self._tick_text(degrees))

        # Assíntotas da tangente (90° e 270°).
        tan_color = theme.color(FUNCTION_STYLES["tan"][0])
        painter.setPen(QPen(with_alpha(tan_color, 0.45), 1, Qt.PenStyle.DashLine))
        for degrees in (90, 270) if "tan" in self.visible else ():
            x = self.to_screen(degrees, 0).x()
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))

        # Curvas.
        painter.save()
        painter.setClipRect(plot.adjusted(-2, -2, 2, 2))
        for name in [n for n in ("cos", "tan", "sin") if n in self.visible]:
            painter.setPen(function_pen(theme, name, 2.2))
            for segment in self._segments[name]:
                path = QPainterPath(self.to_screen(*segment[0]))
                for degrees, value in segment[1:]:
                    path.lineTo(self.to_screen(degrees, value))
                painter.drawPath(path)
        painter.restore()

        # Marca do ângulo atual e os pontos de cada curva nela.
        x = self.to_screen(self.marker, 0).x()
        painter.setPen(QPen(theme.color("text"), 1.5))
        painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
        for name, value in zip(("sin", "cos", "tan"), circle_values(self.marker)):
            if name not in self.visible or value is None or abs(value) > GRAPH_LIMIT:
                continue
            painter.setPen(QPen(theme.color("display_bg"), 1.5))
            painter.setBrush(theme.color(FUNCTION_STYLES[name][0]))
            painter.drawEllipse(self.to_screen(self.marker, value), 4.5, 4.5)

        self._paint_legend(painter, plot)

    def _paint_legend(self, painter: QPainter, plot: QRectF) -> None:
        """Legenda com amostra da linha e nome (não depende só da cor)."""
        font = QFont(self.font())
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)
        x = plot.left()
        y = 8
        for name in [n for n in ("sin", "cos", "tan") if n in self.visible]:
            key, _, label = FUNCTION_STYLES[name]
            painter.setPen(function_pen(self._theme, name, 2.2))
            painter.drawLine(QPointF(x, y + 8), QPointF(x + 20, y + 8))
            painter.setPen(self._theme.color(key))
            painter.drawText(QRectF(x + 24, y, 40, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            x += 70
