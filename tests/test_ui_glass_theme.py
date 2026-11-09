"""Testes da Etapa 3C: paleta, contraste do vidro, transição de tema e animação de clique."""

from pathlib import Path

import pytest
from PySide6.QtCore import QEasingCurve, QPoint, Qt
from PySide6.QtWidgets import QApplication, QWidget

import ai_calc.ui as ui_package
from ai_calc.ui.app import create_app
from ai_calc.ui.keypad import EVALUATE
from ai_calc.ui.main_window import SCIENTIFIC_TAB, MainWindow
from ai_calc.ui.theme import (
    DARK,
    DISPLAY_ALPHA,
    LIGHT,
    PALETTES,
    ROLE_COLORS,
    THEME_TRANSITION_MS,
    ThemeManager,
    backdrop_colors,
    min_contrast,
    surface_colors,
)
from tests.ajudantes import distancia

TEXT_MIN = 4.5
UI_MIN = 3.0     # contorno de foco e ícones
LARGE_TEXT_MIN = 3.0     # texto grande (operadores e "="), como pede a WCAG


# --- paletas -----------------------------------------------------------------
def test_paletas_tem_as_mesmas_cores():
    assert set(PALETTES[LIGHT]) == set(PALETTES[DARK])


def test_paletas_usam_cores_validas():
    for nome, paleta in PALETTES.items():
        for chave, cor in paleta.items():
            assert len(cor) == 7 and cor.startswith("#"), (nome, chave)
            int(cor[1:], 16)


def test_toda_cor_da_paleta_e_usada():
    # Uma cor que nenhum código usa indica um elemento que ficou sem tema.
    pasta = Path(ui_package.__file__).parent
    codigo = ""
    for arquivo in pasta.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        if arquivo.name == "theme.py":
            texto = texto.split("# Cores de cada tipo de superfície", 1)[1]
        codigo += texto
    for chave in PALETTES[LIGHT]:
        assert f'"{chave}"' in codigo, chave


# --- contraste (sobre o vidro, considerando o fundo que aparece através dele) -
@pytest.mark.parametrize("tema", [LIGHT, DARK])
@pytest.mark.parametrize("papel", sorted(ROLE_COLORS))
def test_contraste_das_teclas_e_abas(tema, papel):
    paleta = PALETTES[tema]
    fundo, apertado, texto, opacidade, foco = ROLE_COLORS[papel]
    preenchimentos = {fundo, apertado} | ({"equals_hover"} if papel == "equals" else set())
    minimo_texto = UI_MIN if papel == "theme" else TEXT_MIN     # no botão de tema o "texto" é o ícone
    if papel in ("operator", "equals"):
        # Símbolos grandes (a partir de 18 px de altura): a WCAG pede 3:1 para texto grande.
        minimo_texto = LARGE_TEXT_MIN
    for chave in preenchimentos:
        superficies = surface_colors(paleta, paleta[chave], opacidade, papel != "equals")
        assert min_contrast(paleta, texto, superficies) >= minimo_texto, chave
        assert min_contrast(paleta, foco, superficies) >= UI_MIN, chave


@pytest.mark.parametrize("tema", [LIGHT, DARK])
@pytest.mark.parametrize("texto", ["text", "text_muted", "error"])
def test_contraste_do_visor(tema, texto):
    paleta = PALETTES[tema]
    superficies = surface_colors(paleta, paleta["display_bg"], DISPLAY_ALPHA, False)
    assert min_contrast(paleta, texto, superficies) >= TEXT_MIN


@pytest.mark.parametrize("tema", [LIGHT, DARK])
@pytest.mark.parametrize("cor", ["focus", "icon"])
def test_contraste_sobre_o_fundo(tema, cor):
    paleta = PALETTES[tema]
    assert min_contrast(paleta, cor, backdrop_colors(paleta)) >= UI_MIN


@pytest.mark.parametrize("tema", [LIGHT, DARK])
def test_contraste_das_dicas(tema):
    paleta = PALETTES[tema]
    assert min_contrast(paleta, "tooltip_text", [paleta["tooltip_bg"]]) >= TEXT_MIN


