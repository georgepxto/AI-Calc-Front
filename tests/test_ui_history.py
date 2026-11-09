"""Testes da Etapa 3D na janela: histórico, gaveta, confirmação e preferências."""

import json

import pytest
from PySide6.QtCore import QPoint, Qt
from ai_calc.core.history import History
from ai_calc.core.preferences import Preferences
from ai_calc.ui.app import HISTORY_FILE, PREFERENCES_FILE, build_window, create_app
from ai_calc.ui.history_panel import GlassScrollBar
from ai_calc.ui.keypad import ANGLE_MODE, EVALUATE
from ai_calc.ui.main_window import DOCK_MIN_WIDTH, MIN_HEIGHT, MIN_WIDTH, SCIENTIFIC_TAB, MainWindow
from ai_calc.ui.theme import (
    DARK,
    DIALOG_ALPHA,
    DIM_ALPHA,
    DISPLAY_ALPHA,
    LIGHT,
    PALETTES,
    ROLE_COLORS,
    ThemeManager,
    backdrop_colors,
    composite,
    min_contrast,
    surface_colors,
)
from tests.ajudantes import distancia


def _janela(qtbot, pasta, largura=700, **tema):
    create_app()
    tema.setdefault("reduce_motion", lambda: True)
    window = build_window(pasta, **tema)
    qtbot.addWidget(window)
    window.resize(largura, 640)
    window.show()
    qtbot.waitExposed(window)
    return window


@pytest.fixture
def janela(qtbot, tmp_path):
    return _janela(qtbot, tmp_path)


def conta(qtbot, janela, texto):
    qtbot.keyClicks(janela, texto)
    qtbot.keyClick(janela, Qt.Key.Key_Return)
    qtbot.keyClick(janela, Qt.Key.Key_Escape)


def resultados(janela):
    return [item.entry.result for item in janela.history_panel.items]


# --- histórico na janela -----------------------------------------------------
def test_conta_certa_entra_no_historico(qtbot, janela, tmp_path):
    conta(qtbot, janela, "2+3")
    conta(qtbot, janela, "7*6")
    assert resultados(janela) == ["42", "5"]
    salvo = json.loads((tmp_path / HISTORY_FILE).read_text(encoding="utf-8"))
    assert [i["resultado"] for i in salvo["itens"]] == ["42", "5"]


def test_conta_com_erro_nao_entra(qtbot, janela):
    conta(qtbot, janela, "5/0")
    conta(qtbot, janela, "2+")
    assert resultados(janela) == []
    assert janela.history_panel.empty_label.isVisible()
    assert not janela.history_panel.clear_button.isEnabled()


def test_etiqueta_deg_rad_so_com_trigonometria(qtbot, janela):
    conta(qtbot, janela, "sin(30)")
    janela.set_angle_mode("RAD")
    conta(qtbot, janela, "cos(0)")
    conta(qtbot, janela, "1+1")
    modos = [item.entry.angle_mode for item in janela.history_panel.items]
    assert modos == [None, "RAD", "DEG"]
    assert janela.history_panel.items[2].accessibleName() == "sin(30) igual a 0,5, graus"


def test_clique_insere_so_o_numero(qtbot, janela):
    conta(qtbot, janela, "2+3")
    qtbot.keyClicks(janela, "10+")
    qtbot.mouseClick(janela.history_panel.items[0], Qt.MouseButton.LeftButton)
    assert janela.editor.expression == "10+5"


def test_numero_negativo_entra_entre_parenteses(qtbot, janela):
    conta(qtbot, janela, "2-8")
    qtbot.mouseClick(janela.history_panel.items[0], Qt.MouseButton.LeftButton)
    qtbot.keyClicks(janela, "^2")
    qtbot.keyClick(janela, Qt.Key.Key_Return)
    assert janela.editor.expression == "(-6)^2"
    assert janela.display.result_label.text() == "36"


def test_lista_rola_com_barra_do_tema(qtbot, janela):
    for n in range(15):
        conta(qtbot, janela, f"{n}+1")
    painel = janela.history_panel
    assert isinstance(painel.scroll.verticalScrollBar(), GlassScrollBar)
    qtbot.wait(20)
    assert painel.scroll.verticalScrollBar().maximum() > 0
    itens = painel.items
    for de_cima, de_baixo in zip(itens, itens[1:]):
        assert de_cima.geometry().bottom() < de_baixo.geometry().top()   # sem sobreposição


