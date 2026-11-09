"""Redesign liquid glass: lente das abas, botões sem vidro próprio e organização do teclado."""

from ai_calc.ui.app import create_app
from ai_calc.ui.keypad import BACKSPACE, CLEAR, COMMON_KEYS, EVALUATE, SCIENTIFIC_KEYS
from ai_calc.ui.main_window import MainWindow
from ai_calc.ui.tabs import LENS_MS
from ai_calc.ui.theme import LIGHT, ThemeManager


def _janela(qtbot, movimento):
    create_app()
    window = MainWindow(ThemeManager(LIGHT, reduce_motion=lambda: not movimento))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.tabs.setCurrentIndex(0)
    qtbot.wait(LENS_MS + 50)
    return window


def test_lente_desliza_ate_a_aba_escolhida(qtbot):
    window = _janela(qtbot, movimento=True)
    window.tabs.setCurrentIndex(2)
    assert window.tabs._lens is not None                 # no meio do caminho
    qtbot.waitUntil(lambda: window.tabs._lens is None, timeout=LENS_MS * 10)


def test_lente_vai_direto_quando_reduzir_movimento(qtbot):
    window = _janela(qtbot, movimento=False)
    window.tabs.setCurrentIndex(2)
    assert window.tabs._lens is None


def test_operadores_ficam_na_ultima_coluna():
    for rows in (COMMON_KEYS, SCIENTIFIC_KEYS):
        for row in rows:
            if any(key.role == "digit" for key in row):
                assert row[-1].role in ("operator", "equals"), [key.label for key in row]
    assert COMMON_KEYS[-1][-1].action == EVALUATE
    assert SCIENTIFIC_KEYS[-1][-1].action == EVALUATE


def test_limpar_e_apagar_ficam_juntos():
    for rows in (COMMON_KEYS, SCIENTIFIC_KEYS):
        for row in rows:
            actions = [key.action for key in row]
            if CLEAR in actions:
                assert abs(actions.index(BACKSPACE) - actions.index(CLEAR)) == 1


def test_botoes_do_topo_ficam_na_capsula(qtbot):
    window = _janela(qtbot, movimento=False)
    assert window.theme_button.parent() is window.tools
    assert window.history_button.parent() is window.tools


def test_operador_escolhido_fica_destacado(qtbot):
    window = _janela(qtbot, movimento=False)
    teclado = window.common_keypad
    window.insert("1")
    window.insert("×")
    assert teclado.button("×").selected
    assert not teclado.button("+").selected
    window.insert("2")                       # a próxima tecla tira o destaque
    assert not teclado.button("×").selected


def test_destaque_some_depois_do_igual(qtbot):
    window = _janela(qtbot, movimento=False)
    for tecla in "2+":
        window.insert(tecla)
    window.run_action(EVALUATE)
    window.insert("3")
    window.run_action(EVALUATE)
    assert not window.common_keypad.button("+").selected


def test_teclas_redondas_e_alinhadas(qtbot):
    from ai_calc.ui.keypad import COMMON_METRICS, KEY_PAD

    window = _janela(qtbot, movimento=False)
    window.resize(420, 760)
    qtbot.wait(20)
    teclado = window.common_keypad
    sete = teclado.button("7")
    lado = sete.width() - 2 * KEY_PAD
    assert lado == sete.height() - 2 * KEY_PAD               # círculo
    assert lado <= COMMON_METRICS.max_key                    # tamanho limitado
    grade = teclado.grid_rect
    assert grade.bottom() + KEY_PAD == teclado.height()      # encostado embaixo
    # O número do visor termina na mesma borda das teclas.
    direita_visor = window.display.width() - window.display.layout().contentsMargins().right()
    assert abs(direita_visor - grade.right()) <= 1


def test_teclado_cabe_na_janela_em_varios_tamanhos(qtbot):
    from ai_calc.ui.main_window import MIN_HEIGHT, MIN_WIDTH

    window = _janela(qtbot, movimento=False)
    for aba in (0, 1):
        window.tabs.setCurrentIndex(aba)
        for tamanho in ((MIN_WIDTH, MIN_HEIGHT), (700, 640), (1100, 820)):
            window.resize(*tamanho)
            for tecla in "2(3+4)":
                window.insert(tecla)
            window.run_action(EVALUATE)        # aparece "Interpretado como", que não pode empurrar o teclado
            qtbot.wait(20)
            assert window.pages.geometry().bottom() < window.calculator.height(), (aba, tamanho)
