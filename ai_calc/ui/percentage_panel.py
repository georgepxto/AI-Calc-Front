"""Painel de vidro para operações de porcentagem (Etapa 6B).

Permite calcular:
- Parte do total
- Variação percentual
- Valor original antes de um desconto

Permite também inserir o resultado na expressão da calculadora.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QFont, QKeyEvent, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.errors import CalcError, DivisionByZeroError, DomainError, OverflowCalcError
from ..core.formatting import format_number
from ..core.percentage import (
    original_before_discount,
    part_of_total,
    percentage_change,
)
from .glass import paint_glass, set_text_color
from .glass_button import GlassButton
from .glass_field import GlassField
from .tabs import GlassTabBar
from .theme import DISPLAY_ALPHA, ThemeManager

PANEL_RADIUS = 24


def _parse_number(text: str) -> float:
    """Converte texto com vírgula ou ponto para float."""
    text = text.strip().replace(",", ".")
    if not text:
        raise CalcError("Campo inválido")
    try:
        val = float(text)
    except ValueError:
        raise CalcError("Campo inválido")
    if not math.isfinite(val):
        raise OverflowCalcError()
    return val


class PercentagePanel(QFrame):
    """Painel de vidro com as operações de porcentagem."""

    value_chosen = Signal(str)      # texto pronto para o ExpressionEditor.insert_value
    close_requested = Signal()

    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("percentagePanel")
        self.setAccessibleName("Painel de porcentagem")
        self._theme = theme

        self._has_valid_result = False
        self._editor_insert_text = ""

        # --- Topo (Título + Botão fechar) ---
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        self.title = QLabel("Porcentagem", self)
        font = QFont(self.title.font())
        font.setPointSize(12)
        font.setBold(True)
        self.title.setFont(font)
        top_layout.addWidget(self.title)
        top_layout.addStretch(1)

        self.close_button = GlassButton("✕", theme, role="theme", small=True, parent=self)
        self.close_button.setAccessibleName("Fechar porcentagem")
        self.close_button.setToolTip("Fechar painel de porcentagem")
        self.close_button.setFixedSize(QSize(36, 30))
        self.close_button.clicked.connect(self.close_requested)
        top_layout.addWidget(self.close_button)

        # --- Abas de operações ---
        self.op_tabs = GlassTabBar(theme, self)
        self.op_tabs.setAccessibleName("Operação de porcentagem")
        self.op_tabs.addTab("Parte do total")
        self.op_tabs.addTab("Variação (%)")
        self.op_tabs.addTab("Valor original")
        self.op_tabs.currentChanged.connect(self._operation_changed)

        # --- Páginas de campos específicos ---
        self.fields_stack = QStackedWidget(self)

        # Operação 0: Parte do total
        p0 = QWidget(self.fields_stack)
        l0 = QVBoxLayout(p0)
        l0.setContentsMargins(0, 0, 0, 0)
        l0.setSpacing(6)
        self.part_field = GlassField("Parte", theme, p0)
        self.total_field = GlassField("Total", theme, p0)
        l0.addWidget(self.part_field)
        l0.addWidget(self.total_field)
        self.fields_stack.addWidget(p0)

        # Operação 1: Variação (%)
        p1 = QWidget(self.fields_stack)
        l1 = QVBoxLayout(p1)
        l1.setContentsMargins(0, 0, 0, 0)
        l1.setSpacing(6)
        self.initial_field = GlassField("Valor inicial", theme, p1)
        self.final_field = GlassField("Valor final", theme, p1)
        l1.addWidget(self.initial_field)
        l1.addWidget(self.final_field)
        self.fields_stack.addWidget(p1)

        # Operação 2: Valor original
        p2 = QWidget(self.fields_stack)
        l2 = QVBoxLayout(p2)
        l2.setContentsMargins(0, 0, 0, 0)
        l2.setSpacing(6)
        self.discount_final_field = GlassField("Valor final", theme, p2)
        self.discount_rate_field = GlassField("Desconto (%)", theme, p2)
        l2.addWidget(self.discount_final_field)
        l2.addWidget(self.discount_rate_field)
        self.fields_stack.addWidget(p2)

        # Conectar mudanças de texto e capturar atalhos (ex.: Esc) de todos os campos
        for f in (
            self.part_field,
            self.total_field,
            self.initial_field,
            self.final_field,
            self.discount_final_field,
            self.discount_rate_field,
        ):
            f.edit.textChanged.connect(self._fields_edited)
            f.edit.installEventFilter(self)

        # --- Área de exibição de fórmula, resultado e erro ---
        self.formula_label = QLabel(self)
        self.formula_label.setAccessibleName("Fórmula da porcentagem")
        self.formula_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        formula_font = QFont(self.formula_label.font())
        formula_font.setPointSize(9)
        self.formula_label.setFont(formula_font)

        self.result_label = QLabel(self)
        self.result_label.setAccessibleName("Resultado da porcentagem")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        res_font = QFont(self.result_label.font())
        res_font.setPointSize(18)
        res_font.setBold(True)
        self.result_label.setFont(res_font)

        self.message_label = QLabel(self)
        self.message_label.setAccessibleName("Mensagem de erro")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        msg_font = QFont(self.message_label.font())
        msg_font.setPointSize(10)
        msg_font.setBold(True)
        self.message_label.setFont(msg_font)

        # --- Botão Usar resultado ---
        self.use_result_button = GlassButton("Usar resultado", theme, role="equals", parent=self)
        self.use_result_button.setAccessibleName("Usar resultado na conta")
        self.use_result_button.setToolTip("Inserir o resultado na expressão da calculadora")
        self.use_result_button.setFixedHeight(38)
        self.use_result_button.setEnabled(False)
        self.use_result_button.clicked.connect(self.use_result)

        # --- Montagem do layout principal ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(top_layout)
        layout.addWidget(self.op_tabs)
        layout.addWidget(self.fields_stack)
        layout.addWidget(self.formula_label)
        layout.addWidget(self.result_label)
        layout.addWidget(self.message_label)
        layout.addStretch(1)
        layout.addWidget(self.use_result_button)

        theme.changed.connect(self.apply_colors)
        self.apply_colors()
        self._update_tab_order()

    def set_operation(self, index: int) -> None:
        """Seleciona a operação (0: Parte do total, 1: Variação, 2: Valor original)."""
        self.op_tabs.setCurrentIndex(index)

    def focus_first_field(self) -> None:
        idx = self.op_tabs.currentIndex()
        if idx == 0:
            self.part_field.edit.setFocus(Qt.FocusReason.TabFocusReason)
        elif idx == 1:
            self.initial_field.edit.setFocus(Qt.FocusReason.TabFocusReason)
        else:
            self.discount_final_field.edit.setFocus(Qt.FocusReason.TabFocusReason)

    def result_text(self) -> str:
        return self.result_label.text()

    def formula_text(self) -> str:
        return self.formula_label.text()

    def message_text(self) -> str:
        return self.message_label.text()

    def _fields_edited(self, _text: str | None = None) -> None:
        """Invalida o resultado e calcula se os dois campos da operação estiverem preenchidos."""
        self._invalidate()
        f1, f2 = self._active_fields()
        t1, t2 = f1.edit.text().strip(), f2.edit.text().strip()
        if not t1 or not t2:
            return
        self.calculate()

    def _operation_changed(self, index: int) -> None:
        self.fields_stack.setCurrentIndex(index)
        self._invalidate()
        self._update_tab_order()
        self._fields_edited()

    def _active_fields(self) -> tuple[GlassField, GlassField]:
        idx = self.op_tabs.currentIndex()
        if idx == 0:
            return self.part_field, self.total_field
        if idx == 1:
            return self.initial_field, self.final_field
        return self.discount_final_field, self.discount_rate_field

    def _invalidate(self) -> None:
        self._has_valid_result = False
        self._editor_insert_text = ""
        self.use_result_button.setEnabled(False)
        self.result_label.setText("")
        self.formula_label.setText("")
        self.message_label.setText("")

    def calculate(self) -> None:
        """Executa o cálculo para a operação ativa."""
        f1, f2 = self._active_fields()
        t1 = f1.edit.text().strip()
        t2 = f2.edit.text().strip()
        idx = self.op_tabs.currentIndex()

        try:
            val1 = _parse_number(t1)
            val2 = _parse_number(t2)

            if idx == 0:
                # Parte do total: rate = part / total
                rate = part_of_total(val1, val2)
                pct_value = rate * 100.0
                display_str = f"{format_number(pct_value).replace('-', '−')}%"
                formula_str = f"{t1} de {t2}"
                editor_str = format_number(rate)
            elif idx == 1:
                # Variação percentual: rate = (final - initial) / initial
                rate = percentage_change(val1, val2)
                pct_value = rate * 100.0
                display_str = f"{format_number(pct_value).replace('-', '−')}%"
                formula_str = f"De {t1} para {t2}"
                editor_str = format_number(rate)
            else:
                # Valor original antes do desconto: final / (1 - discount_rate)
                # No campo Desconto (%), converte uma vez dividindo por 100
                discount_rate = val2 / 100.0
                orig = original_before_discount(val1, discount_rate)
                display_str = format_number(orig)
                formula_str = f"{t1} com {t2}% de desconto"
                editor_str = format_number(orig)

            self._has_valid_result = True
            self._editor_insert_text = editor_str
            self.result_label.setText(display_str)
            self.formula_label.setText(formula_str)
            self.message_label.setText("")
            self.use_result_button.setEnabled(True)

        except CalcError as err:
            self._has_valid_result = False
            self._editor_insert_text = ""
            self.result_label.setText("")
            self.formula_label.setText("")
            self.message_label.setText(err.message)
            self.use_result_button.setEnabled(False)

    def use_result(self) -> None:
        """Insere o resultado válido na conta atual da calculadora."""
        if self._has_valid_result and self._editor_insert_text:
            self.value_chosen.emit(self._editor_insert_text)

    def _update_tab_order(self) -> None:
        f1, f2 = self._active_fields()
        QWidget.setTabOrder(self.op_tabs, f1.edit)
        QWidget.setTabOrder(f1.edit, f2.edit)
        QWidget.setTabOrder(f2.edit, self.use_result_button)
        QWidget.setTabOrder(self.use_result_button, self.close_button)

    def apply_colors(self) -> None:
        theme = self._theme
        set_text_color(self.title, theme.color("text"))
        set_text_color(self.formula_label, theme.color("text_muted"))
        set_text_color(self.result_label, theme.color("text"))
        set_text_color(self.message_label, theme.color("error"))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -3)
        theme = self._theme
        paint_glass(painter, rect, PANEL_RADIUS, theme, theme.hex("display_bg"), DISPLAY_ALPHA)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 (nome do Qt)
        if event.type() == QEvent.Type.KeyPress:
            key_event: QKeyEvent = event  # type: ignore
            if key_event.key() == Qt.Key.Key_Escape:
                self.close_requested.emit()
                return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (nome do Qt)
        if event.key() == Qt.Key.Key_Escape:
            self.close_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


__all__ = ["PercentagePanel"]
