"""Teclado na tela: monta a grade de botões a partir de uma lista de teclas."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QWidget

from .glass_button import GlassButton
from .theme import ThemeManager

# Ações especiais (as demais teclas só inserem o próprio texto).
CLEAR = "clear"
BACKSPACE = "backspace"
EVALUATE = "evaluate"
ANGLE_MODE = "angle_mode"


@dataclass(frozen=True)
class Key:
    label: str
    accessible_name: str
    role: str                  # "digit", "operator", "function", "action" ou "equals" (cor)
    insert: str | None = None  # texto inserido; None quando é uma ação
    action: str | None = None
    column_span: int = 1
    small: bool = False        # fonte menor (rótulos com várias letras)


def _digit(d: str, name: str) -> Key:
    return Key(d, name, "digit", insert=d)


def _operator(symbol: str, name: str) -> Key:
    return Key(symbol, name, "operator", insert=symbol)


def _function(label: str, name: str, insert: str) -> Key:
    return Key(label, name, "function", insert=insert, small=True)


def _action(label: str, name: str, insert: str) -> Key:
    """Tecla de controle (parênteses, constantes, %, ;): vidro cinza, insere o próprio texto."""
    return Key(label, name, "action", insert=insert)


CLEAR_KEY = Key("C", "Limpar tudo", "action", action=CLEAR)
BACKSPACE_KEY = Key("⌫", "Apagar último caractere", "action", action=BACKSPACE)

# Organização (igual nas duas abas): controles em cinza na linha de cima, números em
# vidro claro e os operadores em laranja sempre na última coluna, terminando no "=".

# Teclado Comum: 4 colunas, de cima para baixo.
COMMON_KEYS: tuple[tuple[Key, ...], ...] = (
    (
        CLEAR_KEY,
        BACKSPACE_KEY,
        _action("(", "Abre parêntese", "("),
        _action(")", "Fecha parêntese", ")"),
    ),
    (_digit("7", "Sete"), _digit("8", "Oito"), _digit("9", "Nove"), _operator("÷", "Dividir")),
    (_digit("4", "Quatro"), _digit("5", "Cinco"), _digit("6", "Seis"), _operator("×", "Multiplicar")),
    (_digit("1", "Um"), _digit("2", "Dois"), _digit("3", "Três"), _operator("−", "Subtrair")),
    (
        _digit("0", "Zero"),
        Key(",", "Vírgula decimal", "digit", insert=","),
        _action("%", "Porcentagem", "%"),
        _operator("+", "Somar"),
    ),
    (Key("=", "Calcular resultado", "equals", action=EVALUATE, column_span=4),),
)

# Teclado Científico: 5 colunas. Em cima, três linhas de funções (cada inversa logo
# abaixo da sua função); embaixo, o mesmo bloco da aba Comum, com uma coluna a mais
# para π, e, % e ;. A tecla DEG/RAD troca de rótulo conforme o modo.
SCIENTIFIC_KEYS: tuple[tuple[Key, ...], ...] = (
    (
        Key("DEG", "Modo de ângulo: graus", "function", action=ANGLE_MODE, small=True),
        _function("sin", "Seno", "sin("),
        _function("cos", "Cosseno", "cos("),
        _function("tan", "Tangente", "tan("),
        _function("ln", "Logaritmo natural", "ln("),
    ),
    (
        _function("ⁿ√", "Raiz de índice n: raiz(n; x)", "raiz("),
        _function("sin⁻¹", "Arco seno", "asin("),
        _function("cos⁻¹", "Arco cosseno", "acos("),
        _function("tan⁻¹", "Arco tangente", "atan("),
        _function("log", "Logaritmo na base 10", "log("),
    ),
    (
        _function("√", "Raiz quadrada", "√"),
        _function("x²", "Ao quadrado", "^2"),
        _function("xʸ", "Potência", "^"),
        _function("n!", "Fatorial", "!"),
        _function("|x|", "Valor absoluto", "abs("),
    ),
    (
        CLEAR_KEY,
        BACKSPACE_KEY,
        _action("(", "Abre parêntese", "("),
        _action(")", "Fecha parêntese", ")"),
        _operator("÷", "Dividir"),
    ),
    (
        _digit("7", "Sete"), _digit("8", "Oito"), _digit("9", "Nove"),
        _action("π", "Pi", "π"),
        _operator("×", "Multiplicar"),
    ),
    (
        _digit("4", "Quatro"), _digit("5", "Cinco"), _digit("6", "Seis"),
        _action("e", "Número de Euler", "e"),
        _operator("−", "Subtrair"),
    ),
    (
        _digit("1", "Um"), _digit("2", "Dois"), _digit("3", "Três"),
        _action("%", "Porcentagem", "%"),
        _operator("+", "Somar"),
    ),
    (
        _digit("0", "Zero"),
        Key(",", "Vírgula decimal", "digit", insert=","),
        _action(";", "Separador de argumentos (ponto e vírgula)", ";"),
        Key("=", "Calcular resultado", "equals", action=EVALUATE, column_span=2),
    ),
)


class Keypad(QWidget):
    """Grade de teclas. Emite o texto a inserir ou a ação escolhida."""

    inserted = Signal(str)
    action = Signal(str)

    def __init__(
        self,
        rows: tuple[tuple[Key, ...], ...],
        theme: ThemeManager,
        parent: QWidget | None = None,
        key_min_height: int = 44,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._buttons: dict[str, QPushButton] = {}
        self._key_min_height = key_min_height
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        for row_index, row in enumerate(rows):
            column = 0
            for key in row:
                button = self._make_button(key)
                grid.addWidget(button, row_index, column, 1, key.column_span)
                column += key.column_span

    def _make_button(self, key: Key) -> QPushButton:
        button = GlassButton(key.label, self._theme, key.role, key.small, self)
        button.setAccessibleName(key.accessible_name)
        button.setToolTip(key.accessible_name)
        button.setMinimumSize(48, self._key_min_height)
        if key.action == BACKSPACE:
            button.setAutoRepeat(True)
        if key.action is not None:
            button.clicked.connect(lambda _=False, a=key.action: self.action.emit(a))
        else:
            button.clicked.connect(lambda _=False, t=key.insert: self.inserted.emit(t))
        self._buttons[key.action or key.insert] = button
        return button

    def button(self, key: str) -> QPushButton | None:
        """Botão pelo texto que insere ou pela ação (ex.: "7", "×", "evaluate")."""
        return self._buttons.get(key)

    def set_key_text(self, key: str, label: str, accessible_name: str) -> None:
        button = self._buttons[key]
        button.setText(label)
        button.setAccessibleName(accessible_name)
        button.setToolTip(accessible_name)

    def flash(self, key: str) -> None:
        """Mostra o botão "apertado" por um instante (usado pelo teclado físico)."""
        button = self._buttons.get(key)
        if button is None:
            return
        button.setDown(True)
        # O botão é o "contexto": se a janela fechar antes, o timer é cancelado.
        QTimer.singleShot(110, button, lambda: button.setDown(False))
