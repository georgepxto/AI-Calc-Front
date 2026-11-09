"""Menu de modos, como o da Calculadora do Windows.

O botão ☰ no topo abre um cartão de vidro que desliza da esquerda, por cima da
janela levemente escurecida. Clicar num modo troca a aba e fecha o menu; clicar
fora, apertar Esc ou o ☰ de novo também fecha.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QFont, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from .glass import paint_glass, set_text_color, with_alpha
from .tabs import GlassTabBar
from .theme import DIALOG_ALPHA, DIM_ALPHA, ThemeManager

MENU_WIDTH = 240
MENU_RADIUS = 22
MENU_PADDING = 12
MENU_MS = 320          # entrada do cartão (com uma mola leve)


class NavCard(QFrame):
    """Cartão do menu: título e a lista de modos."""

    def __init__(self, theme: ThemeManager, tabs: GlassTabBar, parent: QWidget) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setObjectName("navCard")
        self.setFixedWidth(MENU_WIDTH)

        self.title = QLabel("Modos", self)
        font = QFont(self.title.font())
        font.setPointSize(10)
        font.setWeight(QFont.Weight.DemiBold)
        self.title.setFont(font)

        tabs.setParent(self)
        tabs.setShape(GlassTabBar.Shape.RoundedWest)
        tabs.setExpanding(False)
        tabs.setFixedWidth(MENU_WIDTH - 2 * MENU_PADDING)
        tabs.setMinimumWidth(MENU_WIDTH - 2 * MENU_PADDING)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(MENU_PADDING, MENU_PADDING, MENU_PADDING, MENU_PADDING + 2)
        layout.setSpacing(8)
        layout.addWidget(self.title)
        layout.addWidget(tabs)
        theme.changed.connect(self.apply_colors)
        self.apply_colors()

    def apply_colors(self) -> None:
        set_text_color(self.title, self._theme.color("text_muted"))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -4)
        theme = self._theme
        base = QPainterPath()
        base.addRoundedRect(rect, MENU_RADIUS, MENU_RADIUS)
        painter.fillPath(base, theme.color("window_bottom"))     # sólido: nada aparece por trás
        paint_glass(painter, rect, MENU_RADIUS, theme, theme.hex("display_bg"), DIALOG_ALPHA)


class NavMenu(QWidget):
    """Camada por cima da janela (escurecida) com o cartão do menu."""

    closed = Signal()

    def __init__(self, theme: ThemeManager, tabs: GlassTabBar, parent: QWidget) -> None:
        super().__init__(parent)
        self._theme = theme
        self._open = False
        self._dim = 0.0
        self.card = NavCard(theme, tabs, self)
        self._animation = QPropertyAnimation(self.card, b"pos", self)
        self._animation.setDuration(MENU_MS)
        spring = QEasingCurve(QEasingCurve.Type.OutBack)
        spring.setOvershoot(0.7)
        self._animation.setEasingCurve(spring)
        self._animation.finished.connect(self._finished)
        theme.changed.connect(self.update)
        self.hide()

    @property
    def is_open(self) -> bool:
        return self._open

    def open_at(self, anchor: QPoint) -> None:
        """Abre o menu com o canto de cima do cartão em "anchor" (coordenadas da camada)."""
        parent = self.parentWidget()
        self.setGeometry(QRect(0, 0, parent.width(), parent.height()))
        self.card.adjustSize()
        self._open = True
        self.show()
        self.raise_()
        start = QPoint(anchor.x() - 24, anchor.y())
        self._move(start, anchor)

    def close_menu(self) -> None:
        if not self._open:
            return
        self._open = False
        end = QPoint(self.card.x() - 24, self.card.y())
        self._move(self.card.pos(), end)

    def _move(self, start: QPoint, end: QPoint) -> None:
        self._animation.stop()
        if self._theme.reduce_motion():
            self.card.move(end)
            self._finished()
            return
        self.card.move(start)
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()
        self.update()

    def _finished(self) -> None:
        if not self._open:
            self.hide()
            self.closed.emit()
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        if not self.card.geometry().contains(event.position().toPoint()):
            self.close_menu()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        if event.key() == Qt.Key.Key_Escape:
            self.close_menu()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        if not self._open:
            return
        painter = QPainter(self)
        painter.fillRect(self.rect(), with_alpha(self._theme.hex("shadow"), DIM_ALPHA * 0.6))
