"""Campo de texto de vidro com rótulo ("Ângulo", "Seno")."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPalette
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from .glass import paint_focus_ring, paint_glass, set_text_color
from .theme import KEY_ALPHA, ThemeManager

FIELD_RADIUS = 999     # campo em cápsula (o raio é limitado à metade da altura)
FIELD_HEIGHT = 40
TEXT_POINT_SIZE = 11
TEXT_MIN_POINT_SIZE = 8     # texto longo diminui até aqui antes de rolar dentro do campo


class GlassField(QWidget):
    """Rótulo + caixa de texto sobre vidro. Emite "submitted" com o texto ao apertar Enter
    ou ao sair do campo depois de mudar o texto."""

    submitted = Signal(str)

    def __init__(self, caption: str, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._shown_text = ""
        self.setFixedHeight(FIELD_HEIGHT)

        self.caption = QLabel(caption, self)
        font = QFont(self.caption.font())
        font.setPointSize(10)
        self.caption.setFont(font)

        self.edit = QLineEdit(self)
        self.edit.setFrame(False)
        self.edit.setAccessibleName(caption)
        self.edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.caption.setBuddy(self.edit)
        self.edit.installEventFilter(self)
        self.edit.editingFinished.connect(self._finished)
        self.edit.textChanged.connect(lambda _: self._fit_text())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 2, 16, 4)
        layout.setSpacing(8)
        layout.addWidget(self.caption)
        layout.addWidget(self.edit, 1)

        theme.changed.connect(self.apply_colors)
        self.apply_colors()

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        self._fit_text()

    def _fit_text(self) -> None:
        """Diminui a fonte quando o texto não cabe (ex.: seno 0,707106781187 na janela estreita)."""
        room = self.edit.width() - 8
        font = QFont(self.edit.font())
        size = TEXT_POINT_SIZE
        font.setPointSize(size)
        while size > TEXT_MIN_POINT_SIZE and QFontMetrics(font).horizontalAdvance(self.edit.text()) > room:
            size -= 1
            font.setPointSize(size)
        if font.pointSize() != self.edit.font().pointSize():
            self.edit.setFont(font)

    def show_value(self, text: str) -> None:
        """Mostra o valor atual, sem atrapalhar quem está digitando no campo."""
        if not self.edit.hasFocus():
            self.edit.setText(text)
            self._shown_text = text

    def set_value(self, text: str) -> None:
        """Troca o texto mesmo com o foco no campo (depois de o usuário confirmar um valor)."""
        self.edit.setText(text)
        self._shown_text = text

    def _finished(self) -> None:
        text = self.edit.text()
        if text != self._shown_text:
            self._shown_text = text
            self.submitted.emit(text)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 (nome do Qt)
        if watched is self.edit and event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
            self.update()   # liga/desliga o contorno de foco
        return super().eventFilter(watched, event)

    def apply_colors(self) -> None:
        theme = self._theme
        set_text_color(self.caption, theme.color("text_muted"))
        palette = self.edit.palette()
        palette.setColor(QPalette.ColorRole.Text, theme.color("text"))
        palette.setColor(QPalette.ColorRole.Base, QColor(0, 0, 0, 0))
        palette.setColor(QPalette.ColorRole.PlaceholderText, theme.color("text_muted"))
        palette.setColor(QPalette.ColorRole.Highlight, theme.color("tab_selected_bg"))
        palette.setColor(QPalette.ColorRole.HighlightedText, theme.color("tab_selected_text"))
        self.edit.setPalette(palette)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -3.0)
        theme = self._theme
        paint_glass(painter, rect, FIELD_RADIUS, theme, theme.hex("key_bg"), KEY_ALPHA)
        if self.edit.hasFocus():
            paint_focus_ring(painter, rect, FIELD_RADIUS, theme.color("focus"))
