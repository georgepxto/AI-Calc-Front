"""Painel de vidro do histórico: lista de contas, barra de rolagem e botão Limpar."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QStyle,
    QStyleOptionSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.history import HistoryEntry
from .glass import paint_glass, set_text_color, with_alpha
from .glass_button import GlassButton, TrashButton
from .theme import DIALOG_ALPHA, DISPLAY_ALPHA, ThemeManager

PANEL_RADIUS = 16
ITEM_HEIGHT = 56
ITEM_RADIUS = 8
MODE_NAMES = {"DEG": "graus", "RAD": "radianos"}


class HistoryItemButton(GlassButton):
    """Um item do histórico: conta em cima (discreta), resultado embaixo e etiqueta DEG/RAD.

    Sem vidro próprio: os itens formam uma lista dentro do painel, separados por
    uma linha fina; passar o mouse ou apertar realça o item.
    """

    def __init__(self, entry: HistoryEntry, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(entry.result, theme, role="history", small=True, parent=parent, flat=True)
        self.entry = entry
        self.separator = False      # linha fina embaixo (todos menos o último)
        self.setFixedHeight(ITEM_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        mode = f", {MODE_NAMES[entry.angle_mode]}" if entry.angle_mode else ""
        name = f"{entry.expression} igual a {entry.result}{mode}"
        self.setAccessibleName(name)
        self.setAccessibleDescription("Insere o resultado na conta atual")
        self.setToolTip(f"{entry.expression} = {entry.result}\nClique para inserir {entry.result}")

    def radius(self, rect: QRectF) -> float:
        return ITEM_RADIUS

    def paint_content(self, painter: QPainter, rect: QRectF, color) -> None:
        inner = rect.adjusted(12, 6, -12, -6)
        theme = self._theme

        if self.separator and self._press == 0 and self._hover == 0:
            line = with_alpha(theme.hex("text_muted"), 0.16)
            painter.setPen(QPen(line, 1.0))
            y = rect.bottom() + 0.5
            painter.drawLine(QPointF(rect.left() + 12, y), QPointF(rect.right() - 12, y))

        small = QFont(self.font())
        small.setPointSize(9)
        painter.setFont(small)
        painter.setPen(theme.color("text_muted"))
        top = QRectF(inner.left(), inner.top(), inner.width(), inner.height() / 2)
        expression = QFontMetrics(small).elidedText(
            self.entry.expression, Qt.TextElideMode.ElideLeft, int(top.width())
        )
        painter.drawText(top, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, expression)
        bottom = QRectF(inner.left(), inner.center().y(), inner.width(), inner.height() / 2)
        if self.entry.angle_mode:
            # Etiqueta DEG/RAD num chip discreto, como no visor.
            chip_font = QFont(small)
            chip_font.setBold(True)
            painter.setFont(chip_font)
            text_width = QFontMetrics(chip_font).horizontalAdvance(self.entry.angle_mode)
            chip = QRectF(bottom.left(), bottom.center().y() - 9, text_width + 14, 18)
            path = QPainterPath()
            path.addRoundedRect(chip, 9, 9)
            painter.fillPath(path, with_alpha(theme.hex("text_muted"), 0.12))
            painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, self.entry.angle_mode)

        big = QFont(self.font())
        big.setPointSize(13)
        big.setWeight(QFont.Weight.Medium)
        painter.setFont(big)
        painter.setPen(color)
        result = QFontMetrics(big).elidedText(
            self.entry.result, Qt.TextElideMode.ElideLeft, int(bottom.width() - 40)
        )
        painter.drawText(bottom, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, result)


class GlassScrollBar(QScrollBar):
    """Barra de rolagem fina, desenhada com as cores do tema."""

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)
        self._theme = theme
        self.setFixedWidth(8)

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        track = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        painter.setBrush(with_alpha(self._theme.hex("glass_rim"), 0.18))
        painter.drawRoundedRect(track, 2, 2)

        option = QStyleOptionSlider()
        self.initStyleOption(option)
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_ScrollBar, option, QStyle.SubControl.SC_ScrollBarSlider, self
        )
        painter.setBrush(self._theme.color("scroll_handle"))
        painter.drawRoundedRect(QRectF(handle).adjusted(2, 1, -2, -1), 2, 2)


class HistoryPanel(QFrame):
    value_chosen = Signal(str)      # número do resultado escolhido
    clear_requested = Signal()
    close_requested = Signal()

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("historyPanel")
        self.setAccessibleName("Histórico")
        self._theme = theme
        self._entries: list[HistoryEntry] = []
        self._alpha = DISPLAY_ALPHA

        self.title = QLabel("Histórico", self)
        title_font = QFont(self.title.font())
        title_font.setPointSize(10)
        title_font.setWeight(QFont.Weight.DemiBold)
        self.title.setFont(title_font)

        self.clear_button = TrashButton(theme, self)
        self.clear_button.setAccessibleName("Limpar histórico")
        self.clear_button.setToolTip("Limpar histórico")
        self.clear_button.clicked.connect(self.clear_requested)

        self.close_button = GlassButton("✕", theme, role="theme", small=True, parent=self)
        self.close_button.setAccessibleName("Fechar histórico")
        self.close_button.setToolTip("Fechar histórico")
        self.close_button.setFixedSize(QSize(30, 30))
        self.close_button.clicked.connect(self.close_requested)
        self.close_button.hide()

        self.empty_label = QLabel("Nenhuma conta ainda.\nAs contas feitas aparecem aqui.", self)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)

        self._list = QWidget()
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 4, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch(1)

        self.scroll = QScrollArea(self)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBar(GlassScrollBar(theme))
        self.scroll.setWidget(self._list)
        self.scroll.setAccessibleName("Lista de contas")
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)   # o Tab vai direto aos itens
        # Fundo transparente: o vidro do painel aparece por trás da lista.
        self.scroll.viewport().setAutoFillBackground(False)
        self._list.setAutoFillBackground(False)

        header = QHBoxLayout()
        header.setContentsMargins(8, 0, 4, 0)
        header.setSpacing(4)
        header.addWidget(self.title, 1)
        header.addWidget(self.clear_button)
        header.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 4, 10)
        layout.setSpacing(6)
        self._layout = layout
        layout.addLayout(header)
        layout.addWidget(self.empty_label, 1)
        layout.addWidget(self.scroll, 1)

        theme.changed.connect(self.apply_colors)
        self.apply_colors()
        self.show_entries([])

    @property
    def items(self) -> list[HistoryItemButton]:
        return self._list.findChildren(HistoryItemButton)

    def set_drawer_mode(self, drawer: bool) -> None:
        # Fixo: barra lateral plana encostada na borda. Gaveta: cartão sólido por cima.
        self.close_button.setVisible(drawer)
        self._alpha = DIALOG_ALPHA if drawer else DISPLAY_ALPHA
        self.update()

    @property
    def drawer_mode(self) -> bool:
        return self._alpha == DIALOG_ALPHA

    def show_entries(self, entries: list[HistoryEntry]) -> None:
        self._entries = list(entries)
        for item in self.items:
            item.setParent(None)
            item.deleteLater()
        for index, entry in enumerate(self._entries):
            item = HistoryItemButton(entry, self._theme, self._list)
            item.separator = index < len(self._entries) - 1
            item.clicked.connect(lambda _=False, r=entry.result: self.value_chosen.emit(r))
            self._list_layout.insertWidget(index, item)
            item.show()   # visível já, para entrar na conta da altura logo abaixo
        # Altura mínima da lista = soma dos itens; assim a rolagem aparece em vez de apertar.
        self._list_layout.activate()
        self._list.setMinimumHeight(self._list_layout.minimumSize().height())
        empty = not self._entries
        self.empty_label.setVisible(empty)
        self.scroll.setVisible(not empty)
        self.clear_button.setEnabled(not empty)

    def apply_colors(self) -> None:
        set_text_color(self.title, self._theme.color("text"))
        set_text_color(self.empty_label, self._theme.color("text_muted"))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        theme = self._theme
        if not self.drawer_mode:
            # Barra lateral (como no macOS): superfície plana e um fio separando da calculadora.
            painter.fillRect(self.rect(), with_alpha(theme.hex("display_bg"), self._alpha))
            painter.setPen(QPen(with_alpha(theme.hex("text_muted"), 0.18), 1.0))
            x = self.width() - 0.5
            painter.drawLine(QPointF(x, 0), QPointF(x, self.height()))
            return
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -4)
        if self._alpha == DIALOG_ALPHA:
            # Gaveta por cima do teclado: sem desfoque real, qualquer transparência deixaria as
            # teclas aparecendo como "fantasmas". Uma base sólida por baixo do vidro resolve.
            base = QPainterPath()
            base.addRoundedRect(rect, PANEL_RADIUS, PANEL_RADIUS)
            painter.fillPath(base, theme.color("window_bottom"))
        paint_glass(painter, rect, PANEL_RADIUS, theme, theme.hex("display_bg"), self._alpha)
