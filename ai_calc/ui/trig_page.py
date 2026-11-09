"""Aba Trigonometria: círculo interativo, painel de informações e campos de ângulo e seno."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, QSize, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..core.errors import CalcError
from ..core.formatting import format_number
from ..core.trig import (
    TRIG_FUNCTIONS,
    TrigCircleState,
    angle_text,
    normalize_degrees,
    radians_text,
    toggle_visible,
)
from ..core.trig_input import angle_from_text, sine_from_text
from .glass import paint_glass, set_text_color
from .glass_button import GlassButton
from .glass_field import GlassField
from .motion import fade_in
from .tabs import GlassTabBar
from .theme import DISPLAY_ALPHA, ThemeManager
from .trig_circle import FUNCTION_STYLES, TrigCircleWidget, function_pen
from .trig_graphs import TrigGraphsWidget

START_ANGLE = 30.0
WIDE_MIN_WIDTH = 600    # a partir daqui, círculo e gráficos ficam lado a lado
POINT_MS = 300          # animação do ponto ao digitar um ângulo ou trocar a solução
CIRCLE_VIEW, GRAPHS_VIEW = 0, 1
FUNCTION_NAMES = {"sin": "seno", "cos": "cosseno", "tan": "tangente"}
SIGN_NAMES = {"+": "positivo", "-": "negativo", "0": "zero", "indefinida": "indefinida"}


def _font(label: QLabel, size: int, bold: bool = False) -> None:
    font = QFont(label.font())
    font.setPointSize(size)
    font.setBold(bold)
    label.setFont(font)


class LineSample(QWidget):
    """Amostra do estilo de linha de uma função (contínua, tracejada ou pontilhada)."""

    def __init__(self, theme: ThemeManager, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._name = name
        self.setFixedSize(QSize(26, 14))

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(function_pen(self._theme, self._name, 2.5))
        y = self.height() / 2
        painter.drawLine(QPointF(2, y), QPointF(self.width() - 2, y))


class FunctionToggle(GlassButton):
    """Liga/desliga de uma função: amostra da linha + nome; riscado quando desligada."""

    def __init__(self, theme: ThemeManager, name: str, parent: QWidget | None = None) -> None:
        super().__init__(FUNCTION_STYLES[name][2], theme, role="digit", small=True, parent=parent)
        self.name = name
        self.setCheckable(True)
        self.setChecked(True)
        self.setFixedSize(60, 34)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.toggled.connect(lambda _: self._describe())
        self._describe()

    def _describe(self) -> None:
        verb = "Esconder" if self.isChecked() else "Mostrar"
        self.setAccessibleName(f"Mostrar {FUNCTION_NAMES[self.name]}")
        self.setToolTip(f"{verb} {FUNCTION_NAMES[self.name]} no círculo, nos gráficos e no painel")

    def paint_content(self, painter: QPainter, rect: QRectF, color) -> None:
        theme = self._theme
        on = self.isChecked()
        x = rect.left() + 10
        y = rect.center().y()
        pen = function_pen(theme, self.name, 2.2)
        if not on:
            pen.setColor(theme.color("text_muted"))
        painter.setPen(pen)
        painter.drawLine(QPointF(x, y), QPointF(x + 16, y))
        font = QFont(self.font())
        font.setBold(on)
        font.setStrikeOut(not on)
        painter.setFont(font)
        painter.setPen(theme.color(FUNCTION_STYLES[self.name][0]) if on else theme.color("text_muted"))
        painter.drawText(QRectF(x + 20, rect.top(), rect.width() - 30, rect.height()),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())


class InfoCard(QFrame):
    """Ângulo em graus e radianos, quadrante, valores com sinal e "Também vale"."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setAccessibleName("Informações do ângulo")

        self.angle_label = QLabel(self)
        _font(self.angle_label, 13, bold=True)
        self.quadrant_label = QLabel(self)
        self.quadrant_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        _font(self.quadrant_label, 10)

        top = QHBoxLayout()
        top.addWidget(self.angle_label, 1)
        top.addWidget(self.quadrant_label)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(2)
        self.name_labels: dict[str, QLabel] = {}
        self.value_labels: dict[str, QLabel] = {}
        self.sign_labels: dict[str, QLabel] = {}
        self.samples: dict[str, LineSample] = {}
        for row, name in enumerate(("sin", "cos", "tan")):
            sample = LineSample(theme, name, self)
            title = QLabel(f"{FUNCTION_STYLES[name][2]} θ", self)
            _font(title, 11, bold=True)
            value = QLabel(self)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            _font(value, 11)
            sign = QLabel(self)
            sign.setFixedWidth(34)
            sign.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _font(sign, 10)
            grid.addWidget(sample, row, 0)
            grid.addWidget(title, row, 1)
            grid.addWidget(value, row, 2)
            grid.addWidget(sign, row, 3)
            self.name_labels[name] = title
            self.value_labels[name] = value
            self.sign_labels[name] = sign
            self.samples[name] = sample
        grid.setColumnStretch(2, 1)

        self.period_label = QLabel(self)
        _font(self.period_label, 10)

        # Aviso dos campos: fica dentro do vidro do painel, onde o vermelho tem contraste.
        self.error_label = QLabel(self)
        self.error_label.setAccessibleName("Aviso")
        self.error_label.setWordWrap(True)
        _font(self.error_label, 10, bold=True)
        self.error_label.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)
        layout.addLayout(top)
        layout.addLayout(grid)
        layout.addWidget(self.period_label)
        layout.addWidget(self.error_label)

        theme.changed.connect(self.apply_colors)
        self.apply_colors()

    def set_visible(self, visible: frozenset[str]) -> None:
        for name in TRIG_FUNCTIONS:
            for widget in (self.samples[name], self.name_labels[name],
                           self.value_labels[name], self.sign_labels[name]):
                widget.setVisible(name in visible)

    def show_state(self, state: TrigCircleState, mode: str) -> None:
        degrees = f"{format_number(state.angle)}°"
        radians = f"{radians_text(state.angle)} rad"
        self.angle_label.setText(f"{radians} = {degrees}" if mode == "RAD" else f"{degrees} = {radians}")
        self.quadrant_label.setText(state.quadrant_label)
        for name, value, sign in zip(("sin", "cos", "tan"), state.values, state.signs):
            text = "indefinida" if value is None else format_number(value)
            self.value_labels[name].setText(text)
            self.sign_labels[name].setText("" if sign == "indefinida" else f"({sign})")
            self.sign_labels[name].setAccessibleName(f"Sinal: {SIGN_NAMES[sign]}")
        self.period_label.setText(state.periodicity_text(mode))

    def apply_colors(self) -> None:
        theme = self._theme
        set_text_color(self.angle_label, theme.color("text"))
        set_text_color(self.quadrant_label, theme.color("text_muted"))
        set_text_color(self.period_label, theme.color("text_muted"))
        set_text_color(self.error_label, theme.color("error"))
        for name, title in self.name_labels.items():
            set_text_color(title, theme.color(FUNCTION_STYLES[name][0]))
            set_text_color(self.value_labels[name], theme.color("text"))
            set_text_color(self.sign_labels[name], theme.color("text_muted"))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -3)
        paint_glass(painter, rect, 16, self._theme, self._theme.hex("display_bg"), DISPLAY_ALPHA)


