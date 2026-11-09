"""Janela principal: abas, botões do topo, visor, teclados e histórico.

A lógica fica no core (editor, histórico e preferências); aqui só se liga
cada peça e se mostra o estado.
"""

from __future__ import annotations

import string

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from ..core.editor import KEY_ALIASES, ExpressionEditor
from ..core.history import History
from ..core.preferences import Preferences
from .confirm_dialog import ConfirmDialog
from .display import Display
from .glass import Backdrop
from .glass_button import GlassButton, HistoryToggleButton, ThemeToggleButton, ToolGroup
from .history_panel import HistoryPanel
from .percentage_panel import PercentagePanel
from .motion import fade_in
from .keypad import (
    ANGLE_MODE,
    BACKSPACE,
    CLEAR,
    COMMON_KEYS,
    EVALUATE,
    SCIENTIFIC_KEYS,
    Keypad,
)
from .tabs import GlassTabBar
from .theme import LIGHT, ThemeManager
from .trig_page import TrigPage

MIN_WIDTH = 360
MIN_HEIGHT = 560
START_SIZE = (700, 640)

COMMON_TAB = 0
SCIENTIFIC_TAB = 1
TRIG_TAB = 2
TAB_NAMES = {COMMON_TAB: "comum", SCIENTIFIC_TAB: "cientifica", TRIG_TAB: "trigonometria"}

# Histórico: painel fixo ao lado quando a janela é larga; gaveta com botão quando é estreita.
DOCK_MIN_WIDTH = 660
PANEL_WIDTH = 280
DRAWER_MS = 220