# --- transição de tema -------------------------------------------------------
@pytest.fixture
def tema(qtbot):
    create_app()
    return ThemeManager(LIGHT, reduce_motion=lambda: False)


def cores_iguais(tema_manager, nome):
    return all(tema_manager.hex(chave) == cor for chave, cor in PALETTES[nome].items())


def test_duracao_e_curva(tema):
    assert THEME_TRANSITION_MS == 450
    assert tema._animation.duration() == THEME_TRANSITION_MS
    assert tema._animation.easingCurve().type() == QEasingCurve.Type.InOutCubic


def test_transicao_chega_ao_escuro_passando_por_quadros(qtbot, tema):
    quadros = []
    tema.changed.connect(lambda: quadros.append(tema.progress))
    tema.toggle()
    assert tema.name == DARK
    assert tema.is_animating
    qtbot.waitUntil(lambda: not tema.is_animating, timeout=3000)
    assert tema.progress == 1.0
    assert cores_iguais(tema, DARK)
    intermediarios = [p for p in quadros if 0 < p < 1]
    assert len(intermediarios) >= 3
    assert quadros == sorted(quadros)          # só avança


def test_clicar_de_novo_reverte_do_ponto_atual(qtbot, tema):
    tema.toggle()
    qtbot.waitUntil(lambda: 0.2 < tema.progress < 0.8, timeout=2000)
    meio = tema.progress
    quadros = []
    tema.changed.connect(lambda: quadros.append(tema.progress))
    tema.toggle()
    assert tema.name == LIGHT
    assert tema.is_animating
    qtbot.waitUntil(lambda: not tema.is_animating, timeout=3000)
    assert tema.progress == 0.0
    assert cores_iguais(tema, LIGHT)
    assert quadros[0] <= meio + 0.15           # volta de onde estava, sem salto
    assert quadros == sorted(quadros, reverse=True)


def test_muitos_cliques_seguidos_nao_travam(qtbot, tema):
    for _ in range(9):
        tema.toggle()
        qtbot.wait(15)
    assert tema.name == DARK
    qtbot.waitUntil(lambda: not tema.is_animating, timeout=3000)
    assert tema.progress == 1.0
    assert cores_iguais(tema, DARK)


def test_reduzir_movimento_troca_na_hora(qtbot):
    create_app()
    tema = ThemeManager(LIGHT, reduce_motion=lambda: True)
    tema.toggle()
    assert not tema.is_animating
    assert tema.progress == 1.0
    assert cores_iguais(tema, DARK)


def test_paleta_do_app_atualizada_no_fim(qtbot, tema):
    tema.toggle()
    qtbot.waitUntil(lambda: not tema.is_animating, timeout=3000)
    app = QApplication.instance()
    assert app.palette().toolTipBase().color().name().upper() == PALETTES[DARK]["tooltip_bg"]


# --- janela inteira durante a transição ---------------------------------------
@pytest.fixture
def janela(qtbot):
    create_app()
    window = MainWindow(ThemeManager(LIGHT, reduce_motion=lambda: False))
    qtbot.addWidget(window)
    window.resize(400, 640)
    window.show()
    qtbot.waitExposed(window)
    window.tabs.setCurrentIndex(SCIENTIFIC_TAB)
    # Espera o esmaecimento da troca de aba terminar antes de fotografar a janela.
    qtbot.waitUntil(lambda: window.pages.currentWidget().graphicsEffect() is None, timeout=2000)
    return window


def _foto(qtbot, janela, progresso):
    janela.theme._set_progress(progresso)
    qtbot.wait(10)
    return janela.grab().toImage()


