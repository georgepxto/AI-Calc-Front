"""Janela principal: abas, botões do topo, visor, teclados e histórico.

A lógica fica no core (editor, histórico e preferências); aqui só se liga
cada peça e se mostra o estado.
"""

from __future__ import annotations

import string

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from ..core.editor import KEY_ALIASES, ExpressionEditor
from ..core.history import History
from ..core.preferences import Preferences
from .confirm_dialog import ConfirmDialog
from .display import Display
from .glass import Backdrop, set_text_color
from .glass_button import GlassButton, HistoryToggleButton, ModeButton, ThemeToggleButton
from .history_panel import HistoryPanel
from .nav_menu import NavMenu
from .percentage_panel import PercentagePanel
from .motion import fade_in
from .keypad import (
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

OUTER_MARGIN = 16      # margem dos cartões por cima (gaveta, menu)
CALC_MARGIN = 16       # margem da calculadora dentro da janela
SECTION_GAP = 12       # espaço entre topo, visor e teclado

# Histórico: painel fixo ao lado quando a janela é larga; gaveta com botão quando é estreita.
DOCK_MIN_WIDTH = 660
PANEL_WIDTH = 260
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
        self._sidebar_hidden = False
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

        # Seletor de modo no centro do topo ("Científica ⌄"), que abre a lista de modos.
        self.mode_title = ModeButton(self.tabs.tabText(0), self.theme, self)
        self.mode_title.setAccessibleName("Escolher modo da calculadora")
        self.mode_title.setToolTip("Escolher modo")
        self.mode_title.clicked.connect(self.toggle_menu)
        self.menu_button = self.mode_title

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
        column.setContentsMargins(CALC_MARGIN, 8, CALC_MARGIN, CALC_MARGIN + 6)
        column.setSpacing(SECTION_GAP)
        # Topo: barra lateral à esquerda, modo no centro e tema à direita (como no macOS).
        top = QHBoxLayout()
        top.setSpacing(0)
        top.setContentsMargins(0, 0, 0, 0)
        self._top_row = top
        top.addWidget(self.history_button, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addStretch(1)
        top.addWidget(self.mode_title, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addStretch(1)
        top.addWidget(self.theme_button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.menu_group = self.mode_title
        self.tools = self.theme_button
        column.addLayout(top)
        column.addWidget(self.display, 1)

        self.percentage_button = GlassButton("Porcentagem", self.theme, role="function", small=True,
                                             parent=self, flat=True)
        self.percentage_button.setFixedSize(104, 26)
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
        # Histórico encostado à esquerda (barra lateral) e calculadora ao lado, sem margens.
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)
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
        anchor = group.mapTo(self.centralWidget(), QPoint(group.width() // 2, group.height() + 6))
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
        if self.history_wide:
            # Janela larga: o botão esconde/mostra a barra lateral (como no macOS).
            self._sidebar_hidden = not self._sidebar_hidden
            self._update_history_layout()
            self._place_body()
            return
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
        self._slide(panel, QPoint(-target.width(), target.y()), target.topLeft())
        self._update_history_button()
        first = panel.items[0] if panel.items else panel.close_button
        # Contorno de foco só para quem abriu pelo teclado.
        reason = (Qt.FocusReason.TabFocusReason if self.history_button.keyboard_focus
                  else Qt.FocusReason.PopupFocusReason)
        first.setFocus(reason)

    def close_history_drawer(self) -> None:
        if not self._drawer_open:
            return
        self._drawer_open = False
        panel = self.history_panel
        self._slide(panel, panel.pos(), QPoint(-panel.width(), panel.y()))
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
        top = self.history_button.mapTo(body, QPoint(0, self.history_button.height())).y() + 8
        width = min(PANEL_WIDTH + 20, body.width() - 48)
        return QRect(OUTER_MARGIN, top, width, body.height() - top - OUTER_MARGIN)

    @property
    def history_wide(self) -> bool:
        """Janela larga o bastante para o histórico ficar como barra lateral."""
        return self.width() >= DOCK_MIN_WIDTH and self.tabs.currentIndex() != TRIG_TAB

    def _update_history_layout(self) -> None:
        if not hasattr(self, "_root"):
            return                       # ainda montando a janela
        docked = self.history_wide and not self._sidebar_hidden
        panel = self.history_panel
        if docked and not self._docked:
            self._drawer_animation.stop()
            self._drawer_open = False
            panel.set_drawer_mode(False)
            panel.setFixedWidth(PANEL_WIDTH)
            panel.setMinimumHeight(0)
            panel.setMaximumHeight(16777215)
            self._root.insertWidget(0, panel)
            panel.show()
        elif not docked and (self._docked or not panel.isHidden() and not self._drawer_open):
            self._root.removeWidget(panel)
            panel.hide()
        self._docked = docked
        if self._drawer_open:
            target = self._drawer_geometry()
            panel.setFixedSize(target.size())
            panel.move(target.topLeft())
        self._update_history_button()

    def _update_history_button(self) -> None:
        showing = self._drawer_open or self._docked
        label = "Esconder histórico" if showing else "Mostrar histórico"
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
        """O corpo ocupa a janela toda: barra lateral encostada à esquerda, como no macOS.
        Em telas grandes, quem se centraliza é o conteúdo da calculadora (ver _fit_keypad);
        na Trigonometria, o conteúdo tem tamanho máximo e fica no meio."""
        if not hasattr(self, "body"):
            return
        central = self.centralWidget()
        if self.tabs.currentIndex() == TRIG_TAB:
            width = min(central.width(), TRIG_MAX_SIZE[0])
            height = min(central.height(), TRIG_MAX_SIZE[1])
            self.body.setGeometry((central.width() - width) // 2, (central.height() - height) // 2,
                                  width, height)
        else:
            self.body.setGeometry(central.rect())
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
            self.pages.setMinimumHeight(0)
            self.pages.setMaximumHeight(16777215)
            self._column.setStretchFactor(self.pages, 1)
            return
        self._column.setStretchFactor(self.pages, 0)
        keypad = self.current_keypad
        # Tela grande: visor e teclado sobem para perto do meio, em vez de grudar no rodapé.
        extra = max(0, self.calculator.height() - BODY_MAX_HEIGHT)
        bottom = CALC_MARGIN + 6 + extra // 2
        margins = self._column.contentsMargins()
        if margins.bottom() != bottom:
            self._column.setContentsMargins(margins.left(), margins.top(), margins.right(), bottom)
            margins = self._column.contentsMargins()
        width = self.calculator.width() - margins.left() - margins.right()
        room = (
            self.calculator.height() - margins.top() - margins.bottom()
            - self.history_button.sizeHint().height()
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
        # O topo fica na largura da janela (barra lateral à esquerda, tema à direita).

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
