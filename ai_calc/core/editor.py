"""Edição da conta digitada (o que acontece a cada tecla), sem interface.

A janela só repassa as teclas para cá e mostra o estado resultante.
"""

from __future__ import annotations

from .calculator import CalcResult, calculate
from .errors import CalcError
from .limits import MAX_EXPRESSION_LENGTH

# Depois do "=", estas teclas continuam a conta a partir do resultado;
# qualquer outra começa uma conta nova.
CONTINUE_KEYS = ("+", "−", "×", "÷", "^", "%", "!")

# Atalhos do teclado físico trocados pelo símbolo mostrado no visor.
KEY_ALIASES = {"*": "×", "/": "÷", "-": "−", ".": ","}

_STARTS_NUMBER_BEFORE = "+−×÷^(;"

# Depois destes caracteres, um número vindo do histórico entra com "×" na frente.
_ENDS_OPERAND = ",)!%"

# Depois destes caracteres a tecla "( )" fecha um parêntese aberto (fim de um número,
# de uma constante ou de outro parêntese); depois de qualquer outro, ela abre um novo.
_CLOSES_AFTER = ")!%πe"


def as_operand(number: str) -> str:
    """Número pronto para continuar uma conta: negativo vai entre parênteses."""
    return f"({number})" if number.startswith("-") else number


class ExpressionEditor:
    """Conta em edição, último resultado e mensagem (erro ou "Interpretado como")."""

    def __init__(self) -> None:
        self.expression = ""
        self.result = ""
        self.message = ""
        self.is_error = False
        self.last_outcome: CalcResult | None = None
        self._just_evaluated = False

    def insert(self, key: str) -> None:
        key = KEY_ALIASES.get(key, key)
        if self._just_evaluated:
            if key[:1] in CONTINUE_KEYS:
                # Resultado negativo vai entre parênteses: (-6)^2 = 36, não -36.
                self.expression = as_operand(self.result)
            else:
                self.expression = ""
            self.result = ""
        self._just_evaluated = False
        self._clear_message()
        if key == "," and (not self.expression or self.expression[-1] in _STARTS_NUMBER_BEFORE):
            key = "0,"
        if len(self.expression) + len(key) <= MAX_EXPRESSION_LENGTH:
            self.expression += key

    def parenthesis(self) -> str:
        """Tecla "( )": fecha um parêntese aberto se a conta pede, senão abre um.

        Devolve o caractere inserido ("(" ou ")").
        """
        expression = "" if self._just_evaluated else self.expression
        last = expression[-1:]
        still_open = expression.count("(") > expression.count(")")
        closes = still_open and bool(last) and (last.isdigit() or last in _CLOSES_AFTER)
        key = ")" if closes else "("
        self.insert(key)
        return key

    def insert_value(self, number: str) -> None:
        """Insere um número pronto (ex.: resultado do histórico) na conta atual."""
        if self._just_evaluated:
            self.expression = ""
            self.result = ""
            self._just_evaluated = False
        self._clear_message()
        text = as_operand(number)
        last = self.expression[-1:]
        if last and (last.isalnum() or last in _ENDS_OPERAND):
            text = "×" + text
        if len(self.expression) + len(text) <= MAX_EXPRESSION_LENGTH:
            self.expression += text

    def backspace(self) -> None:
        if self._just_evaluated:
            self.result = ""
            self._just_evaluated = False
        self._clear_message()
        self.expression = self.expression[:-1]

    def clear(self) -> None:
        self.expression = ""
        self.result = ""
        self._just_evaluated = False
        self._clear_message()

    def evaluate(self, angle_mode: str = "DEG") -> bool:
        """Calcula a conta atual. Devolve True se deu certo."""
        if not self.expression.strip() or self._just_evaluated:
            return False
        try:
            outcome = calculate(self.expression, angle_mode)
        except CalcError as error:
            self.result = ""
            self.message = error.message
            self.is_error = True
            return False
        self.last_outcome = outcome
        self.result = outcome.text
        self.message = f"Interpretado como: {outcome.interpreted}" if outcome.interpreted else ""
        self.is_error = False
        self._just_evaluated = True
        return True

    def _clear_message(self) -> None:
        self.message = ""
        self.is_error = False
