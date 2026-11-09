"""Tema claro e escuro: a paleta única de cores do app e a transição entre eles.

Todo elemento é desenhado à mão (vidro) e pede a cor atual ao ThemeManager.
Durante a transição, o ThemeManager mistura as duas paletas quadro a quadro e
avisa a janela, que redesenha tudo junto. As duas paletas precisam ter
exatamente os mesmos nomes de cor.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QObject, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from .system import reduce_motion as system_reduce_motion

LIGHT = "claro"
DARK = "escuro"

# Duração da transição de tema (fácil de ajustar).
THEME_TRANSITION_MS = 450

# Vidro: opacidade de cada superfície sobre o fundo e intensidade dos brilhos.
KEY_ALPHA = 0.74        # teclas, abas e botões do topo
FUNCTION_ALPHA = 0.38   # teclas de função: vidro mais transparente, ficam em segundo plano
DISPLAY_ALPHA = 0.64    # visor e painéis
ACCENT_ALPHA = 0.95     # operadores, tecla "=" e aba selecionada
GLOW_ALPHA = 0.42       # brilhos de cor do fundo
TOP_TINT = 0.16         # quanto o topo da superfície clareia (degradê)
SHEEN_ALPHA = 0.42      # brilho na metade de cima
HOVER_ALPHA = 0.12      # clareada ao passar o mouse
RIM_ALPHA = 0.85        # reflexo na borda de cima (vidro líquido)
GLINT_ALPHA = 0.40      # reflexo fino na borda de baixo
SHADOW_ALPHA = 0.12     # sombra difusa embaixo
DIM_ALPHA = 0.40        # escurecimento atrás da janela de confirmação
DIALOG_ALPHA = 0.97     # cartão da janela de confirmação e gaveta do histórico

# Paleta neutra no estilo "liquid glass": claro em branco-gelo e escuro em grafite
# (nunca preto puro), com um único acento laranja para operadores e "=".
PALETTES: dict[str, dict[str, str]] = {
    LIGHT: {
        "window_top": "#F4F5F8",
        "window_bottom": "#E3E6EC",
        "glow_a": "#9EC5FF",
        "glow_b": "#FFC89A",
        "text": "#111318",
        "text_muted": "#4B5160",
        "error": "#B42318",
        "glass_rim": "#FFFFFF",
        "glass_edge": "#A3AAB8",
        "shadow": "#1B2030",
        "display_bg": "#FFFFFF",
        "key_bg": "#FFFFFF",
        "key_pressed": "#E3E6EC",
        "operator_bg": "#EE7300",
        "operator_pressed": "#CF6400",
        "operator_text": "#1F1000",
        "function_bg": "#F3F5F8",
        "function_pressed": "#DCE1E9",
        "action_bg": "#C9CFDA",
        "action_pressed": "#B6BDCA",
        "equals_bg": "#E86A00",
        "equals_hover": "#F57C00",
        "equals_pressed": "#C95C00",
        "equals_text": "#1F1000",
        "tab_bg": "#E3E6EC",
        "tab_selected_bg": "#FFFFFF",
        "tab_selected_text": "#111318",
        "tab_disabled_bg": "#E6E8ED",
        "tab_disabled_text": "#59606E",
        "focus": "#0A5BC4",
        "focus_on_accent": "#111318",
        "icon": "#2B2F38",
        "tooltip_bg": "#111318",
        "tooltip_text": "#FFFFFF",
        "scroll_handle": "#6E7585",
        "trig_sin": "#B0246A",
        "trig_cos": "#1F5FAE",
        "trig_tan": "#7A5600",
    },
    DARK: {
        "window_top": "#0C0D11",
        "window_bottom": "#17191F",
        "glow_a": "#2B4C8C",
        "glow_b": "#7A3F12",
        "text": "#F2F4F8",
        "text_muted": "#BCC3D0",
        "error": "#FF8A80",
        "glass_rim": "#C9D2E6",
        "glass_edge": "#454B58",
        "shadow": "#000000",
        "display_bg": "#1C1F26",
        "key_bg": "#282B33",
        "key_pressed": "#353943",
        "operator_bg": "#FFA51F",
        "operator_pressed": "#E8900A",
        "operator_text": "#1F1000",
        "function_bg": "#20232A",
        "function_pressed": "#2C3039",
        "action_bg": "#454A56",
        "action_pressed": "#535967",
        "equals_bg": "#FFB340",
        "equals_hover": "#FFC266",
        "equals_pressed": "#F09A12",
        "equals_text": "#1F1000",
        "tab_bg": "#2A2D35",
        "tab_selected_bg": "#5E6370",
        "tab_selected_text": "#FFFFFF",
        "tab_disabled_bg": "#22252C",
        "tab_disabled_text": "#B4BBC9",
        "focus": "#8CC8FF",
        "focus_on_accent": "#1F1000",
        "icon": "#FFB340",
        "tooltip_bg": "#F2F4F8",
        "tooltip_text": "#111318",
        "scroll_handle": "#8D94A5",
        "trig_sin": "#FFB3D9",
        "trig_cos": "#A8D6FF",
        "trig_tan": "#F5C451",
    },
}


# Cores de cada tipo de superfície de vidro (usado no desenho e nos testes):
# (fundo, fundo apertado, texto, opacidade, cor do contorno de foco).
ROLE_COLORS: dict[str, tuple[str, str, str, float, str]] = {
    "digit": ("key_bg", "key_pressed", "text", KEY_ALPHA, "focus"),
    "operator": ("operator_bg", "operator_pressed", "operator_text", ACCENT_ALPHA, "focus_on_accent"),
    "function": ("function_bg", "function_pressed", "text", FUNCTION_ALPHA, "focus"),
    "action": ("action_bg", "action_pressed", "text", KEY_ALPHA, "focus"),
    "equals": ("equals_bg", "equals_pressed", "equals_text", ACCENT_ALPHA, "focus_on_accent"),
    "theme": ("tab_bg", "key_pressed", "icon", KEY_ALPHA, "focus"),
    "tab": ("tab_bg", "tab_bg", "text", KEY_ALPHA, "focus"),
    "tab_selected": (
        "tab_selected_bg", "tab_selected_bg", "tab_selected_text", ACCENT_ALPHA, "focus_on_accent",
    ),
    "tab_disabled": ("tab_disabled_bg", "tab_disabled_bg", "tab_disabled_text", KEY_ALPHA, "focus"),
    # Itens do histórico não mudam de cor ao apertar (só encolhem): o texto discreto
    # da conta precisa de contraste 4,5:1 em qualquer estado.
    "history": ("key_bg", "key_bg", "text", KEY_ALPHA, "focus"),
}


# --- contas de cor (sem Qt, usadas também pelos testes) -----------------------
def _rgb(hex_color: str) -> tuple[int, int, int]:
    return int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)


def _hex(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(max(0, min(255, c))):02X}" for c in rgb)


def mix(a: str, b: str, amount: float) -> str:
    """Cor entre a e b (amount 0 = a, 1 = b)."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * amount for x, y in zip(ra, rb)))


