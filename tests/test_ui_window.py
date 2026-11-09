"""Testes da janela (Etapa 3A) com pytest-qt, em modo offscreen."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from ai_calc.ui.app import create_app
from ai_calc.ui.keypad import BACKSPACE, CLEAR, COMMON_KEYS, EVALUATE
from ai_calc.ui.main_window import MIN_HEIGHT, MIN_WIDTH, SCIENTIFIC_TAB, TRIG_TAB, MainWindow


@pytest.fixture
def janela(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def clicar(qtbot, janela, *teclas):
    for tecla in teclas:
        qtbot.mouseClick(janela.common_keypad.button(tecla), Qt.MouseButton.LeftButton)


def resultado(janela):
    return janela.display.result_label.text()


# --- botões na tela ----------------------------------------------------------
def test_soma_pelos_botoes(qtbot, janela):
    clicar(qtbot, janela, "2", "+", "3", EVALUATE)
    assert resultado(janela) == "5"
    assert janela.display.expression_label.text() == "2+3"


def test_enquanto_digita_a_conta_aparece_na_linha_grande(qtbot, janela):
    clicar(qtbot, janela, "1", "2", "×")
    assert resultado(janela) == "12×"
    assert janela.display.expression_label.text() == ""


def test_visor_comeca_em_zero(janela):
    assert resultado(janela) == "0"


def test_apagar_e_limpar_pelos_botoes(qtbot, janela):
    clicar(qtbot, janela, "4", "5", BACKSPACE)
    assert resultado(janela) == "4"
    clicar(qtbot, janela, CLEAR)
    assert resultado(janela) == "0"


def test_erro_aparece_e_app_continua(qtbot, janela):
    clicar(qtbot, janela, "5", "÷", "0", EVALUATE)
    assert janela.display.message_label.text() == "Divisão por zero inválida"
    assert janela.isVisible()
    clicar(qtbot, janela, CLEAR, "1", "+", "1", EVALUATE)
    assert resultado(janela) == "2"
    assert janela.display.message_label.text() == ""


def test_porcentagem_e_virgula(qtbot, janela):
    clicar(qtbot, janela, "2", "0", "0", "+", "1", "0", "%", EVALUATE)
    assert resultado(janela) == "220"
    clicar(qtbot, janela, CLEAR, ",", "5", "×", "3", EVALUATE)
    assert resultado(janela) == "1,5"


def test_interpretado_como(qtbot, janela):
    clicar(qtbot, janela, "2", "(", "3", ")", EVALUATE)
    assert resultado(janela) == "6"
    assert janela.display.message_label.text().startswith("Interpretado como:")


# --- teclado físico ----------------------------------------------------------
def test_teclado_fisico(qtbot, janela):
    qtbot.keyClicks(janela, "12*3-6/2")
    assert janela.editor.expression == "12×3−6÷2"
    qtbot.keyClick(janela, Qt.Key.Key_Return)
    assert resultado(janela) == "33"


def test_teclado_fisico_enter_do_numerico_e_ponto(qtbot, janela):
    qtbot.keyClicks(janela, "1.5+1")
    qtbot.keyClick(janela, Qt.Key.Key_Enter, Qt.KeyboardModifier.KeypadModifier)
    assert resultado(janela) == "2,5"


def test_teclado_fisico_backspace_e_esc(qtbot, janela):
    qtbot.keyClicks(janela, "789")
    qtbot.keyClick(janela, Qt.Key.Key_Backspace)
    assert janela.editor.expression == "78"
    qtbot.keyClick(janela, Qt.Key.Key_Escape)
    assert janela.editor.expression == ""


def test_teclado_fisico_aceita_funcoes(qtbot, janela):
    qtbot.keyClicks(janela, "SIN(30)")
    qtbot.keyClick(janela, Qt.Key.Key_Return)
    assert resultado(janela) == "0,5"


def test_teclado_fisico_ignora_outros_simbolos(qtbot, janela):
    qtbot.keyClicks(janela, "2#+@3&")
    assert janela.editor.expression == "2+3"


def test_teclado_fisico_com_foco_num_botao(qtbot, janela):
    botao = janela.common_keypad.button("7")
    botao.setFocus()
    qtbot.keyClicks(botao, "8+1")
    qtbot.keyClick(botao, Qt.Key.Key_Return)
    assert resultado(janela) == "9"


# --- acessibilidade e foco ---------------------------------------------------
def test_toda_tecla_tem_nome_acessivel(janela):
    botoes = janela.common_keypad.findChildren(QPushButton)
    assert len(botoes) == sum(len(linha) for linha in COMMON_KEYS)
    for botao in botoes:
        assert botao.accessibleName(), botao.text()


def test_teclas_recebem_foco_com_tab(janela):
    for botao in janela.common_keypad.findChildren(QPushButton):
        assert botao.focusPolicy() & Qt.FocusPolicy.TabFocus, botao.text()


def test_tab_percorre_as_teclas(qtbot, janela):
    janela.common_keypad.button(CLEAR).setFocus()
    qtbot.keyClick(janela.focusWidget(), Qt.Key.Key_Tab)
    assert janela.focusWidget() is janela.common_keypad.button("%")


def test_espaco_aperta_a_tecla_em_foco(qtbot, janela):
    botao = janela.common_keypad.button("7")
    botao.setFocus()
    qtbot.keyClick(botao, Qt.Key.Key_Space)
    assert janela.editor.expression == "7"


# --- janela e abas -----------------------------------------------------------
def test_tamanho_minimo(janela):
    assert janela.minimumWidth() == MIN_WIDTH
    assert janela.minimumHeight() == MIN_HEIGHT


def test_teclado_cabe_na_largura_minima(qtbot, janela):
    janela.resize(MIN_WIDTH, MIN_HEIGHT)
    qtbot.wait(20)
    for botao in janela.common_keypad.findChildren(QPushButton):
        assert botao.width() >= 48, botao.text()
        assert botao.geometry().right() <= janela.common_keypad.width()


def test_todas_as_abas_ativas(janela):
    assert janela.tabs.currentIndex() == 0
    assert janela.tabs.isTabEnabled(SCIENTIFIC_TAB)
    assert janela.tabs.isTabEnabled(TRIG_TAB)


def test_abas_cabem_na_largura_minima(qtbot, janela):
    janela.resize(MIN_WIDTH, MIN_HEIGHT)
    qtbot.wait(20)
    assert janela.tabs.sizeHint().width() <= janela.tabs.width()
