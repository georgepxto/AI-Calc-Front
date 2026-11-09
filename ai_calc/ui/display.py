"""Visor: conta em edição, resultado e uma linha de mensagem.

Como na calculadora da Apple, não há caixa em volta: o número fica grande e fino
direto sobre o fundo, alinhado à direita.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics, QPalette
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .theme import ThemeManager

RESULT_POINT_SIZE = 50
RESULT_MIN_POINT_SIZE = 16


def _point_size(label: QLabel, size: int, bold: bool = False, light: bool = False) -> None:
    font = QFont(label.font())
    font.setPointSize(size)
    font.setBold(bold)
    if light:
        font.setWeight(QFont.Weight.Light)
    label.setFont(font)


class Display(QFrame):
    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("display")
        self._theme = theme
        self._expression = ""
        self._result = ""
        self._is_error = False

        self.expression_label = QLabel(self)
        self.expression_label.setObjectName("expression")
        self.expression_label.setAccessibleName("Conta")

        self.result_label = QLabel(self)
        self.result_label.setObjectName("result")
        self.result_label.setAccessibleName("Resultado")
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.message_label = QLabel(self)
        self.message_label.setObjectName("message")
        self.message_label.setAccessibleName("Mensagem")

        self.angle_mode_label = QLabel("DEG", self)
        self.angle_mode_label.setObjectName("angleMode")
        self.angle_mode_label.setAccessibleName("Modo de ângulo")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(2)
        layout.addStretch(1)       # o número fica embaixo, encostado no teclado
        self._layout = layout
        top = QHBoxLayout()
        top.setSpacing(8)
        self._top = top
        self.angle_mode_label.setContentsMargins(0, 0, 4, 0)
        top.addWidget(self.angle_mode_label, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.expression_label, 1)
        layout.addLayout(top)
        for label in (self.expression_label, self.result_label, self.message_label):
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.result_label)
        layout.addWidget(self.message_label)
        self.expression_label.setMinimumHeight(20)

        _point_size(self.expression_label, 12)
        _point_size(self.angle_mode_label, 9, bold=True)
        _point_size(self.result_label, RESULT_POINT_SIZE, light=True)
        _point_size(self.message_label, 10)
        # Alturas fixas: o visor não cresce quando aparece uma mensagem, e a janela
        # pode reservar o espaço exato dele ao medir o teclado.
        self.result_label.setFixedHeight(QFontMetrics(self.result_label.font()).height())
        self.message_label.setFixedHeight(20)
        self.message_label.setWordWrap(False)
        theme.changed.connect(self.apply_colors)
        self.apply_colors()

    def apply_colors(self) -> None:
        """Cor do texto de cada linha, vinda do tema (inclusive no meio da transição)."""
        theme = self._theme
        message_key = "error" if self._is_error else "text_muted"
        for label, key in (
            (self.expression_label, "text_muted"),
            (self.angle_mode_label, "text_muted"),
            (self.result_label, "text"),
            (self.message_label, message_key),
        ):
            palette = label.palette()
            palette.setColor(QPalette.ColorRole.WindowText, theme.color(key))
            label.setPalette(palette)
        self.update()

    # Sem caixa nem chips: o visor é só texto sobre o fundo, como no macOS (nada a pintar).

    def set_side_margins(self, left: int, right: int) -> None:
        """Margens dos lados (o número alinha com a borda das teclas)."""
        margins = self._layout.contentsMargins()
        if (margins.left(), margins.right()) != (left, right):
            self._layout.setContentsMargins(left, margins.top(), right, margins.bottom())
            self._refresh()

    def add_tool(self, widget: QWidget) -> None:
        """Põe um botão pequeno no canto de cima, ao lado do modo de ângulo."""
        self._top.insertWidget(1, widget, 0, Qt.AlignmentFlag.AlignVCenter)

    def show_state(self, expression: str, result: str, message: str, is_error: bool) -> None:
        self._expression = expression
        self._result = result
        self.message_label.setText(message)
        if is_error != self._is_error:
            self._is_error = is_error
            _point_size(self.message_label, 10, bold=is_error)
            self.apply_colors()
        self._refresh()

    def show_angle_mode(self, mode: str) -> None:
        self.angle_mode_label.setText(mode)
        name = "graus" if mode == "DEG" else "radianos"
        self.angle_mode_label.setAccessibleName(f"Modo de ângulo: {name}")

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        width = max(10, self.contentsRect().width() - self._layout.contentsMargins().left() - self._layout.contentsMargins().right())

        # Enquanto se digita, a conta fica na linha grande; depois do "=",
        # ela sobe para a linha de cima e o resultado ocupa a linha grande.
        top = self._expression if self._result else ""
        metrics = QFontMetrics(self.expression_label.font())
        others = sum(
            item.widget().sizeHint().width() + 8
            for item in (self._top.itemAt(i) for i in range(self._top.count()))
            if item.widget() is not None and item.widget() is not self.expression_label
            and not item.widget().isHidden()
        )
        top_width = max(10, width - others)
        self.expression_label.setText(metrics.elidedText(top, Qt.TextElideMode.ElideLeft, top_width))
        self.expression_label.setToolTip(top)

        # Texto longo mostra o final (onde se está digitando) e a fonte diminui até caber.
        shown = self._result or self._expression or "0"
        self.result_label.setToolTip(shown)
        font = QFont(self.result_label.font())
        size = RESULT_POINT_SIZE
        font.setPointSize(size)
        while size > RESULT_MIN_POINT_SIZE and QFontMetrics(font).horizontalAdvance(shown) > width:
            size -= 1
            font.setPointSize(size)
        self.result_label.setFont(font)
        self.result_label.setText(
            QFontMetrics(font).elidedText(shown, Qt.TextElideMode.ElideLeft, width)
        )