def composite(front: str, alpha: float, back: str) -> str:
    """Cor vista quando "front" com essa opacidade fica sobre "back"."""
    return mix(back, front, alpha)


def _luminance(hex_color: str) -> float:
    channels = [c / 255 for c in _rgb(hex_color)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Contraste WCAG entre duas cores "#RRGGBB" (de 1 a 21)."""
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def backdrop_colors(palette: dict[str, str]) -> list[str]:
    """Cores possíveis do fundo da janela (degradê e manchas) atrás do vidro."""
    result = []
    for base in (palette["window_top"], palette["window_bottom"]):
        result.append(base)
        for glow in ("glow_a", "glow_b"):
            result.append(composite(palette[glow], GLOW_ALPHA, base))
    return result


def surface_colors(
    palette: dict[str, str],
    fill: str,
    alpha: float,
    hover_overlay: bool = True,
    backs: list[str] | None = None,
) -> list[str]:
    """Cores possíveis no meio de uma superfície de vidro (onde fica o texto).

    Considera todo fundo possível atrás do vidro, sem e com o brilho do
    mouse; o degradê do topo vale TOP_TINT/2 no meio da superfície. A tecla
    "=" não usa o brilho do mouse: ela escurece para "equals_hover". "backs"
    troca o fundo da janela por outro (ex.: vidro sobre vidro, no histórico).
    """
    center = mix(fill, palette["glass_rim"], TOP_TINT / 2)
    result = []
    for back in backs if backs is not None else backdrop_colors(palette):
        seen = composite(center, alpha, back)
        result.append(seen)
        if hover_overlay:
            result.append(composite(palette["glass_rim"], HOVER_ALPHA, seen))
    return result


def min_contrast(palette: dict[str, str], foreground: str, backgrounds: list[str]) -> float:
    return min(contrast_ratio(palette[foreground], back) for back in backgrounds)


# --- gerente de tema ----------------------------------------------------------
class ThemeManager(QObject):
    """Tema atual, transição animada e cores do momento para quem desenha.

    O progresso vai de 0 (claro) a 1 (escuro). Clicar de novo no meio da
    transição só inverte o sentido da animação, que volta do ponto atual.
    """

    changed = Signal()            # as cores mudaram (a cada quadro da transição)
    theme_changed = Signal(str)   # o tema escolhido mudou (começo da transição)

    def __init__(
        self,
        name: str | None = None,
        parent: QObject | None = None,
        reduce_motion: Callable[[], bool] = system_reduce_motion,
    ) -> None:
        super().__init__(parent)
        self._name = name or system_theme()
        self._reduce_motion = reduce_motion
        self._progress = 1.0 if self._name == DARK else 0.0
        self._colors = self._blend(self._progress)

        self._animation = QVariantAnimation(self)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setDuration(THEME_TRANSITION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.valueChanged.connect(self._set_progress)
        self._animation.finished.connect(self._apply_app_palette)

    # --- leitura ---
    @property
    def name(self) -> str:
        return self._name

    @property
    def progress(self) -> float:
        return self._progress

    @property
    def is_animating(self) -> bool:
        return self._animation.state() == QVariantAnimation.State.Running

    def reduce_motion(self) -> bool:
        return self._reduce_motion()

    def color(self, key: str) -> QColor:
        return QColor(self._colors[key])

    def hex(self, key: str) -> str:
        return self._colors[key]

    # --- mudança ---
    def apply(self) -> None:
        """Aplica o estado atual (usado ao abrir a janela)."""
        self._apply_app_palette()
        self.theme_changed.emit(self._name)
        self.changed.emit()

    def toggle(self) -> None:
        self.set_theme(DARK if self._name == LIGHT else LIGHT)

    def set_theme(self, name: str) -> None:
        if name not in PALETTES:
            raise ValueError(f"Tema desconhecido: {name}")
        self._name = name
        self.theme_changed.emit(name)
        target = 1.0 if name == DARK else 0.0

        if self._reduce_motion():
            self._animation.stop()
            self._set_progress(target)
            self._apply_app_palette()
            return

        direction = (
            QVariantAnimation.Direction.Forward if target == 1.0
            else QVariantAnimation.Direction.Backward
        )
        self._animation.setDirection(direction)
        if not self.is_animating and self._progress != target:
            # Parada, a animação recomeça da ponta certa (0 indo, 1 voltando).
            self._animation.start()

    def _set_progress(self, value: float) -> None:
        self._progress = float(value)
        self._colors = self._blend(self._progress)
        self.changed.emit()

    @staticmethod
    def _blend(progress: float) -> dict[str, str]:
        light, dark = PALETTES[LIGHT], PALETTES[DARK]
        return {key: mix(light[key], dark[key], progress) for key in light}

    def _apply_app_palette(self) -> None:
        # Cores dos elementos padrão do Qt (dicas, menus, caixas de mensagem).
        app = QApplication.instance()
        if app is None:
            return
        colors = self._colors
        palette = QPalette()
        roles = {
            QPalette.ColorRole.Window: "window_top",
            QPalette.ColorRole.WindowText: "text",
            QPalette.ColorRole.Base: "display_bg",
            QPalette.ColorRole.Text: "text",
            QPalette.ColorRole.Button: "key_bg",
            QPalette.ColorRole.ButtonText: "text",
            QPalette.ColorRole.ToolTipBase: "tooltip_bg",
            QPalette.ColorRole.ToolTipText: "tooltip_text",
            QPalette.ColorRole.Highlight: "tab_selected_bg",
            QPalette.ColorRole.HighlightedText: "tab_selected_text",
        }
        for role, key in roles.items():
            palette.setColor(role, QColor(colors[key]))
        app.setPalette(palette)


def system_theme() -> str:
    """Tema do Windows (claro quando não dá para saber)."""
    app = QApplication.instance()
    if app is not None and app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return DARK
    return LIGHT
