"""Testes da edição da conta (Etapa 3A): o que cada tecla faz."""

from ai_calc.core.editor import ExpressionEditor


def digitar(editor, teclas):
    for tecla in teclas:
        editor.insert(tecla)


def test_conta_simples():
    editor = ExpressionEditor()
    digitar(editor, "2+3")
    assert editor.evaluate()
    assert editor.expression == "2+3"
    assert editor.result == "5"
    assert editor.message == ""


def test_atalhos_do_teclado_fisico_viram_simbolos():
    editor = ExpressionEditor()
    digitar(editor, "7*2-1/4.5")
    assert editor.expression == "7×2−1÷4,5"


def test_virgula_no_comeco_ganha_zero():
    editor = ExpressionEditor()
    digitar(editor, ",5+,5")
    assert editor.expression == "0,5+0,5"
    editor.evaluate()
    assert editor.result == "1"


def test_operador_depois_do_igual_continua_do_resultado():
    editor = ExpressionEditor()
    digitar(editor, "2+3")
    editor.evaluate()
    digitar(editor, "×2")
    assert editor.expression == "5×2"
    assert editor.result == ""
    editor.evaluate()
    assert editor.result == "10"


def test_numero_depois_do_igual_comeca_conta_nova():
    editor = ExpressionEditor()
    digitar(editor, "2+3")
    editor.evaluate()
    editor.insert("7")
    assert editor.expression == "7"
    assert editor.result == ""


def test_resultado_negativo_continua():
    editor = ExpressionEditor()
    digitar(editor, "2−8")
    editor.evaluate()
    digitar(editor, "×2")
    assert editor.expression == "(-6)×2"
    editor.evaluate()
    assert editor.result == "-12"


def test_resultado_negativo_ao_quadrado():
    editor = ExpressionEditor()
    digitar(editor, "2−8")
    editor.evaluate()
    editor.insert("^2")                # tecla x²
    editor.evaluate()
    assert editor.result == "36"


def test_funcao_depois_do_igual_comeca_conta_nova():
    editor = ExpressionEditor()
    digitar(editor, "2+3")
    editor.evaluate()
    editor.insert("sin(")
    assert editor.expression == "sin("


def test_trigonometria_respeita_o_modo():
    editor = ExpressionEditor()
    editor.insert("sin(")
    digitar(editor, "30)")
    editor.evaluate("DEG")
    assert editor.result == "0,5"
    editor.clear()
    editor.insert("sin(")
    editor.insert("π")
    digitar(editor, "÷2)")
    editor.evaluate("RAD")
    assert editor.result == "1"


def test_raiz_de_indice_n():
    editor = ExpressionEditor()
    editor.insert("raiz(")
    digitar(editor, "3;−8)")
    editor.evaluate()
    assert editor.result == "-2"


def test_resultado_decimal_continua():
    editor = ExpressionEditor()
    digitar(editor, "7÷2")
    editor.evaluate()
    digitar(editor, "+1")
    editor.evaluate()
    assert editor.result == "4,5"


def test_igual_repetido_nao_faz_nada():
    editor = ExpressionEditor()
    digitar(editor, "2+3")
    assert editor.evaluate()
    assert not editor.evaluate()
    assert editor.result == "5"


def test_igual_com_conta_vazia():
    editor = ExpressionEditor()
    assert not editor.evaluate()
    assert editor.message == ""


def test_erro_mostra_mensagem_e_mantem_a_conta():
    editor = ExpressionEditor()
    digitar(editor, "5÷0")
    assert not editor.evaluate()
    assert editor.is_error
    assert editor.message == "Divisão por zero inválida"
    assert editor.expression == "5÷0"
    editor.backspace()
    digitar(editor, "2")
    assert not editor.is_error
    editor.evaluate()
    assert editor.result == "2,5"


def test_expressao_incompleta():
    editor = ExpressionEditor()
    digitar(editor, "2+")
    editor.evaluate()
    assert editor.message == "Expressão incompleta"


def test_apagar_e_limpar():
    editor = ExpressionEditor()
    digitar(editor, "123")
    editor.backspace()
    assert editor.expression == "12"
    editor.clear()
    assert editor.expression == ""
    assert editor.result == ""
    editor.backspace()                 # apagar no vazio não quebra
    assert editor.expression == ""


def test_apagar_depois_do_igual_volta_a_editar():
    editor = ExpressionEditor()
    digitar(editor, "12+3")
    editor.evaluate()
    editor.backspace()
    assert editor.expression == "12+"
    assert editor.result == ""


def test_interpretado_como():
    editor = ExpressionEditor()
    digitar(editor, "2(3+4)")
    editor.evaluate()
    assert editor.result == "14"
    assert editor.message.startswith("Interpretado como: ")
    assert "×" in editor.message


def test_porcentagem():
    editor = ExpressionEditor()
    digitar(editor, "200+10%")
    editor.evaluate()
    assert editor.result == "220"


def test_limite_de_500_caracteres():
    editor = ExpressionEditor()
    digitar(editor, "1" * 600)
    assert len(editor.expression) == 500


# --- tecla "( )" (abre ou fecha, conforme a conta) ---------------------------------
def _parenteses(*teclas):
    editor = ExpressionEditor()
    for tecla in teclas:
        if tecla == "()":
            editor.parenthesis()
        else:
            editor.insert(tecla)
    return editor.expression


def test_parenteses_abre_no_comeco():
    assert _parenteses("()") == "("


def test_parenteses_fecha_depois_de_numero():
    assert _parenteses("()", "2", "+", "3", "()") == "(2+3)"


def test_parenteses_abre_depois_de_operador():
    assert _parenteses("2", "×", "()") == "2×("


def test_parenteses_sem_nada_aberto_abre():
    assert _parenteses("2", "()") == "2("


def test_parenteses_aninhados():
    assert _parenteses("()", "()", "1", "()", "()") == "((1))"


def test_parenteses_fecha_depois_de_constante_e_porcentagem():
    assert _parenteses("()", "π", "()") == "(π)"
    assert _parenteses("()", "1", "0", "%", "()") == "(10%)"


def test_parenteses_fecha_funcao_aberta():
    assert _parenteses("sin(", "3", "0", "()") == "sin(30)"


def test_parenteses_depois_do_igual_comeca_conta_nova():
    editor = ExpressionEditor()
    for tecla in "2+3":
        editor.insert(tecla)
    editor.evaluate()
    assert editor.parenthesis() == "("
    assert editor.expression == "("
