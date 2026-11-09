"""Botões de vidro: teclas da calculadora, botões do topo (tema e histórico) e a
cápsula que agrupa os botões do topo."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget

from .glass import capsule_radius, paint_focus_ring, paint_glass, with_alpha
from .icons import paint_clock, paint_moon, paint_sun
from .theme import HOVER_ALPHA, KEY_ALPHA, ROLE_COLORS, ThemeManager, mix

KEY_RADIUS = 999       # teclas em cápsula (o raio é limitado à metade da altura)
TOOL_SIZE = 34         # botões redondos dentro da cápsula do topo
PRESS_IN_MS = 70
PRESS_OUT_MS = 180
HOVER_MS = 140
PRESS_SCALE = 0.04     # a tecla encolhe 4% quando apertada


class GlassButton(QPushButton):
    """Tecla de vidro com animações discretas de passar o mouse e de clique."""

    def __init__(
        self,
        text: str,
        theme: ThemeManager,
        role: str = "digit",
        small: bool = False,
        parent: QWidget | None = None,
        flat: bool = False,
    ) -> None:
        super().__init__(text, parent)
        self._theme = theme
        self._role = role
        # Sem vidro próprio: o botão fica sobre outra superfície de vidro (cápsula do
        # topo, lista do histórico) e só mostra um realce ao passar o mouse ou apertar.
        self._flat = flat
        self._press = 0.0
        self._hover = 0.0
        self._was_down = False
        self.setProperty("role", role)
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._small = small
        self.auto_font = False     # teclado: a fonte acompanha o tamanho da tecla
        font = QFont(self.font())
        font.setPointSize(11 if small else 16)
        if role in ("equals", "operator") and not small:
            font.setPointSize(19)
            font.setWeight(QFont.Weight.Medium)
        self.setFont(font)

        self._press_animation = QVariantAnimation(self)
        self._press_animation.valueChanged.connect(self._set_press)
        self._hover_animation = QVariantAnimation(self)
        self._hover_animation.valueChanged.connect(self._set_hover)

    @property
    def role(self) -> str:
        return self._role

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        if self.auto_font:
            self.fit_font()

    def fit_font(self) -> None:
        """Fonte proporcional à altura da tecla (números grandes, como na Apple)."""
        height = self.height()
        if self._small:
            share, low, high = 0.34, 11, 22
        elif self._role in ("operator", "equals"):
            share, low, high = 0.50, 18, 40
        else:
            share, low, high = 0.42, 16, 34
        font = QFont(self.font())
        font.setPixelSize(int(max(low, min(high, height * share))))
        # Rótulos longos (ex.: "sin⁻¹") diminuem até caber na largura.
        width = self.width() - 16
        while font.pixelSize() > low and QFontMetrics(font).horizontalAdvance(self.text()) > width:
            font.setPixelSize(font.pixelSize() - 1)
        self.setFont(font)

    # --- animações ---
    def _set_press(self, value: float) -> None:
        self._press = float(value)
        self.update()

    def _set_hover(self, value: float) -> None:
        self._hover = float(value)
        self.update()

    def _animate(self, animation: QVariantAnimation, current: float, target: float, ms: int) -> None:
        animation.stop()
        if self._theme.reduce_motion():
            setter = self._set_press if animation is self._press_animation else self._set_hover
            setter(target)
            return
        animation.setStartValue(current)
        animation.setEndValue(target)
        animation.setDuration(ms)
        animation.start()

    def enterEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().enterEvent(event)
        self._animate(self._hover_animation, self._hover, 1.0, HOVER_MS)

    def leaveEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().leaveEvent(event)
        self._animate(self._hover_animation, self._hover, 0.0, HOVER_MS)

    # --- desenho ---
    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        # isDown() muda por mouse, Espaço ou teclado físico (flash); anima a partir daqui.
        down = self.isDown()
        if down != self._was_down:
            self._was_down = down
            if down:
                self._animate(self._press_animation, self._press, 1.0, PRESS_IN_MS)
            else:
                self._animate(self._press_animation, self._press, 0.0, PRESS_OUT_MS)

        role = self._role if self.isEnabled() else "tab_disabled"
        fill_key, pressed_key, text_key, alpha, focus_key = ROLE_COLORS[role]
        theme = self._theme
        fill = mix(theme.hex(fill_key), theme.hex(pressed_key), self._press)
        hover = self._hover if self.isEnabled() else 0.0
        if role == "equals":
            fill = mix(fill, theme.hex("equals_hover"), hover * (1 - self._press))
            hover = 0.0

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bottom = -1.5 if self._flat else -4.0      # espaço para a sombra embaixo
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, bottom)
        scale = 1.0 - PRESS_SCALE * self._press
        center = rect.center()
        painter.translate(center)
        painter.scale(scale, scale)
        painter.translate(-center)

        radius = self.radius(rect)
        if self._flat:
            self.paint_flat(painter, rect, radius, fill, alpha, hover)
        else:
            paint_glass(painter, rect, radius, theme, fill, alpha, hover)
        self.paint_content(painter, rect, theme.color(text_key))
        if self.hasFocus():
            paint_focus_ring(painter, rect, radius, theme.color(focus_key))

    def radius(self, rect: QRectF) -> float:
        return min(KEY_RADIUS, capsule_radius(rect))

    def paint_flat(self, painter: QPainter, rect: QRectF, radius: float, fill: str, alpha: float,
                   hover: float) -> None:
        """Realce discreto de um botão sem vidro próprio (mouse por cima ou apertado)."""
        strength = max(hover * 0.6, self._press)
        if strength <= 0:
            return
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        painter.fillPath(path, with_alpha(fill, alpha * strength))
        painter.fillPath(path, with_alpha(self._theme.hex("glass_rim"), HOVER_ALPHA * hover))

    def paint_content(self, painter: QPainter, rect: QRectF, color) -> None:
        painter.setPen(color)
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())


class ThemeToggleButton(GlassButton):
    """Botão de tema: lua no claro, sol no escuro, trocando suavemente junto com o tema."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__("", theme, role="theme", parent=parent, flat=True)
        self.setObjectName("themeButton")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(QSize(TOOL_SIZE, TOOL_SIZE))

    def paint_content(self, painter: QPainter, rect: QRectF, color) -> None:
        progress = self._theme.progress         # 0 = claro (lua), 1 = escuro (sol)
        icon_rect = QRectF(0, 0, 20, 20)
        icon_rect.moveCenter(rect.center())
        if progress < 1:
            paint_moon(painter, icon_rect, with_alpha(color, 1 - progress))
        if progress > 0:
            paint_sun(painter, icon_rect, with_alpha(color, progress))


class HistoryToggleButton(GlassButton):
    """Botão que mostra/esconde o histórico quando a janela está estreita."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__("", theme, role="theme", parent=parent, flat=True)
        self.setObjectName("historyButton")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(QSize(TOOL_SIZE, TOOL_SIZE))

    def paint_content(self, painter: QPainter, rect: QRectF, color) -> None:
        icon_rect = QRectF(0, 0, 20, 20)
        icon_rect.moveCenter(rect.center())
        paint_clock(painter, icon_rect, color)


class ToolGroup(QWidget):
    """Cápsula de vidro que agrupa os botões redondos do topo (histórico e tema)."""

    PADDING = 3

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._layout = QHBoxLayout(self)
        pad = self.PADDING
        self._layout.setContentsMargins(pad, pad, pad, pad + 2)    # +2: sombra embaixo
        self._layout.setSpacing(2)

    def add(self, button: QWidget) -> None:
        self._layout.addWidget(button)

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        if not any(child.isVisible() for child in self.findChildren(GlassButton)):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -3)
        theme = self._theme
        paint_glass(painter, rect, capsule_radius(rect), theme, theme.hex("tab_bg"), KEY_ALPHA)
