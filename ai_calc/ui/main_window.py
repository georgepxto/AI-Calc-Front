"""Janela principal: abas, botões do topo, visor, teclados e histórico.

A lógica fica no core (editor, histórico e preferências); aqui só se liga
cada peça e se mostra o estado.
"""

from __future__ import annotations

import string

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from ..core.editor import KEY_ALIASES, ExpressionEditor
from ..core.history import History
from ..core.preferences import Preferences
from .confirm_dialog import ConfirmDialog
from .display import Display
from .glass import Backdrop, set_text_color
from .glass_button import GlassButton, HistoryToggleButton, MenuButton, ThemeToggleButton, ToolGroup
from .history_panel import HistoryPanel
from .nav_menu import NavMenu
from .percentage_panel import PercentagePanel
from .motion import fade_in
from .keypad import (
    KEY_PAD,
    COMMON_METRICS,
    SCIENTIFIC_METRICS,
    ANGLE_MODE,
    BACKSPACE,
    PARENTHESES,
    CLEAR,
    COMMON_KEYS,
    EVALUATE,
    SCIENTIFIC_KEYS,
    Keypad,
)
from .tabs import GlassTabBar
from .system import set_dark_title_bar
from .theme import DARK, LIGHT, ThemeManager
from .trig_page import TrigPage

MIN_WIDTH = 360
MIN_HEIGHT = 560
START_SIZE = (700, 640)

COMMON_TAB = 0
SCIENTIFIC_TAB = 1
TRIG_TAB = 2
OPERATOR_KEYS = ("+", "−", "×", "÷")
TAB_NAMES = {COMMON_TAB: "comum", SCIENTIFIC_TAB: "cientifica", TRIG_TAB: "trigonometria"}

OUTER_MARGIN = 16      # margem da janela e espaço até o painel do histórico
SECTION_GAP = 12       # espaço entre topo, visor e teclado

# Histórico: painel fixo ao lado quando a janela é larga; gaveta com botão quando é estreita.
DOCK_MIN_WIDTH = 660
PANEL_WIDTH = 280
# Tela grande: calculadora e histórico ficam juntos e centralizados, com tamanho máximo.
BODY_MAX_HEIGHT = 780          # abas com teclado
TRIG_MAX_SIZE = (1500, 1000)   # aba Trigonometria (círculo e gráficos aproveitam o espaço)

