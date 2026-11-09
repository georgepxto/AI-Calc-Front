"""Testes de interface do painel de porcentagem (Etapa 6B) com pytest-qt."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from ai_calc.ui.app import create_app
from ai_calc.ui.keypad import COMMON_KEYS, EVALUATE
from ai_calc.ui.main_window import MIN_HEIGHT, MIN_WIDTH, SCIENTIFIC_TAB, TRIG_TAB, MainWindow


@pytest.fixture
def janela(qtbot):
    create_app()
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def clicar_teclas(qtbot, janela, *teclas):
    for tecla in teclas:
        qtbot.mouseClick(janela.common_keypad.button(tecla), Qt.MouseButton.LeftButton)


def test_botao_porcentagem_visivel_apenas_na_aba_comum(qtbot, janela):
    assert janela.percentage_button.isVisible()
    assert janela.percentage_button.text() == "Porcentagem"

    # Muda para Científica
    janela.tabs.setCurrentIndex(SCIENTIFIC_TAB)
    qtbot.wait(20)
    assert not janela.percentage_button.isVisible()

    # Muda para Trigonometria
    janela.tabs.setCurrentIndex(TRIG_TAB)
    qtbot.wait(20)
    assert not janela.percentage_button.isVisible()

    # Volta para Comum
    janela.tabs.setCurrentIndex(0)
    qtbot.wait(20)
    assert janela.percentage_button.isVisible()


def test_abrir_e_fechar_painel_porcentagem(qtbot, janela):
    assert not janela.percentage_panel_open
    assert not janela.percentage_panel.isVisible()

    # Clica no botão Porcentagem para abrir
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    assert janela.percentage_panel_open
    assert janela.percentage_panel.isVisible()

    # Clica no botão fechar ✕
    qtbot.mouseClick(janela.percentage_panel.close_button, Qt.MouseButton.LeftButton)
    assert not janela.percentage_panel_open
    assert not janela.percentage_panel.isVisible()

    # Abre novamente e fecha com Esc
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    assert janela.percentage_panel.isVisible()
    qtbot.keyClick(janela.percentage_panel, Qt.Key.Key_Escape)
    assert not janela.percentage_panel.isVisible()


def test_parte_do_total_e_usar_resultado(qtbot, janela):
    # Digita 200 ×
    clicar_teclas(qtbot, janela, "2", "0", "0", "×")
    assert janela.display.expression_label.text() == ""
    assert janela.display.result_label.text() == "200×"

    # Abre o painel de porcentagem
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel
    assert panel.isVisible()

    # Operação 0: Parte do total
    panel.set_operation(0)
    panel.part_field.set_value("36")
    panel.total_field.set_value("240")

    # Verifica exibição
    assert panel.result_text() == "15%"
    assert panel.use_result_button.isEnabled()

    # Clica em Usar resultado
    qtbot.mouseClick(panel.use_result_button, Qt.MouseButton.LeftButton)

    # Painel fecha e visor completa a expressão com 0,15
    assert not panel.isVisible()
    assert janela.editor.expression == "200×0,15"

    # Ao calcular, o visor mostra 30
    clicar_teclas(qtbot, janela, EVALUATE)
    assert janela.display.result_label.text() == "30"


def test_variacao_percentual_e_regra_negativo(qtbot, janela):
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel

    # Operação 1: Variação (%)
    panel.set_operation(1)
    panel.initial_field.set_value("240")
    panel.final_field.set_value("204")

    # De 240 para 204 exibe −15%
    assert panel.result_text() in ("−15%", "-15%")
    assert panel.use_result_button.isEnabled()

    # Clica em Usar resultado
    qtbot.mouseClick(panel.use_result_button, Qt.MouseButton.LeftButton)
    assert not panel.isVisible()

    # Editor aplica regra de valores negativos entre parênteses
    assert janela.editor.expression == "(-0,15)"


def test_valor_original_com_desconto(qtbot, janela):
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel

    # Operação 2: Valor original
    panel.set_operation(2)
    panel.discount_final_field.set_value("150")
    panel.discount_rate_field.set_value("25")

    # 150 e 25 exibem 200
    assert panel.result_text() == "200"
    assert panel.use_result_button.isEnabled()

    # Clica em Usar resultado
    qtbot.mouseClick(panel.use_result_button, Qt.MouseButton.LeftButton)
    assert not panel.isVisible()
    assert janela.editor.expression == "200"


def test_virgula_e_ponto_decimal_produzem_mesmo_resultado(qtbot, janela):
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel

    panel.set_operation(0)
    # Com vírgula
    panel.part_field.set_value("36,0")
    panel.total_field.set_value("240,0")
    res_virgula = panel.result_text()

    # Com ponto
    panel.part_field.set_value("36.0")
    panel.total_field.set_value("240.0")
    res_ponto = panel.result_text()

    assert res_virgula == res_ponto == "15%"


def test_erros_e_bloqueio_de_insercao(qtbot, janela):
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel

    # 1. Base zero em Parte do total
    panel.set_operation(0)
    panel.part_field.set_value("50")
    panel.total_field.set_value("0")
    assert panel.message_text() == "Divisão por zero inválida"
    assert not panel.use_result_button.isEnabled()

    # 2. Desconto de 100% no cálculo inverso
    panel.set_operation(2)
    panel.discount_final_field.set_value("150")
    panel.discount_rate_field.set_value("100")
    assert panel.message_text() == "Valor fora do domínio"
    assert not panel.use_result_button.isEnabled()

    # 3. Campo inválido
    panel.discount_rate_field.set_value("abc")
    assert panel.message_text() == "Campo inválido"
    assert not panel.use_result_button.isEnabled()


def test_invalidacao_ao_alterar_campo_ou_operacao(qtbot, janela):
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel

    panel.set_operation(0)
    panel.part_field.set_value("36")
    panel.total_field.set_value("240")
    assert panel.use_result_button.isEnabled()

    # Altera um campo: deve invalidar
    panel.part_field.set_value("")
    assert not panel.use_result_button.isEnabled()
    assert panel.result_text() == ""

    # Preenche de novo e troca de operação
    panel.part_field.set_value("36")
    assert panel.use_result_button.isEnabled()
    panel.set_operation(1)
    # Ao trocar de operação, resultado anterior deve estar desabilitado
    assert not panel.use_result_button.isEnabled()
    assert panel.result_text() == ""


def test_painel_cabe_na_largura_minima_e_funciona_em_ambos_temas(qtbot, janela):
    janela.resize(MIN_WIDTH, MIN_HEIGHT)
    qtbot.wait(20)
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel
    assert panel.isVisible()
    assert panel.width() <= MIN_WIDTH

    # Testa tema escuro
    janela.theme.set_theme("escuro")
    qtbot.wait(20)
    panel.set_operation(0)
    panel.part_field.set_value("50")
    panel.total_field.set_value("100")
    assert panel.result_text() == "50%"

    # Testa tema claro
    janela.theme.set_theme("claro")
    qtbot.wait(20)
    assert panel.result_text() == "50%"


def test_navegacao_com_tab(qtbot, janela):
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel
    panel.set_operation(0)
    panel.part_field.set_value("36")
    panel.total_field.set_value("240")

    # Foco no primeiro campo
    panel.part_field.edit.setFocus()
    assert panel.part_field.edit.hasFocus()

    # Tab vai para o segundo campo
    qtbot.keyClick(panel.part_field.edit, Qt.Key.Key_Tab)
    assert panel.total_field.edit.hasFocus()

    # Tab vai para Usar resultado
    qtbot.keyClick(panel.total_field.edit, Qt.Key.Key_Tab)
    assert panel.use_result_button.hasFocus()


# --- Critérios específicos de regressão (Etapa 6B) ---------------------------
def test_tab_e_shift_tab_nao_focam_teclas_encobertas(qtbot, janela):
    """Critério 1: Com o painel Porcentagem aberto, Tab e Shift+Tab não focam teclas encobertas."""
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel
    assert panel.isVisible()

    teclas_encobertas = set(janela.common_keypad.findChildren(QPushButton))
    panel.part_field.edit.setFocus()

    # Percorre para a frente com Tab
    for _ in range(35):
        qtbot.keyClick(janela.focusWidget(), Qt.Key.Key_Tab)
        assert janela.focusWidget() not in teclas_encobertas

    # Percorre para trás com Shift+Tab
    for _ in range(35):
        qtbot.keyClick(janela.focusWidget(), Qt.Key.Key_Tab, Qt.KeyboardModifier.ShiftModifier)
        assert janela.focusWidget() not in teclas_encobertas


def test_escape_com_campo_em_foco_fecha_painel_e_devolve_foco(qtbot, janela):
    """Critério 2: Esc com um campo em foco fecha o painel e devolve o foco ao botão Porcentagem."""
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel
    assert panel.isVisible()

    # Coloca foco no campo de texto
    panel.part_field.edit.setFocus()
    assert janela.focusWidget() is panel.part_field.edit

    # Pressiona Esc
    qtbot.keyClick(panel.part_field.edit, Qt.Key.Key_Escape)
    qtbot.wait(20)

    # Painel fecha e foco retorna ao botão Porcentagem
    assert not janela.percentage_panel_open
    assert not panel.isVisible()
    assert janela.focusWidget() is janela.percentage_button


def test_largura_minima_gaveta_historico_mantem_painel_alinhado_e_usar_resultado(qtbot, janela):
    """Critério 3: Na largura mínima, abrir e fechar a gaveta do histórico mantém o painel alinhado e o botão acessível."""
    janela.resize(MIN_WIDTH, MIN_HEIGHT)
    qtbot.wait(20)

    # Abre o painel Porcentagem e calcula 36 de 240
    qtbot.mouseClick(janela.percentage_button, Qt.MouseButton.LeftButton)
    panel = janela.percentage_panel
    panel.set_operation(0)
    panel.part_field.set_value("36")
    panel.total_field.set_value("240")
    assert panel.result_text() == "15%"
    assert panel.use_result_button.isEnabled()

    # Abre a gaveta do histórico
    janela.open_history_drawer()
    qtbot.wait(20)

    # Fecha a gaveta do histórico
    janela.close_history_drawer()
    qtbot.wait(250)  # aguarda a animação da gaveta

    # Painel continua visível e alinhado exatamente à sua área (visor + teclado)
    assert panel.isVisible()
    assert panel.geometry() == janela.percentage_area()

    # Botão "Usar resultado" continua acessível dentro do painel
    btn = panel.use_result_button
    assert btn.isVisible()
    assert btn.isEnabled()
    assert btn.geometry().bottom() <= panel.height()

    # Clica em Usar resultado e valida a inserção
    qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)
    assert not panel.isVisible()
    assert janela.editor.expression == "0,15"