def test_historico_recarregado_ao_abrir(qtbot, tmp_path):
    History(tmp_path / HISTORY_FILE).add("sin(30)", "0,5", "DEG")
    window = _janela(qtbot, tmp_path)
    assert resultados(window) == ["0,5"]


def test_historico_corrompido_abre_vazio(qtbot, tmp_path):
    (tmp_path / HISTORY_FILE).write_text("{estragado", encoding="utf-8")
    window = _janela(qtbot, tmp_path)
    assert resultados(window) == []
    assert any(".corrompido-" in p.name for p in tmp_path.iterdir())
    conta(qtbot, window, "1+1")
    assert resultados(window) == ["2"]


# --- limpar com confirmação ---------------------------------------------------
def _abrir_confirmacao(qtbot, janela):
    conta(qtbot, janela, "1+1")
    conta(qtbot, janela, "2+2")
    qtbot.mouseClick(janela.history_panel.clear_button, Qt.MouseButton.LeftButton)
    dialogo = janela.confirm_dialog
    qtbot.waitUntil(dialogo.isVisible, timeout=1000)
    return dialogo


def test_limpar_pede_confirmacao_e_cancelar_mantem(qtbot, janela):
    dialogo = _abrir_confirmacao(qtbot, janela)
    assert "2 contas" in dialogo.text_label.text()
    assert dialogo.focusWidget() is dialogo.cancel_button   # a opção segura começa com o foco
    qtbot.mouseClick(dialogo.cancel_button, Qt.MouseButton.LeftButton)
    assert resultados(janela) == ["4", "2"]


def test_esc_cancela(qtbot, janela):
    dialogo = _abrir_confirmacao(qtbot, janela)
    qtbot.keyClick(dialogo, Qt.Key.Key_Escape)
    qtbot.waitUntil(lambda: not dialogo.isVisible(), timeout=1000)
    assert resultados(janela) == ["4", "2"]


def test_confirmar_apaga_e_salva(qtbot, janela, tmp_path):
    dialogo = _abrir_confirmacao(qtbot, janela)
    qtbot.mouseClick(dialogo.confirm_button, Qt.MouseButton.LeftButton)
    assert resultados(janela) == []
    assert History(tmp_path / HISTORY_FILE).entries == []


def test_confirmacao_navegavel_por_tab(qtbot, janela):
    dialogo = _abrir_confirmacao(qtbot, janela)
    assert dialogo.accessibleName() == "Limpar o histórico?"
    qtbot.keyClick(dialogo.cancel_button, Qt.Key.Key_Tab)
    assert dialogo.focusWidget() is dialogo.confirm_button
    qtbot.keyClick(dialogo.confirm_button, Qt.Key.Key_Space)
    assert resultados(janela) == []


