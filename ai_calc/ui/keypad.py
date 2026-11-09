"""Teclado na tela: monta a grade de botões a partir de uma lista de teclas."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, QSize, QTimer, Signal
from PySide6.QtWidgets import QPushButton, QWidget

from .glass_button import GlassButton
from .theme import ThemeManager

# Ações especiais (as demais teclas só inserem o próprio texto).
CLEAR = "clear"
BACKSPACE = "backspace"
EVALUATE = "evaluate"
ANGLE_MODE = "angle_mode"
PARENTHESES = "parentheses"     # tecla "( )": abre ou fecha, conforme a conta


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


CLEAR_KEY = Key("AC", "Limpar tudo", "action", action=CLEAR)
BACKSPACE_KEY = Key("⌫", "Apagar último caractere", "action", action=BACKSPACE)

# Layout da calculadora da Apple (iOS 26): "⌫ AC % ÷" em cima, números no meio,
# operadores em laranja na última coluna terminando no "=".

# Teclado Comum: 4 colunas, de cima para baixo.
COMMON_KEYS: tuple[tuple[Key, ...], ...] = (
    (BACKSPACE_KEY, CLEAR_KEY, _action("%", "Porcentagem", "%"), _operator("÷", "Dividir")),
    (_digit("7", "Sete"), _digit("8", "Oito"), _digit("9", "Nove"), _operator("×", "Multiplicar")),
    (_digit("4", "Quatro"), _digit("5", "Cinco"), _digit("6", "Seis"), _operator("−", "Subtrair")),
    (_digit("1", "Um"), _digit("2", "Dois"), _digit("3", "Três"), _operator("+", "Somar")),
    (
        Key("( )", "Parênteses: abre ou fecha", "action", action=PARENTHESES),
        _digit("0", "Zero"),
        Key(",", "Vírgula decimal", "digit", insert=","),
        Key("=", "Calcular resultado", "equals", action=EVALUATE),
    ),
)

# Teclado Científico: 5 colunas. Em cima, três linhas de funções (cada inversa logo
# abaixo da sua função). Embaixo, o mesmo teclado da aba Comum com uma coluna de
# funções à esquerda, como a calculadora da Apple deitada. DEG/RAD troca de rótulo.
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
        _function("(", "Abre parêntese", "("),
        BACKSPACE_KEY, CLEAR_KEY, _action("%", "Porcentagem", "%"), _operator("÷", "Dividir"),
    ),
    (
        _function(")", "Fecha parêntese", ")"),
        _digit("7", "Sete"), _digit("8", "Oito"), _digit("9", "Nove"), _operator("×", "Multiplicar"),
    ),
    (
        _function(";", "Separador de argumentos (ponto e vírgula)", ";"),
        _digit("4", "Quatro"), _digit("5", "Cinco"), _digit("6", "Seis"), _operator("−", "Subtrair"),
    ),
    (
        _function("e", "Número de Euler", "e"),
        _digit("1", "Um"), _digit("2", "Dois"), _digit("3", "Três"), _operator("+", "Somar"),
    ),
    (
        _function("π", "Pi", "π"),
        Key("0", "Zero", "digit", insert="0", column_span=2),
        Key(",", "Vírgula decimal", "digit", insert=","),
        Key("=", "Calcular resultado", "equals", action=EVALUATE),
    ),
)


@dataclass(frozen=True)
class KeypadMetrics:
    """Medidas do teclado (como na calculadora da Apple: teclas de tamanho limitado,
    espaço fixo entre elas e o bloco todo encostado embaixo, centralizado)."""

    max_key: int        # altura máxima de uma tecla (diâmetro do círculo)
    gap: int            # espaço entre as teclas
    aspect: float       # largura / altura de uma tecla (1 = círculo)
    min_key: int        # altura mínima (abaixo disso o teclado não encolhe)


COMMON_METRICS = KeypadMetrics(max_key=64, gap=12, aspect=1.0, min_key=44)
SCIENTIFIC_METRICS = KeypadMetrics(max_key=48, gap=8, aspect=1.45, min_key=30)

# Folga em volta de cada tecla: espaço para a sombra e para a tecla "estufar" ao apertar.
KEY_PAD = 4


class Keypad(QWidget):
    """Teclas em grade. Emite o texto a inserir ou a ação escolhida."""

    inserted = Signal(str)
    action = Signal(str)
    laid_out = Signal()         # as teclas mudaram de lugar (o visor se alinha a elas)

    def __init__(
        self,
        rows: tuple[tuple[Key, ...], ...],
        theme: ThemeManager,
        parent: QWidget | None = None,
        metrics: KeypadMetrics = COMMON_METRICS,
    ) -> None:
        super().__init__(parent)
        self._theme = theme
        self._buttons: dict[str, QPushButton] = {}
        self._metrics = metrics
        self._rows = len(rows)
        self._columns = max(sum(key.column_span for key in row) for row in rows)
        self._cells: list[tuple[QPushButton, int, int, int]] = []    # botão, linha, coluna, largura
        self._grid = QRectF()
        for row_index, row in enumerate(rows):
            column = 0
            for key in row:
                button = self._make_button(key)
                self._cells.append((button, row_index, column, key.column_span))
                column += key.column_span
        self.setMinimumSize(self.minimumSizeHint())

    # --- medidas ---
    def _key_size(self, width: float, height: float) -> tuple[int, int]:
        """Altura e largura de uma tecla para caber em width × height."""
        m = self._metrics
        cols, rows = self._columns, self._rows
        room_w = width - 2 * KEY_PAD - (cols - 1) * m.gap
        room_h = height - 2 * KEY_PAD - (rows - 1) * m.gap
        key_h = int(min(m.max_key, room_h / rows, room_w / (cols * m.aspect)))
        key_h = max(m.min_key, key_h)
        key_w = int(min(key_h * m.aspect, room_w / cols))
        return key_h, key_w

    def max_grid_width(self) -> int:
        """Largura das teclas no tamanho máximo (sem a folga)."""
        m = self._metrics
        key_w = int(m.max_key * m.aspect)
        return self._columns * key_w + (self._columns - 1) * m.gap

    def grid_height(self, width: float, height: float) -> int:
        """Altura que as teclas ocupam (com a folga) numa área width × height."""
        key_h, _ = self._key_size(width, height)
        return self._rows * key_h + (self._rows - 1) * self._metrics.gap + 2 * KEY_PAD

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (nome do Qt)
        m = self._metrics
        key_w = 48
        width = self._columns * key_w + (self._columns - 1) * m.gap + 2 * KEY_PAD
        height = self._rows * m.min_key + (self._rows - 1) * m.gap + 2 * KEY_PAD
        return QSize(width, height)

    @property
    def grid_rect(self) -> QRectF:
        """Retângulo das teclas (sem a folga), em coordenadas do teclado."""
        return QRectF(self._grid)

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        self._place_keys()

    def _place_keys(self) -> None:
        m = self._metrics
        key_h, key_w = self._key_size(self.width(), self.height())
        grid_w = self._columns * key_w + (self._columns - 1) * m.gap
        grid_h = self._rows * key_h + (self._rows - 1) * m.gap
        left = round((self.width() - grid_w) / 2)
        top = self.height() - KEY_PAD - grid_h          # encostado embaixo
        self._grid = QRectF(left, top, grid_w, grid_h)
        for button, row, column, span in self._cells:
            x = left + column * (key_w + m.gap)
            y = top + row * (key_h + m.gap)
            w = span * key_w + (span - 1) * m.gap
            button.setGeometry(x - KEY_PAD, y - KEY_PAD, w + 2 * KEY_PAD, key_h + 2 * KEY_PAD)
        self.laid_out.emit()

    def _make_button(self, key: Key) -> QPushButton:
        button = GlassButton(key.label, self._theme, key.role, key.small, self)
        button.setAccessibleName(key.accessible_name)
        button.setToolTip(key.accessible_name)
        button.pad = KEY_PAD
        button.auto_font = True
        if key.action == BACKSPACE:
            button.setAutoRepeat(True)
        if key.action is not None:
            button.clicked.connect(lambda _=False, a=key.action: self.action.emit(a))
        else:
            button.clicked.connect(lambda _=False, t=key.insert: self.inserted.emit(t))
        self._buttons[key.action or key.insert] = button
        if key.action == PARENTHESES:
            # Teclado físico: "(" e ")" também piscam a tecla "( )".
            self._buttons.setdefault("(", button)
            self._buttons.setdefault(")", button)
        return button

    def button(self, key: str) -> QPushButton | None:
        """Botão pelo texto que insere ou pela ação (ex.: "7", "×", "evaluate")."""
        return self._buttons.get(key)

    def set_key_text(self, key: str, label: str, accessible_name: str) -> None:
        button = self._buttons[key]
        button.setText(label)
        button.fit_font()
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

    def set_selected(self, key: str | None) -> None:
        """Destaca o operador escolhido (como na Apple) até a próxima tecla."""
        for name, button in self._buttons.items():
            if isinstance(button, GlassButton) and button.role == "operator":
                button.set_selected(name == key)