def _pontos(janela):
    """Um ponto dentro de cada tipo de elemento (fora do texto)."""

    def ponto(widget: QWidget, x=6, y=None):
        y = widget.height() // 2 if y is None else y
        return widget.mapTo(janela, QPoint(x, y))

    teclado = janela.scientific_keypad
    return {
        "fundo": QPoint(3, janela.height() - 3),
        "visor": ponto(janela.display, 8),
        "tecla": ponto(teclado.button("7")),
        "operador": ponto(teclado.button("÷")),
        "funcao": ponto(teclado.button("sin(")),
        "acao": ponto(teclado.button("clear")),
        "igual": ponto(teclado.button(EVALUATE)),
        "aba": ponto(janela.tabs, 8),
        "botao_tema": ponto(janela.theme_button, 5),
        "icone": janela.theme_button.mapTo(janela, janela.theme_button.rect().center()),
    }


def test_todos_os_elementos_mudam_juntos(qtbot, janela):
    claro = _foto(qtbot, janela, 0.0)
    meio = _foto(qtbot, janela, 0.5)
    escuro = _foto(qtbot, janela, 1.0)
    for nome, p in _pontos(janela).items():
        c, m, e = claro.pixelColor(p), meio.pixelColor(p), escuro.pixelColor(p)
        assert m != c and m != e, nome
        assert c != e, nome


@pytest.mark.parametrize("nome", [LIGHT, DARK])
def test_cada_elemento_usa_a_paleta_do_tema(qtbot, janela, nome):
    foto = _foto(qtbot, janela, 0.0 if nome == LIGHT else 1.0)
    outro = DARK if nome == LIGHT else LIGHT
    chaves = {
        "fundo": "window_bottom",
        "visor": "display_bg",
        "tecla": "key_bg",
        "operador": "operator_bg",
        "funcao": "function_bg",
        "acao": "action_bg",
        "igual": "equals_bg",
        "aba": "tab_bg",
        "botao_tema": "tab_bg",
    }
    pontos = _pontos(janela)
    for elemento, chave in chaves.items():
        cor = foto.pixelColor(pontos[elemento])
        assert distancia(cor, PALETTES[nome][chave]) < distancia(cor, PALETTES[outro][chave]), elemento


def test_icone_cruza_lua_e_sol(qtbot, janela):
    botao = janela.theme_button
    janela.theme._set_progress(0.0)
    lua = botao.grab().toImage()
    janela.theme._set_progress(0.5)
    meio = botao.grab().toImage()
    janela.theme._set_progress(1.0)
    sol = botao.grab().toImage()
    assert lua != sol and meio != lua and meio != sol


# --- animação de clique -------------------------------------------------------
def test_tecla_anima_ao_clicar(qtbot, janela):
    tecla = janela.scientific_keypad.button("7")
    qtbot.mousePress(tecla, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tecla._press > 0.9, timeout=1000)
    qtbot.mouseRelease(tecla, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: tecla._press == 0.0, timeout=1000)
    assert janela.editor.expression == "7"


def test_teclado_fisico_tambem_anima(qtbot, janela):
    tecla = janela.scientific_keypad.button("8")
    qtbot.keyClick(janela, Qt.Key.Key_8)
    qtbot.waitUntil(lambda: tecla._press > 0.5, timeout=1000)
    qtbot.waitUntil(lambda: tecla._press == 0.0, timeout=1000)


def test_clique_sem_animacao_quando_reduzir_movimento(qtbot):
    create_app()
    window = MainWindow(ThemeManager(LIGHT, reduce_motion=lambda: True))
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    tecla = window.common_keypad.button("7")
    qtbot.mousePress(tecla, Qt.MouseButton.LeftButton)
    qtbot.wait(5)
    assert tecla._press == 1.0
    assert not tecla._press_animation.state() == tecla._press_animation.State.Running
    qtbot.mouseRelease(tecla, Qt.MouseButton.LeftButton)


def test_aba_trigonometria_cabe_com_o_nome_inteiro(qtbot, janela):
    from ai_calc.ui.main_window import MIN_HEIGHT, MIN_WIDTH, TRIG_TAB

    assert janela.tabs.tabText(TRIG_TAB) == "Trigonometria"
    janela.resize(MIN_WIDTH, MIN_HEIGHT)
    qtbot.wait(20)
    assert janela.tabs.sizeHint().width() <= janela.tabs.width()
