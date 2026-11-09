"""Botões de vidro: teclas da calculadora, botões do topo (tema e histórico) e a
cápsula que agrupa os botões do topo."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QWidget

from .glass import capsule_radius, paint_focus_ring, paint_glass, with_alpha
from .icons import paint_clock, paint_menu, paint_moon, paint_sun
from .theme import HOVER_ALPHA, KEY_ALPHA, ROLE_COLORS, ThemeManager, mix

KEY_RADIUS = 999       # teclas em cápsula (o raio é limitado à metade da altura)
TOOL_SIZE = 34         # botões redondos dentro da cápsula do topo
PRESS_IN_MS = 60       # apertar: a tecla clareia e "estufa" quase na hora
PRESS_OUT_MS = 420     # soltar: volta com efeito de mola (passa um pouco do ponto e assenta)
PRESS_OVERSHOOT = 2.2  # quanto a mola passa do ponto
HOVER_MS = 140
SELECT_MS = 180        # operador escolhido ganha o destaque branco
POP_SCALE = 0.07       # teclas do teclado crescem 7% ao apertar (como no vidro líquido da Apple)
PRESS_SCALE = 0.04     # botões sem folga em volta encolhem 4%


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
        self._selected = 0.0
        self._was_down = False
        self._keyboard_focus = False
        self.pad = 0           # folga em volta (o teclado reserva espaço para a tecla crescer)
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
        self._select_animation = QVariantAnimation(self)
        self._select_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._select_animation.valueChanged.connect(self._set_selected)

    @property
    def role(self) -> str:
        return self._role

    @property
    def keyboard_focus(self) -> bool:
        return self.hasFocus() and self._keyboard_focus

    # Contorno de foco só quando o foco veio do teclado (Tab), não ao abrir a janela.
    def focusInEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().focusInEvent(event)
        self._keyboard_focus = event.reason() in (
            Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason,
            Qt.FocusReason.ShortcutFocusReason,
        )

    def focusOutEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().focusOutEvent(event)
        self._keyboard_focus = False

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        if self.auto_font:
            self.fit_font()

    def fit_font(self) -> None:
        """Fonte proporcional à altura da tecla (números grandes, como na Apple)."""
        height = self.height() - 2 * self.pad
        if self._small:
            share, low, high = 0.36, 11, 17
        elif self._role in ("operator", "equals"):
            share, low, high = 0.48, 16, 30
        else:
            share, low, high = 0.42, 14, 26
        font = QFont(self.font())
        font.setPixelSize(int(max(low, min(high, height * share))))
        # Rótulos longos (ex.: "sin⁻¹") diminuem até caber na largura.
        width = self.width() - 2 * self.pad - 12
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

    def _set_selected(self, value: float) -> None:
        self._selected = float(value)
        self.update()

    @property
    def selected(self) -> bool:
        return self._selected > 0.5

    def set_selected(self, selected: bool) -> None:
        """Operador escolhido: fundo branco e símbolo laranja até a próxima tecla."""
        target = 1.0 if selected else 0.0
        if self._select_animation.endValue() == target and (
            self._select_animation.state() == QVariantAnimation.State.Running
            or self._selected == target
        ):
            return
        self._animate(self._select_animation, self._selected, target, SELECT_MS)

    def _animate(
        self,
        animation: QVariantAnimation,
        current: float,
        target: float,
        ms: int,
        easing: QEasingCurve | None = None,
    ) -> None:
        animation.stop()
        if self._theme.reduce_motion():
            setters = {
                id(self._press_animation): self._set_press,
                id(self._hover_animation): self._set_hover,
                id(self._select_animation): self._set_selected,
            }
            setters[id(animation)](target)
            return
        if easing is not None:
            animation.setEasingCurve(easing)
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
                self._animate(self._press_animation, self._press, 1.0, PRESS_IN_MS,
                              QEasingCurve(QEasingCurve.Type.OutCubic))
            else:
                spring = QEasingCurve(QEasingCurve.Type.OutBack)
                spring.setOvershoot(PRESS_OVERSHOOT)
                self._animate(self._press_animation, self._press, 0.0, PRESS_OUT_MS, spring)

        role = self._role if self.isEnabled() else "tab_disabled"
        fill_key, pressed_key, text_key, alpha, focus_key = ROLE_COLORS[role]
        theme = self._theme
        press = max(0.0, min(1.0, self._press))     # a mola passa de 0; a cor não
        fill = mix(theme.hex(fill_key), theme.hex(pressed_key), press)
        text_color = theme.color(text_key)
        hover = self._hover if self.isEnabled() else 0.0
        if role == "equals":
            fill = mix(fill, theme.hex("equals_hover"), hover * (1 - press))
            hover = 0.0
        if role == "operator" and self._selected > 0:
            fill = mix(fill, theme.hex("operator_selected_bg"), self._selected)
            text_color = QColor(mix(theme.hex(text_key), theme.hex("operator_bg"), self._selected))

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.pad:
            rect = QRectF(self.rect()).adjusted(self.pad, self.pad, -self.pad, -self.pad)
            scale = 1.0 + POP_SCALE * self._press
        else:
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
        self.paint_content(painter, rect, text_color)
        if self.hasFocus() and self._keyboard_focus:
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


class MenuButton(GlassButton):
    """Botão ☰ que abre o menu de modos (Comum, Científica, Trigonometria)."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__("", theme, role="theme", parent=parent, flat=True)
        self.setObjectName("menuButton")
        self.setAccessibleName("Abrir menu de modos")
        self.setToolTip("Modos da calculadora")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(QSize(TOOL_SIZE, TOOL_SIZE))

    def paint_content(self, painter: QPainter, rect: QRectF, color) -> None:
        icon_rect = QRectF(0, 0, 20, 20)
        icon_rect.moveCenter(rect.center())
        paint_menu(painter, icon_rect, color)


class ToolGroup(QWidget):
    """Cápsula de vidro que agrupa os botões redondos do topo (histórico e tema)."""

    PADDING = 3

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._layout = QHBoxLayout(self)
        pad = self.PADDING
        # 2 em cima e 4 embaixo: com a sombra, o grupo tem os mesmos 40 px das outras peças do topo.
        self._layout.setContentsMargins(pad, 2, pad, 4)
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
