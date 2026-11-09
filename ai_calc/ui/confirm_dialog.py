"""Janela de confirmação de vidro (sem o estilo padrão do Windows)."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .glass import paint_glass, set_text_color, with_alpha
from .glass_button import GlassButton
from .theme import DIALOG_ALPHA, DIM_ALPHA, ThemeManager

CARD_WIDTH = 320
CARD_RADIUS = 16


class _Card(QFrame):
    def __init__(self, theme: ThemeManager, parent: QWidget) -> None:
        super().__init__(parent)
        self._theme = theme

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -3)
        theme = self._theme
        paint_glass(painter, rect, CARD_RADIUS, theme, theme.hex("display_bg"), DIALOG_ALPHA)


class ConfirmDialog(QDialog):
    """Escurece a janela por trás e mostra um cartão com Cancelar e a ação.

    Cancelar começa com o foco (a opção segura). Esc cancela; Tab circula
    só dentro do cartão.
    """

    def __init__(
        self,
        theme: ThemeManager,
        parent: QWidget,
        title: str,
        text: str,
        confirm_label: str,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setAccessibleName(title)
        self.setAccessibleDescription(text)
        self._theme = theme

        self.card = _Card(theme, self)
        self.card.setFixedWidth(CARD_WIDTH)

        self.title_label = QLabel(title, self.card)
        font = QFont(self.title_label.font())
        font.setPointSize(13)
        font.setBold(True)
        self.title_label.setFont(font)
        self.text_label = QLabel(text, self.card)
        self.text_label.setWordWrap(True)

        self.cancel_button = GlassButton("Cancelar", theme, role="digit", small=True, parent=self.card)
        self.cancel_button.setAccessibleName("Cancelar")
        self.confirm_button = GlassButton(confirm_label, theme, role="action", small=True, parent=self.card)
        self.confirm_button.setAccessibleName(confirm_label)
        for button in (self.cancel_button, self.confirm_button):
            button.setMinimumHeight(40)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.setAutoDefault(True)
        self.cancel_button.setDefault(True)
        self.cancel_button.clicked.connect(self.reject)
        self.confirm_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.confirm_button)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 16, 18, 18)
        card_layout.setSpacing(10)
        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.text_label)
        card_layout.addSpacing(4)
        card_layout.addLayout(buttons)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addStretch(1)
        outer.addWidget(self.card, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        theme.changed.connect(self.apply_colors)
        self.apply_colors()

    def apply_colors(self) -> None:
        set_text_color(self.title_label, self._theme.color("text"))
        set_text_color(self.text_label, self._theme.color("text"))
        self.update()

    def showEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        # Cobre a janela principal inteira (para escurecê-la por trás do cartão).
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(QRect(parent.mapToGlobal(QPoint(0, 0)), parent.size()))
            self.card.setFixedWidth(min(CARD_WIDTH, parent.width() - 32))
        super().showEvent(event)
        self.activateWindow()
        self.cancel_button.setFocus()

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.fillRect(self.rect(), with_alpha(self._theme.hex("shadow"), DIM_ALPHA))
