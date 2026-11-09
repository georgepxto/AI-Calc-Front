"""Preferências do sistema operacional lidas pela interface."""

from __future__ import annotations

import sys

# SystemParametersInfo: "Efeitos de animação" (Configurações › Acessibilidade › Efeitos visuais).
_SPI_GETCLIENTAREAANIMATION = 0x1042


def reduce_motion() -> bool:
    """True quando o usuário desligou as animações no Windows."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes

        enabled = ctypes.c_int(1)
        ok = ctypes.windll.user32.SystemParametersInfoW(
            _SPI_GETCLIENTAREAANIMATION, 0, ctypes.byref(enabled), 0
        )
        return bool(ok) and not enabled.value
    except Exception:  # sem acesso à API: segue com animações
        return False


# DwmSetWindowAttribute: barra de título escura (Windows 10 20H1 em diante e Windows 11).
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def set_dark_title_bar(window, dark: bool) -> None:
    """Deixa a barra de título do Windows escura no tema escuro (e clara no claro).

    Sem isso, a barra continua branca por cima do app escuro. Fora do Windows, ou se a
    API não existir, não faz nada.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(window.winId())
        value = ctypes.c_int(1 if dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:  # API ausente: a barra fica no padrão do sistema
        pass