class TrigPage(QWidget):
    mode_toggle_requested = Signal()     # o botão DEG/RAD desta aba foi apertado
    visible_changed = Signal(tuple)      # funções visíveis mudaram (para salvar)

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.mode = "DEG"
        self.state = TrigCircleState(START_ANGLE)

        self.circle = TrigCircleWidget(theme, self.state, self)
        self.circle.angle_changed.connect(self._circle_moved)
        self.graphs = TrigGraphsWidget(theme, self)

        # Janela estreita: seletor "Círculo | Gráficos" no lugar de mostrar os dois.
        self.view_tabs = GlassTabBar(theme, self)
        self.view_tabs.setAccessibleName("Mostrar círculo ou gráficos")
        self.view_tabs.addTab("Círculo")
        self.view_tabs.addTab("Gráficos")
        self.view_tabs.currentChanged.connect(lambda _: self._switch_view())

        # Liga/desliga de seno, cosseno e tangente (vale para círculo, gráficos e painel).
        self.visible: frozenset[str] = frozenset(TRIG_FUNCTIONS)
        self.toggles = {name: FunctionToggle(theme, name, self) for name in TRIG_FUNCTIONS}
        for toggle in self.toggles.values():
            toggle.clicked.connect(lambda _=False, n=toggle.name: self.toggle_function(n))
        self.top_bar = QWidget(self)
        top = QHBoxLayout(self.top_bar)
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(6)
        top.addWidget(self.view_tabs, 1)
        top.addStretch(0)      # na janela larga (sem o seletor), empurra os botões para a direita
        for toggle in self.toggles.values():
            top.addWidget(toggle)
        self.view_tabs.setParent(self.top_bar)
        for toggle in self.toggles.values():
            toggle.setParent(self.top_bar)

        self._animation = QVariantAnimation(self)
        self._animation.setDuration(POINT_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.valueChanged.connect(self._show_angle)

        self.controls = QWidget(self)
        self.info = InfoCard(theme, self.controls)

        self.angle_field = GlassField("Ângulo", theme, self.controls)
        self.angle_field.submitted.connect(self._angle_typed)
        self.mode_button = GlassButton("DEG", theme, role="action", small=True, parent=self.controls)
        self.mode_button.setFixedWidth(64)
        self.mode_button.setMinimumHeight(40)
        self.mode_button.clicked.connect(self.mode_toggle_requested)

        self.sine_field = GlassField("Seno", theme, self.controls)
        self.sine_field.submitted.connect(self._sine_typed)
        self.toggle_button = GlassButton("Outra solução", theme, role="function", small=True, parent=self.controls)
        self.toggle_button.setMinimumHeight(40)
        self.toggle_button.clicked.connect(self._toggle)

        self.error_label = self.info.error_label

        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(self.angle_field, 1)
        row1.addWidget(self.mode_button)
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(self.sine_field, 1)
        row2.addWidget(self.toggle_button, 1)

        controls = QVBoxLayout(self.controls)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addWidget(self.info)
        controls.addLayout(row1)
        controls.addLayout(row2)

        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(8)
        self._wide: bool | None = None
        self._apply_layout()

        # Ordem do Tab = ordem de leitura: seletor, sen/cos/tan, círculo, campos e botões.
        order = [self.view_tabs, *self.toggles.values(), self.circle, self.angle_field.edit,
                 self.mode_button, self.sine_field.edit, self.toggle_button]
        for first, second in zip(order, order[1:]):
            QWidget.setTabOrder(first, second)
        self.refresh()

    # --- layout ---
    @property
    def wide(self) -> bool:
        return bool(self._wide)

    def _apply_layout(self) -> None:
        wide = self.width() >= WIDE_MIN_WIDTH
        grid = self._grid
        for widget in (self.top_bar, self.circle, self.graphs, self.controls):
            grid.removeWidget(widget)
        for index in range(3):
            grid.setRowStretch(index, 0)
            grid.setColumnStretch(index, 0)
        grid.addWidget(self.top_bar, 0, 0, 1, 2 if wide else 1)
        if wide:
            self.view_tabs.hide()
            self.circle.show()
            self.graphs.show()
            grid.addWidget(self.circle, 1, 0)
            grid.addWidget(self.controls, 2, 0)
            grid.addWidget(self.graphs, 1, 1, 2, 1)
            grid.setRowStretch(1, 1)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(1, 1)
        else:
            show_graphs = self.view_tabs.currentIndex() == GRAPHS_VIEW
            self.view_tabs.show()
            grid.addWidget(self.circle, 1, 0)
            grid.addWidget(self.graphs, 1, 0)
            self.circle.setVisible(not show_graphs)
            self.graphs.setVisible(show_graphs)
            grid.addWidget(self.controls, 2, 0)
            grid.setRowStretch(1, 1)
            grid.setColumnStretch(0, 1)
        self._wide = wide

    def _switch_view(self) -> None:
        self._apply_layout()
        if not self.wide:
            shown = self.graphs if self.view_tabs.currentIndex() == GRAPHS_VIEW else self.circle
            fade_in(shown, self._theme)

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        if (self.width() >= WIDE_MIN_WIDTH) != self._wide:
            self._apply_layout()

    # --- funções visíveis ---
    def set_visible_functions(self, names) -> None:
        visible = frozenset(name for name in names if name in TRIG_FUNCTIONS) or frozenset(TRIG_FUNCTIONS)
        self.visible = visible
        self.circle.set_visible(visible)
        self.graphs.set_visible(visible)
        self.info.set_visible(visible)
        for name, toggle in self.toggles.items():
            toggle.setChecked(name in visible)
            # A última função ligada não pode ser desligada.
            alone = visible == {name}
            toggle.setEnabled(not alone)
            if alone:
                toggle.setToolTip("Pelo menos uma função fica visível")

    def toggle_function(self, name: str) -> None:
        self.set_visible_functions(toggle_visible(self.visible, name))
        self.visible_changed.emit(tuple(n for n in TRIG_FUNCTIONS if n in self.visible))

    # --- modo DEG/RAD ---
    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.circle.mode = mode
        self.graphs.mode = mode
        name = "graus" if mode == "DEG" else "radianos"
        self.mode_button.setText(mode)
        self.mode_button.setAccessibleName(f"Modo de ângulo: {name}")
        self.mode_button.setToolTip(f"Modo de ângulo: {name}")
        self.refresh(force_fields=True)          # o campo passa a mostrar o ângulo no novo modo

    # --- ações ---
    def _circle_moved(self) -> None:
        self._clear_error()
        self.refresh()

    def _angle_typed(self, text: str) -> None:
        try:
            self.state.set_angle(angle_from_text(text, self.mode))
        except CalcError as error:
            self._show_error(f"Ângulo: {error.message}")
            return
        self._clear_error()
        self.refresh(force_fields=True, animate=True)

    def _sine_typed(self, text: str) -> None:
        try:
            self.state.set_sin(sine_from_text(text, self.mode))
        except CalcError as error:
            self._show_error(f"Seno: {error.message}")
            return
        self._clear_error()
        self.refresh(force_fields=True, animate=True)

    def _toggle(self) -> None:
        self.state.toggle()
        self._clear_error()
        self.refresh(force_fields=True, animate=True)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _clear_error(self) -> None:
        self.error_label.clear()
        self.error_label.hide()

    # --- exibição ---
    def refresh(self, force_fields: bool = False, animate: bool = False) -> None:
        state, mode = self.state, self.mode
        self.circle.refresh()
        self.graphs.update()
        self._move_point(animate)
        self.info.show_state(state, mode)
        angle_value = radians_text(state.angle) if mode == "RAD" else format_number(state.angle)
        self._show_field(self.angle_field, angle_value, force_fields)
        self._show_field(self.sine_field, format_number(state.values[0]), force_fields)

        self.toggle_button.setEnabled(state.can_toggle)
        if state.can_toggle:
            other = angle_text(normalize_degrees(180 - state.angle), mode)
            self.toggle_button.setText(f"Outra: {other}")
            spoken = other.replace("°", " graus")
            self.toggle_button.setAccessibleName(f"Outra solução do seno: {spoken}")
            self.toggle_button.setToolTip(f"Troca θ por 180° − θ ({other})")
        else:
            self.toggle_button.setText("Solução única")
            self.toggle_button.setAccessibleName("Outra solução indisponível: seno 1 ou −1 tem uma só")
            self.toggle_button.setToolTip("Com seno 1 ou −1 só existe uma solução")

    # --- animação do ponto ---
    @property
    def animating(self) -> bool:
        return self._animation.state() == QVariantAnimation.State.Running

    def _show_angle(self, angle: float) -> None:
        self.circle.set_shown_angle(float(angle))
        self.graphs.set_marker(float(angle))

    def _move_point(self, animate: bool) -> None:
        """Leva o ponto (e a marca dos gráficos) ao ângulo atual pelo caminho mais curto."""
        target = self.state.angle
        start = self.circle.shown_angle
        delta = ((target - start + 180) % 360) - 180
        self._animation.stop()
        if not animate or self._theme.reduce_motion() or abs(delta) < 1e-9:
            self._show_angle(target)
            return
        self._animation.setStartValue(start)
        self._animation.setEndValue(start + delta)
        self._animation.start()

    @staticmethod
    def _show_field(field: GlassField, text: str, force: bool) -> None:
        if force:
            field.set_value(text)
        else:
            field.show_value(text)