DRAWER_MS = 340        # gaveta do histórico entra com uma mola leve

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
        # Os modos ficam num menu (☰), como na Calculadora do Windows; o nome do modo
        # atual aparece ao lado. Assim o topo não muda de tamanho ao trocar de modo.
        self.tabs = GlassTabBar(self.theme, self)
        self.tabs.setAccessibleName("Modo da calculadora")
        self.tabs.addTab("Comum")
        self.tabs.addTab("Científica")
        self.tabs.addTab("Trigonometria")

        self.menu_button = MenuButton(self.theme, self)
        self.menu_button.clicked.connect(self.toggle_menu)
        self.mode_title = QLabel(self.tabs.tabText(0), self)
        self.mode_title.setObjectName("modeTitle")
        title_font = QFont(self.mode_title.font())
        title_font.setPointSize(15)
        title_font.setWeight(QFont.Weight.DemiBold)
        self.mode_title.setFont(title_font)
        self.mode_title.setMinimumWidth(10)

        self.history_button = HistoryToggleButton(self.theme, self)
        self.history_button.clicked.connect(self.toggle_history_drawer)

        self.theme_button = ThemeToggleButton(self.theme, self)
        self.theme_button.clicked.connect(self._choose_other_theme)
        self.theme.theme_changed.connect(self._update_theme_button)
        # Cada quadro da transição redesenha a janela inteira de uma vez.
        self.theme.changed.connect(self.update)

        # --- calculadora ---
        self.display = Display(self.theme, self)
        self.common_keypad = Keypad(COMMON_KEYS, self.theme, self, COMMON_METRICS)
        self.scientific_keypad = Keypad(SCIENTIFIC_KEYS, self.theme, self, SCIENTIFIC_METRICS)
        for keypad in (self.common_keypad, self.scientific_keypad):
            keypad.inserted.connect(self.insert)
            keypad.action.connect(self.run_action)
            keypad.laid_out.connect(self._align_display)

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
        central.installEventFilter(self)             # centraliza o corpo ao mudar de tamanho
        self.body = QWidget(central)
        self.body.setObjectName("body")

        self.calculator = QWidget(self.body)
        self.calculator.installEventFilter(self)     # refaz as medidas do teclado ao mudar de tamanho
        column = QVBoxLayout(self.calculator)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(SECTION_GAP)
        # Topo: ☰ e nome do modo à esquerda; histórico e tema numa cápsula à direita.
        self.menu_group = ToolGroup(self.theme, self.calculator)
        self.menu_group.add(self.menu_button)
        self.tools = ToolGroup(self.theme, self.calculator)
        self.tools.add(self.history_button)
        self.tools.add(self.theme_button)
        top = QHBoxLayout()
        top.setSpacing(10)
        self._top_row = top
        top.addWidget(self.menu_group, 0, Qt.AlignmentFlag.AlignTop)
        top.addWidget(self.mode_title, 1)
        top.addWidget(self.tools, 0, Qt.AlignmentFlag.AlignTop)
        column.addLayout(top)
        column.addWidget(self.display, 1)

        self.percentage_button = GlassButton("Porcentagem", self.theme, role="function", small=True, parent=self)
        self.percentage_button.setFixedSize(112, 28)
        self.percentage_button.setAccessibleName("Porcentagem")
        self.percentage_button.setToolTip("Abrir painel de porcentagem")
        self.percentage_button.clicked.connect(self.toggle_percentage_panel)
        # Fica no canto de cima do visor (só na aba Comum), sem ocupar uma linha própria.
        self.display.add_tool(self.percentage_button)

        column.addWidget(self.pages, 0)
        self._column = column

        self.percentage_panel = PercentagePanel(self.theme, self.calculator)
        self.percentage_panel.value_chosen.connect(self.insert_percentage_value)
        self.percentage_panel.close_requested.connect(self.close_percentage_panel)
        self.percentage_panel.hide()

        self.history_panel = HistoryPanel(self.theme, self.body)
        self.history_panel.setFixedWidth(PANEL_WIDTH)
        self.history_panel.value_chosen.connect(self.insert_history_value)
        self.history_panel.clear_requested.connect(self.ask_clear_history)
        self.history_panel.close_requested.connect(self.close_history_drawer)
        self.history_panel.show_entries(self.history.entries)
        self._drawer_animation = QPropertyAnimation(self.history_panel, b"pos", self)
        self._drawer_animation.setDuration(DRAWER_MS)
        drawer_spring = QEasingCurve(QEasingCurve.Type.OutBack)
        drawer_spring.setOvershoot(0.6)
        self._drawer_animation.setEasingCurve(drawer_spring)
        self._drawer_animation.finished.connect(self._drawer_animation_finished)

        self._root = QHBoxLayout(self.body)
        self._root.setContentsMargins(OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN, OUTER_MARGIN)
        self._root.setSpacing(OUTER_MARGIN)
        self._root.addWidget(self.calculator, 1)

        self.confirm_dialog: ConfirmDialog | None = None

        self.nav_menu = NavMenu(self.theme, self.tabs, central)
        self.tabs.tabBarClicked.connect(lambda _: self.close_menu())
        self.nav_menu.closed.connect(lambda: self.menu_button.setFocus(Qt.FocusReason.TabFocusReason)
                                     if self.menu_button.hasFocus() else None)
        self.theme.changed.connect(self._apply_title_color)
        self._apply_title_color()

        # --- preferências salvas ---
        self.set_angle_mode(self.preferences.angle_mode, save=False)
        for index, name in TAB_NAMES.items():
            if self.preferences.last_tab == name:
                self.tabs.setCurrentIndex(index)

        self.theme.apply()
        self._update_history_layout()
        self.percentage_button.setVisible(self.tabs.currentIndex() == COMMON_TAB)
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
        elif action == PARENTHESES:
            self.editor.parenthesis()
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
        # Como na Apple: o operador recém-escolhido fica destacado até a próxima tecla.
        last = editor.expression[-1:] if not editor.result else ""
        for keypad in (self.common_keypad, self.scientific_keypad):
            keypad.set_selected(last if last in OPERATOR_KEYS else None)

    # --- menu de modos ----------------------------------------------------------
    @property
    def menu_open(self) -> bool:
        return self.nav_menu.is_open

    def toggle_menu(self) -> None:
        if self.nav_menu.is_open:
            self.close_menu()
        else:
            self.open_menu()

    def open_menu(self) -> None:
        group = self.menu_group
        anchor = group.mapTo(self.centralWidget(), QPoint(0, group.height() + 6))
        self.nav_menu.open_at(anchor)
        # Contorno de foco na lista só para quem chegou pelo teclado.
        reason = (Qt.FocusReason.TabFocusReason if self.menu_button.keyboard_focus
                  else Qt.FocusReason.PopupFocusReason)
        self.tabs.setFocus(reason)

    def close_menu(self) -> None:
        self.nav_menu.close_menu()

    def _apply_title_color(self) -> None:
        set_text_color(self.mode_title, self.theme.color("text"))

    def _tab_changed(self, index: int) -> None:
        self.mode_title.setText(self.tabs.tabText(index))
        self.pages.setCurrentIndex(index)
        fade_in(self.pages.currentWidget(), self.theme)
        # A aba Trigonometria não usa o visor e dá o espaço do histórico ao círculo
        # (o histórico continua na gaveta, pelo botão de relógio).
        self.display.setVisible(index != TRIG_TAB)
        self.percentage_button.setVisible(index == COMMON_TAB)
        self._fit_keypad()
        if index != COMMON_TAB and self._percentage_open:
            self.close_percentage_panel()
        self._update_history_layout()
        self._place_body()
        if index in TAB_NAMES:
            self.preferences.update(last_tab=TAB_NAMES[index])

    # --- tema -----------------------------------------------------------------
    def _choose_other_theme(self) -> None:
        # A escolha feita no botão passa a valer sobre o tema do Windows.
        self.theme.toggle()
        self.preferences.update(theme=self.theme.name)

    def showEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().showEvent(event)
        set_dark_title_bar(self, self.theme.name == DARK)

    def _update_theme_button(self, name: str) -> None:
        set_dark_title_bar(self, name == DARK)
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
        self._slide(panel, QPoint(self.body.width(), target.y()), target.topLeft())
        self._update_history_button()
        first = panel.items[0] if panel.items else panel.close_button
        first.setFocus(Qt.FocusReason.TabFocusReason)

    def close_history_drawer(self) -> None:
        if not self._drawer_open:
            return
        self._drawer_open = False
        panel = self.history_panel
        self._slide(panel, panel.pos(), QPoint(self.body.width(), panel.y()))
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
        body = self.body
        top = self.tools.mapTo(body, QPoint(0, self.tools.height())).y() + 8
        width = min(PANEL_WIDTH + 20, body.width() - 48)
        rect = body.rect().adjusted(
            body.width() - width - OUTER_MARGIN, top, -OUTER_MARGIN, -OUTER_MARGIN
        )
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
        self.percentage_panel.setGeometry(self.percentage_area())

    def percentage_area(self):
        """Onde o painel de porcentagem aparece: do visor até o fim do teclado, alinhado às
        bordas das teclas (espaço para os campos e o resultado não ficarem apertados)."""
        pages = self.pages.geometry()
        top = self.display.geometry().top()
        grid = self.common_keypad.grid_rect
        left = pages.left() + max(0, int(grid.left()) - 4)
        right = pages.left() + min(pages.width(), int(grid.right()) + 4)
        return QRect(left, top, right - left, pages.bottom() - top + 1)

    def _update_percentage_button(self) -> None:
        label = "Fechar painel de porcentagem" if self._percentage_open else "Abrir painel de porcentagem"
        self.percentage_button.setToolTip(label)

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        self._update_history_layout()
        self._fit_keypad()
        self._update_percentage_layout()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 (nome do Qt)
        if event.type() == QEvent.Type.Resize:
            if watched is getattr(self, "calculator", None):
                self._fit_keypad()
            elif watched is self.centralWidget():
                self._place_body()
        return super().eventFilter(watched, event)

    def _place_body(self) -> None:
        """Centraliza o corpo (calculadora + histórico) com tamanho máximo, para a tela
        cheia não espalhar as peças pelos cantos."""
        if not hasattr(self, "body"):
            return
        central = self.centralWidget()
        if self.tabs.currentIndex() == TRIG_TAB:
            max_w, max_h = TRIG_MAX_SIZE
        else:
            keypad = self.current_keypad
            calc_w = keypad.max_grid_width() + 2 * KEY_PAD
            max_w = calc_w + 2 * OUTER_MARGIN
            if central.width() >= DOCK_MIN_WIDTH:
                max_w += OUTER_MARGIN + PANEL_WIDTH
            max_h = BODY_MAX_HEIGHT
        width = min(central.width(), max(max_w, MIN_WIDTH))
        height = min(central.height(), max_h)
        x = (central.width() - width) // 2
        y = (central.height() - height) // 2
        self.body.setGeometry(x, y, width, height)
        menu = getattr(self, "nav_menu", None)
        if menu is not None and menu.is_open:
            menu.setGeometry(central.rect())

    # --- medidas (teclado embaixo, visor ocupa o resto) -------------------------
    def _fit_keypad(self) -> None:
        """Teclado com a altura exata das teclas; o espaço que sobra fica com o visor,
        que encosta o número no teclado (como na Apple). Na Trigonometria, a aba ocupa tudo."""
        if not hasattr(self, "_column"):
            return
        if self.tabs.currentIndex() == TRIG_TAB:
            self._top_row.setContentsMargins(0, 0, 0, 0)
            self.pages.setMinimumHeight(0)
            self.pages.setMaximumHeight(16777215)
            self._column.setStretchFactor(self.pages, 1)
            return
        self._column.setStretchFactor(self.pages, 0)
        keypad = self.current_keypad
        width = self.calculator.width()
        room = (
            self.calculator.height() - self.tabs.sizeHint().height()
            - 2 * SECTION_GAP - self.display.minimumSizeHint().height() - 2
        )
        height = max(keypad.minimumSizeHint().height(), keypad.grid_height(width, room))
        if self.pages.height() != height or self.pages.maximumHeight() != height:
            self.pages.setFixedHeight(height)

    def _align_display(self) -> None:
        """Alinha a borda direita do número com a borda direita das teclas."""
        keypad = self.current_keypad
        if not isinstance(keypad, Keypad):
            return
        grid = keypad.grid_rect
        left = int(grid.left())
        right = int(keypad.width() - grid.right())
        self.display.set_side_margins(left, right)
        # O topo também acompanha as bordas das teclas (desde que tudo caiba).
        needed = (self.menu_group.sizeHint().width() + self.mode_title.sizeHint().width()
                  + self.tools.sizeHint().width() + 2 * self._top_row.spacing())
        room = self.calculator.width() - needed
        if left + right > room:
            left = right = max(0, room // 2)
        if self.tabs.currentIndex() != TRIG_TAB:
            self._top_row.setContentsMargins(left, 0, right, 0)

    # --- teclado físico ------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (nome do Qt)
        key = event.key()
        modifiers = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            super().keyPressEvent(event)
            return

        if key == Qt.Key.Key_Escape and self.nav_menu.is_open:
            self.close_menu()
            event.accept()
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
