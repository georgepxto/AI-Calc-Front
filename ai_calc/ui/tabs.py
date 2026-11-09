"""Controle segmentado de vidro (Comum, Científica, Trigonometria).

Uma cápsula de vidro única com as opções lado a lado; a opção escolhida fica
numa "lente" mais clara que desliza até a nova opção quando ela muda.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QTabBar, QWidget

from .glass import capsule_radius, paint_focus_ring, paint_glass
from .theme import ROLE_COLORS, ThemeManager

TAB_PADDING = 8
TAB_HEIGHT = 40
TAB_INSET = 3          # espaço entre a borda da cápsula e a lente
LENS_MS = 260          # deslize da lente até a opção escolhida


class GlassTabBar(QTabBar):
    def __init__(self, theme: ThemeManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setExpanding(True)
        self.setDrawBase(False)
        self.setUsesScrollButtons(False)
        font = QFont(self.font())
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)

        self._lens: QRectF | None = None        # posição da lente durante o deslize
        self._lens_animation = QVariantAnimation(self)
        self._lens_animation.setDuration(LENS_MS)
        self._lens_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._lens_animation.valueChanged.connect(self._set_lens)
        self._lens_animation.finished.connect(self._lens_done)
        self._last_index = -1
        self._keyboard_focus = False            # contorno só quando o foco veio do teclado
        self.currentChanged.connect(self._slide_lens)

    # --- tamanho ---
    def tabSizeHint(self, index: int) -> QSize:  # noqa: N802 (nome do Qt)
        width = QFontMetrics(self.font()).horizontalAdvance(self.tabText(index))
        return QSize(width + 2 * TAB_PADDING, TAB_HEIGHT)

    def minimumTabSizeHint(self, index: int) -> QSize:  # noqa: N802 (nome do Qt)
        return self.tabSizeHint(index)

    # --- lente ---
    def _lens_rect(self, index: int) -> QRectF:
        tab = QRectF(self.tabRect(index))
        inset = TAB_INSET + 1
        return tab.adjusted(inset, inset, -inset, -(inset + 2))

    def _slide_lens(self, index: int) -> None:
        previous = self._last_index
        self._last_index = index
        self._lens_animation.stop()
        if (
            previous < 0 or index < 0 or previous >= self.count()
            or self._theme.reduce_motion() or not self.isVisible()
        ):
            self._lens = None
            self.update()
            return
        start = self._lens if self._lens is not None else self._lens_rect(previous)
        self._lens = QRectF(start)              # já pinta a lente no ponto de partida
        self._lens_animation.setStartValue(start)
        self._lens_animation.setEndValue(self._lens_rect(index))
        self._lens_animation.start()

    def _set_lens(self, value: QRectF) -> None:
        self._lens = QRectF(value)
        self.update()

    def _lens_done(self) -> None:
        self._lens = None
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().resizeEvent(event)
        # A barra mudou de largura no meio do deslize (ex.: o histórico saiu da lateral):
        # a lente continua, agora indo para a nova posição da opção escolhida.
        if self._lens_animation.state() == QVariantAnimation.State.Running:
            self._lens_animation.setEndValue(self._lens_rect(self.currentIndex()))

    # --- foco ---
    def focusInEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().focusInEvent(event)
        self._keyboard_focus = event.reason() in (
            Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason,
            Qt.FocusReason.ShortcutFocusReason,
        )
        self.update()

    def focusOutEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        super().focusOutEvent(event)
        self._keyboard_focus = False
        self.update()

    def keyPressEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        # Setas trocam a opção: quem usa o teclado precisa ver onde está o foco.
        self._keyboard_focus = True
        super().keyPressEvent(event)

    # --- desenho ---
    def paintEvent(self, event) -> None:  # noqa: N802 (nome do Qt)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font())
        theme = self._theme
        if self.count() == 0:
            return

        # Cápsula que envolve todas as opções.
        fill_key, _, _, alpha, _ = ROLE_COLORS["tab"]
        track = QRectF(self.rect()).adjusted(1, 1, -1, -3)
        paint_glass(painter, track, capsule_radius(track), theme, theme.hex(fill_key), alpha)

        # Lente da opção escolhida (deslizando, se estiver em movimento).
        current = self.currentIndex()
        if current >= 0:
            lens = self._lens if self._lens is not None else self._lens_rect(current)
            sel_fill, _, _, sel_alpha, sel_focus = ROLE_COLORS["tab_selected"]
            paint_glass(painter, lens, capsule_radius(lens), theme, theme.hex(sel_fill), sel_alpha)
            if self.hasFocus() and self._keyboard_focus:
                paint_focus_ring(painter, lens, capsule_radius(lens), theme.color(sel_focus))

        for index in range(self.count()):
            if not self.isTabEnabled(index):
                role = "tab_disabled"
            elif index == current:
                role = "tab_selected"
            else:
                role = "tab"
            color = theme.color(ROLE_COLORS[role][2])
            painter.setPen(color)
            painter.drawText(self._lens_rect(index), Qt.AlignmentFlag.AlignCenter, self.tabText(index))