@pytest.mark.parametrize("nome", [LIGHT, DARK])
def test_confirmacao_segue_o_tema(qtbot, janela, nome):
    janela.theme.set_theme(nome)
    dialogo = _abrir_confirmacao(qtbot, janela)
    imagem = dialogo.card.grab().toImage()
    cor = imagem.pixelColor(QPoint(12, imagem.height() // 2))
    outro = DARK if nome == LIGHT else LIGHT
    assert distancia(cor, PALETTES[nome]["display_bg"]) < distancia(cor, PALETTES[outro]["display_bg"])
    # Botões da confirmação também são de vidro com as cores do tema.
    assert dialogo.cancel_button.role == "digit"
    janela.theme.set_theme(outro)                 # mudar o tema com a janela aberta também vale
    imagem = dialogo.card.grab().toImage()
    cor = imagem.pixelColor(QPoint(12, imagem.height() // 2))
    assert distancia(cor, PALETTES[outro]["display_bg"]) < distancia(cor, PALETTES[nome]["display_bg"])
    dialogo.reject()


# --- painel fixo x gaveta -----------------------------------------------------
def test_janela_larga_mostra_painel_fixo(qtbot, janela):
    assert janela.width() >= DOCK_MIN_WIDTH
    assert janela.history_docked
    assert janela.history_panel.isVisible()
    # Como no macOS, o botão de barra lateral esconde e mostra o histórico fixo.
    assert janela.history_button.isVisible()
    assert janela.history_button.accessibleName() == "Esconder histórico"
    qtbot.mouseClick(janela.history_button, Qt.MouseButton.LeftButton)
    assert not janela.history_docked and not janela.history_panel.isVisible()
    qtbot.mouseClick(janela.history_button, Qt.MouseButton.LeftButton)
    assert janela.history_docked and janela.history_panel.isVisible()


def test_janela_estreita_usa_gaveta(qtbot, tmp_path):
    window = _janela(qtbot, tmp_path, largura=400)
    assert not window.history_docked
    assert not window.history_panel.isVisible()
    assert window.history_button.isVisible()
    assert window.history_button.accessibleName() == "Mostrar histórico"
    qtbot.mouseClick(window.history_button, Qt.MouseButton.LeftButton)
    assert window.history_drawer_open
    assert window.history_panel.isVisible()
    assert window.history_panel.close_button.isVisible()
    assert window.history_button.accessibleName() == "Esconder histórico"
    painel = window.history_panel.geometry()
    assert painel.right() <= window.centralWidget().width()
    qtbot.keyClick(window, Qt.Key.Key_Escape)
    assert not window.history_drawer_open
    assert not window.history_panel.isVisible()


def test_gaveta_fecha_ao_escolher_numero(qtbot, tmp_path):
    window = _janela(qtbot, tmp_path, largura=MIN_WIDTH)
    conta(qtbot, window, "6*7")
    window.open_history_drawer()
    assert window.focusWidget() is window.history_panel.items[0]
    qtbot.mouseClick(window.history_panel.items[0], Qt.MouseButton.LeftButton)
    assert window.editor.expression == "42"
    assert not window.history_drawer_open


def test_gaveta_desliza_quando_ha_movimento(qtbot, tmp_path):
    window = _janela(qtbot, tmp_path, largura=400, reduce_motion=lambda: False)
    window.open_history_drawer()
    assert window._drawer_animation.state() == window._drawer_animation.State.Running
    qtbot.waitUntil(lambda: window._drawer_animation.state() != window._drawer_animation.State.Running,
                    timeout=2000)
    window.close_history_drawer()
    qtbot.waitUntil(lambda: not window.history_panel.isVisible(), timeout=2000)


def test_alargar_a_janela_fixa_o_painel(qtbot, tmp_path):
    window = _janela(qtbot, tmp_path, largura=400)
    window.open_history_drawer()
    window.resize(800, 640)
    qtbot.wait(20)
    assert window.history_docked
    assert not window.history_drawer_open
    assert window.history_panel.isVisible()
    window.resize(400, 640)
    qtbot.wait(20)
    assert not window.history_panel.isVisible()


def test_topo_cabe_na_largura_minima(qtbot, tmp_path):
    window = _janela(qtbot, tmp_path, largura=MIN_WIDTH)
    window.resize(MIN_WIDTH, MIN_HEIGHT)
    qtbot.wait(20)
    assert window.tabs.sizeHint().width() <= window.tabs.width()
    assert window.theme_button.geometry().right() <= window.calculator.width()


# --- acessibilidade -----------------------------------------------------------
def test_nomes_para_leitor_de_tela(qtbot, janela):
    conta(qtbot, janela, "2+3")
    painel = janela.history_panel
    assert painel.accessibleName() == "Histórico"
    assert painel.clear_button.accessibleName() == "Limpar histórico"
    assert painel.close_button.accessibleName() == "Fechar histórico"
    assert painel.scroll.accessibleName() == "Lista de contas"
    item = painel.items[0]
    assert item.accessibleName() == "2+3 igual a 5"
    assert item.accessibleDescription() == "Insere o resultado na conta atual"


def test_tab_chega_aos_itens_e_espaco_insere(qtbot, janela):
    conta(qtbot, janela, "2+3")
    painel = janela.history_panel
    painel.clear_button.setFocus()
    qtbot.keyClick(painel.clear_button, Qt.Key.Key_Tab)
    assert janela.focusWidget() is painel.items[0]
    qtbot.keyClick(painel.items[0], Qt.Key.Key_Space)
    assert janela.editor.expression == "5"


# --- preferências -------------------------------------------------------------
def test_preferencias_salvas_ao_mudar(qtbot, janela, tmp_path):
    qtbot.mouseClick(janela.theme_button, Qt.MouseButton.LeftButton)
    janela.tabs.setCurrentIndex(SCIENTIFIC_TAB)
    qtbot.mouseClick(janela.scientific_keypad.button(ANGLE_MODE), Qt.MouseButton.LeftButton)
    salvo = Preferences(tmp_path / PREFERENCES_FILE)
    assert (salvo.theme, salvo.angle_mode, salvo.last_tab) == (
        DARK if janela.theme.name == DARK else LIGHT, "RAD", "cientifica"
    )


def test_preferencias_aplicadas_ao_abrir(qtbot, tmp_path):
    Preferences(tmp_path / PREFERENCES_FILE).update(theme="escuro", angle_mode="RAD", last_tab="cientifica")
    window = _janela(qtbot, tmp_path)
    assert window.theme.name == DARK
    assert window.angle_mode == "RAD"
    assert window.tabs.currentIndex() == SCIENTIFIC_TAB
    assert window.scientific_keypad.button(ANGLE_MODE).text() == "RAD"


def test_tema_salvo_vale_sobre_o_windows(qtbot, tmp_path):
    for salvo in (LIGHT, DARK):
        Preferences(tmp_path / PREFERENCES_FILE).update(theme=salvo)
        window = _janela(qtbot, tmp_path)
        assert window.theme.name == salvo


def test_sem_escolha_salva_segue_o_windows(qtbot, tmp_path):
    window = _janela(qtbot, tmp_path)
    assert window.preferences.theme is None
    assert window.theme.name in (LIGHT, DARK)
    assert not (tmp_path / PREFERENCES_FILE).exists() or Preferences(tmp_path / PREFERENCES_FILE).theme is None


def test_preferencias_corrompidas_abrem_no_padrao(qtbot, tmp_path):
    (tmp_path / PREFERENCES_FILE).write_text("nada a ver", encoding="utf-8")
    window = _janela(qtbot, tmp_path)
    assert window.angle_mode == "DEG"
    assert window.tabs.currentIndex() == 0
    assert any(p.name.startswith("preferencias.corrompido-") for p in tmp_path.iterdir())


# --- contraste (histórico, gaveta e confirmação) -------------------------------
@pytest.mark.parametrize("tema", [LIGHT, DARK])
@pytest.mark.parametrize("painel_alpha", [DISPLAY_ALPHA, DIALOG_ALPHA])
def test_contraste_do_historico(tema, painel_alpha):
    paleta = PALETTES[tema]
    # Fundo atrás do painel: a janela (painel fixo) ou as teclas (gaveta por cima do teclado).
    atras = backdrop_colors(paleta)
    for papel in ("digit", "operator", "function", "action", "equals"):
        fundo, _, _, opacidade, _ = ROLE_COLORS[papel]
        atras += surface_colors(paleta, paleta[fundo], opacidade, False)
    painel = surface_colors(paleta, paleta["display_bg"], painel_alpha, False, atras)
    if painel_alpha == DISPLAY_ALPHA:                         # fixo: só a janela atrás
        painel = surface_colors(paleta, paleta["display_bg"], painel_alpha, False)
    assert min_contrast(paleta, "text", painel) >= 4.5            # título
    assert min_contrast(paleta, "text_muted", painel) >= 4.5      # "Nenhuma conta ainda"
    assert min_contrast(paleta, "scroll_handle", painel) >= 3.0   # barra de rolagem
    for papel in ("history", "action", "theme"):                 # itens, Limpar e Fechar
        fundo, apertado, texto, opacidade, foco = ROLE_COLORS[papel]
        for chave in (fundo, apertado):
            item = surface_colors(paleta, paleta[chave], opacidade, True, painel)
            minimo = 3.0 if papel == "theme" else 4.5
            assert min_contrast(paleta, texto, item) >= minimo, (papel, chave)
            assert min_contrast(paleta, foco, item) >= 3.0, (papel, chave)
            if papel == "history":
                assert min_contrast(paleta, "text_muted", item) >= 4.5, chave


@pytest.mark.parametrize("tema", [LIGHT, DARK])
def test_contraste_da_confirmacao(tema):
    paleta = PALETTES[tema]
    escurecido = [composite(paleta["shadow"], DIM_ALPHA, c) for c in backdrop_colors(paleta)]
    cartao = surface_colors(paleta, paleta["display_bg"], DIALOG_ALPHA, False, escurecido)
    assert min_contrast(paleta, "text", cartao) >= 4.5
    for papel in ("digit", "action"):                            # Cancelar e Limpar
        fundo, apertado, texto, opacidade, foco = ROLE_COLORS[papel]
        for chave in (fundo, apertado):
            botao = surface_colors(paleta, paleta[chave], opacidade, True, cartao)
            assert min_contrast(paleta, texto, botao) >= 4.5, (papel, chave)
            assert min_contrast(paleta, foco, botao) >= 3.0, (papel, chave)


def test_janela_de_teste_sem_pasta_nao_grava(qtbot):
    create_app()
    window = MainWindow(ThemeManager(LIGHT, reduce_motion=lambda: True))
    qtbot.addWidget(window)
    assert window.history.path is None and window.preferences.path is None
    window.run_action(EVALUATE)
