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
                assert actions.index(BACKSPACE) == actions.index(CLEAR) + 1


def test_botoes_do_topo_ficam_na_capsula(qtbot):
    window = _janela(qtbot, movimento=False)
    assert window.theme_button.parent() is window.tools
    assert window.history_button.parent() is window.tools