# Caracteres aceitos do teclado físico (letras servem para digitar funções: sin, ln...).
TYPED_CHARACTERS = (
    set("0123456789,+()%×÷−^!;") | set(KEY_ALIASES) | set(string.ascii_letters)
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        theme: ThemeManager | None = None,
        history: History | None = None,
        preferences: Preferences | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("AI Calc")
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)
        self.resize(*START_SIZE)

        self.editor = ExpressionEditor()
        self.angle_mode = "DEG"
        self.theme = theme or ThemeManager()
        self.history = history or History()
        self.preferences = preferences or Preferences()
        self._docked = False
        self._drawer_open = False
        self._percentage_open = False

        # --- topo ---
        self.tabs = GlassTabBar(self.theme, self)
        self.tabs.setAccessibleName("Modo da calculadora")
        self.tabs.addTab("Comum")
        self.tabs.addTab("Científica")
        self.tabs.addTab("Trigonometria")

        self.history_button = HistoryToggleButton(self.theme, self)
        self.history_button.clicked.connect(self.toggle_history_drawer)

        self.theme_button = ThemeToggleButton(self.theme, self)
        self.theme_button.clicked.connect(self._choose_other_theme)
        self.theme.theme_changed.connect(self._update_theme_button)
        # Cada quadro da transição redesenha a janela inteira de uma vez.
        self.theme.changed.connect(self.update)

        # --- calculadora ---
        self.display = Display(self.theme, self)
        self.common_keypad = Keypad(COMMON_KEYS, self.theme, self)
        self.scientific_keypad = Keypad(SCIENTIFIC_KEYS, self.theme, self, key_min_height=34)
        for keypad in (self.common_keypad, self.scientific_keypad):
            keypad.inserted.connect(self.insert)
            keypad.action.connect(self.run_action)

        self.trig_page = TrigPage(self.theme, self)
        self.trig_page.mode_toggle_requested.connect(lambda: self.run_action(ANGLE_MODE))
        self.trig_page.set_visible_functions(self.preferences.visible_functions)
        self.trig_page.visible_changed.connect(lambda names: self.preferences.update(visible_functions=names))

        self.pages = QStackedWidget(self)
        self.pages.addWidget(self.common_keypad)
        self.pages.addWidget(self.scientific_keypad)
        self.pages.addWidget(self.trig_page)
        self.tabs.currentChanged.connect(self._tab_changed)

        # --- montagem ---
        central = Backdrop(self.theme, self)
        central.setObjectName("central")
        self.setCentralWidget(central)

        self.calculator = QWidget(central)
        column = QVBoxLayout(self.calculator)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        # Topo: abas (controle segmentado) e, numa cápsula ao lado, histórico e tema.
        self.tools = ToolGroup(self.theme, self.calculator)
        self.tools.add(self.history_button)
        self.tools.add(self.theme_button)
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(self.tabs, 1)
        top.addWidget(self.tools, 0, Qt.AlignmentFlag.AlignTop)
        column.addLayout(top)
        column.addWidget(self.display)

        self.percentage_button = GlassButton("Porcentagem", self.theme, role="function", small=True, parent=self)
        self.percentage_button.setFixedSize(132, 32)
        self.percentage_button.setAccessibleName("Porcentagem")
        self.percentage_button.setToolTip("Abrir painel de porcentagem")
        self.percentage_button.clicked.connect(self.toggle_percentage_panel)

        self.common_tools = QWidget(self.calculator)
        common_tools_layout = QHBoxLayout(self.common_tools)
        common_tools_layout.setContentsMargins(0, 0, 0, 0)
        common_tools_layout.setSpacing(6)
        common_tools_layout.addWidget(self.percentage_button)
        common_tools_layout.addStretch(1)
        column.addWidget(self.common_tools)

        column.addWidget(self.pages, 1)

        self.percentage_panel = PercentagePanel(self.theme, self.calculator)
        self.percentage_panel.value_chosen.connect(self.insert_percentage_value)
        self.percentage_panel.close_requested.connect(self.close_percentage_panel)
        self.percentage_panel.hide()

        self.history_panel = HistoryPanel(self.theme, central)
        self.history_panel.setFixedWidth(PANEL_WIDTH)
        self.history_panel.value_chosen.connect(self.insert_history_value)
        self.history_panel.clear_requested.connect(self.ask_clear_history)
        self.history_panel.close_requested.connect(self.close_history_drawer)
        self.history_panel.show_entries(self.history.entries)
        self._drawer_animation = QPropertyAnimation(self.history_panel, b"pos", self)
        self._drawer_animation.setDuration(DRAWER_MS)
        self._drawer_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._drawer_animation.finished.connect(self._drawer_animation_finished)

        self._root = QHBoxLayout(central)
        self._root.setContentsMargins(16, 14, 16, 16)
        self._root.setSpacing(16)
        self._root.addWidget(self.calculator, 1)

        self.confirm_dialog: ConfirmDialog | None = None

        # --- preferências salvas ---
        self.set_angle_mode(self.preferences.angle_mode, save=False)
        for index, name in TAB_NAMES.items():
            if self.preferences.last_tab == name:
                self.tabs.setCurrentIndex(index)

        self.theme.apply()
        self._update_history_layout()
        self.common_tools.setVisible(self.tabs.currentIndex() == COMMON_TAB)
        self._refresh()

    @property
    def current_keypad(self) -> Keypad:
        return self.pages.currentWidget()

    @property
    def percentage_panel_open(self) -> bool:
        return self._percentage_open

    @property
    def history_docked(self) -> bool:
        return self._docked

    @property
    def history_drawer_open(self) -> bool:
        return self._drawer_open

    # --- ações da calculadora -------------------------------------------------
    def insert(self, text: str) -> None:
        self.editor.insert(text)
        self._refresh()

    def run_action(self, action: str) -> None:
        if action == CLEAR:
            self.editor.clear()
        elif action == BACKSPACE:
            self.editor.backspace()
        elif action == EVALUATE:
            if self.editor.evaluate(self.angle_mode):
                self._remember(self.editor.last_outcome)
                self._refresh()
                fade_in(self.display.result_label, self.theme)
        elif action == ANGLE_MODE:
            self.set_angle_mode("RAD" if self.angle_mode == "DEG" else "DEG")
        self._refresh()

    def set_angle_mode(self, mode: str, save: bool = True) -> None:
        self.angle_mode = mode
        name = "graus" if mode == "DEG" else "radianos"
        self.scientific_keypad.set_key_text(ANGLE_MODE, mode, f"Modo de ângulo: {name}")
        self.display.show_angle_mode(mode)
        self.trig_page.set_mode(mode)
        if save:
            self.preferences.update(angle_mode=mode)

    def _refresh(self) -> None:
        editor = self.editor
        self.display.show_state(editor.expression, editor.result, editor.message, editor.is_error)

    def _tab_changed(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        fade_in(self.pages.currentWidget(), self.theme)
        # A aba Trigonometria não usa o visor e dá o espaço do histórico ao círculo
        # (o histórico continua na gaveta, pelo botão de relógio).
        self.display.setVisible(index != TRIG_TAB)
        self.common_tools.setVisible(index == COMMON_TAB)
        if index != COMMON_TAB and self._percentage_open:
            self.close_percentage_panel()
        self._update_history_layout()
        if index in TAB_NAMES:
            self.preferences.update(last_tab=TAB_NAMES[index])

    # --- tema -----------------------------------------------------------------
    def _choose_other_theme(self) -> None:
        # A escolha feita no botão passa a valer sobre o tema do Windows.
        self.theme.toggle()
        self.preferences.update(theme=self.theme.name)

    def _update_theme_button(self, name: str) -> None:
        # O ícone mostra para qual tema o botão leva: lua no claro, sol no escuro.
        label = "Mudar para o tema escuro" if name == LIGHT else "Mudar para o tema claro"
        self.theme_button.setAccessibleName(label)
        self.theme_button.setToolTip(label)

    # --- histórico ------------------------------------------------------------
    def _remember(self, outcome) -> None:
        mode = self.angle_mode if outcome.uses_trig else None
        if self.history.add(outcome.expression, outcome.text, mode):
            self.history_panel.show_entries(self.history.entries)

    def insert_history_value(self, number: str) -> None:
        self.editor.insert_value(number)
        self._refresh()
        if not self._docked:
            self.close_history_drawer()

    def ask_clear_history(self) -> None:
        count = len(self.history.entries)
        if not count:
            return
        text = (
            "A conta salva será apagada." if count == 1
            else f"As {count} contas salvas serão apagadas."
        ) + " Isso não pode ser desfeito."
        dialog = ConfirmDialog(self.theme, self, "Limpar o histórico?", text, "Limpar")
        dialog.accepted.connect(self.clear_history)
        dialog.finished.connect(lambda _: self.history_panel.clear_button.setFocus())
        dialog.finished.connect(dialog.deleteLater)
        self.confirm_dialog = dialog
        dialog.open()

    def clear_history(self) -> None:
        self.history.clear()
        self.history_panel.show_entries([])

    def toggle_history_drawer(self) -> None:
        if self._drawer_open:
            self.close_history_drawer()
        else:
            self.open_history_drawer()

    def open_history_drawer(self) -> None:
        if self._docked or self._drawer_open:
            return
        self._drawer_open = True
        panel = self.history_panel
        panel.set_drawer_mode(True)
        target = self._drawer_geometry()
        panel.setFixedWidth(target.width())
        panel.setFixedHeight(target.height())
        panel.raise_()
        panel.show()
        self._slide(panel, QPoint(self.centralWidget().width(), target.y()), target.topLeft())
        self._update_history_button()
        first = panel.items[0] if panel.items else panel.close_button
        first.setFocus(Qt.FocusReason.TabFocusReason)

    def close_history_drawer(self) -> None:
        if not self._drawer_open:
            return
        self._drawer_open = False
        panel = self.history_panel
        self._slide(panel, panel.pos(), QPoint(self.centralWidget().width(), panel.y()))
        self._update_history_button()
        if self._percentage_open:
            self._update_percentage_layout()
            self.percentage_panel.raise_()
        else:
            self.history_button.setFocus(Qt.FocusReason.TabFocusReason)

    def _slide(self, panel: QWidget, start: QPoint, end: QPoint) -> None:
        self._drawer_animation.stop()
        if self.theme.reduce_motion():
            panel.move(end)
            self._drawer_animation_finished()
            return
        self._drawer_animation.setStartValue(start)
        self._drawer_animation.setEndValue(end)
        self._drawer_animation.start()

    def _drawer_animation_finished(self) -> None:
        if not self._drawer_open and not self._docked:
            self.history_panel.hide()
        if self._percentage_open:
            self._update_percentage_layout()
            self.percentage_panel.raise_()

    def _drawer_geometry(self):
        central = self.centralWidget()
        top = self.tabs.mapTo(central, QPoint(0, self.tabs.height())).y() + 8
        width = min(PANEL_WIDTH + 20, central.width() - 48)
        rect = central.rect().adjusted(central.width() - width - 16, top, -16, -16)
        return rect

    def _update_history_layout(self) -> None:
        if not hasattr(self, "_root"):
            return                       # ainda montando a janela
        docked = self.width() >= DOCK_MIN_WIDTH and self.tabs.currentIndex() != TRIG_TAB
        panel = self.history_panel
        if docked and not self._docked:
            self._drawer_animation.stop()
            self._drawer_open = False
            panel.set_drawer_mode(False)
            panel.setFixedWidth(PANEL_WIDTH)
            panel.setMinimumHeight(0)
            panel.setMaximumHeight(16777215)
            self._root.addWidget(panel)
            panel.show()
        elif not docked and (self._docked or not panel.isHidden() and not self._drawer_open):
            self._root.removeWidget(panel)
            panel.hide()
        self._docked = docked
        self.history_button.setVisible(not docked)
        if self._drawer_open:
            target = self._drawer_geometry()
            panel.setFixedSize(target.size())
            panel.move(target.topLeft())
        self._update_history_button()

    def _update_history_button(self) -> None:
        label = "Esconder histórico" if self._drawer_open else "Mostrar histórico"
        self.history_button.setAccessibleName(label)
        self.history_button.setToolTip(label)

    # --- porcentagem ---------------------------------------------------------
    def toggle_percentage_panel(self) -> None:
        if self._percentage_open:
            self.close_percentage_panel()
        else:
            self.open_percentage_panel()

    def open_percentage_panel(self) -> None:
        if self.tabs.currentIndex() != COMMON_TAB:
            self.tabs.setCurrentIndex(COMMON_TAB)
        self._percentage_open = True
        self.common_keypad.setEnabled(False)
        self._update_percentage_layout()
        self.percentage_panel.raise_()
        self.percentage_panel.show()
        self.percentage_panel.focus_first_field()
        self._update_percentage_button()

    def close_percentage_panel(self) -> None:
        if not self._percentage_open:
            return
        self._percentage_open = False
        self.percentage_panel.hide()
        self.common_keypad.setEnabled(True)
        self._update_percentage_button()
        self.percentage_button.setFocus(Qt.FocusReason.TabFocusReason)

    def insert_percentage_value(self, number: str) -> None:
        self.editor.insert_value(number)
        self._refresh()
        self.close_percentage_panel()

    def _update_percentage_layout(self) -> None:
        if not self._percentage_open:
            return
        self.percentage_panel.setGeometry(self.pages.geometry())

    def _update_percentage_button(self) -> None:
        label = "Fechar painel de porcentagem" if self._percentage_open else "Abrir painel de porcentagem"
        self.percentage_button.setToolTip(label)

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        self._update_history_layout()
        self._update_percentage_layout()

    # --- teclado físico ------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (nome do Qt)
        key = event.key()
        modifiers = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            super().keyPressEvent(event)
            return

        if key == Qt.Key.Key_Escape and self._percentage_open:
            self.close_percentage_panel()
            event.accept()
            return
        if key == Qt.Key.Key_Escape and self._drawer_open:
            self.close_history_drawer()
        elif self.tabs.currentIndex() == TRIG_TAB:
            # Na Trigonometria as teclas não vão para a conta escondida.
            super().keyPressEvent(event)
            return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Equal):
            self._press_action(EVALUATE)
        elif key == Qt.Key.Key_Backspace:
            self._press_action(BACKSPACE)
        elif key in (Qt.Key.Key_Escape, Qt.Key.Key_Delete):
            self._press_action(CLEAR)
        elif event.text() and event.text() in TYPED_CHARACTERS:
            text = event.text()
            self.current_keypad.flash(KEY_ALIASES.get(text, text))
            self.insert(text.lower())
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def _press_action(self, action: str) -> None:
        self.current_keypad.flash(action)
        self.run_action(action)
