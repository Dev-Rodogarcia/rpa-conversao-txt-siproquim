"""
Janela principal da interface PySide6 — Conversor SIPROQUIM.
Segue o design system definido em docs/identidade_visual.md.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
import traceback
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QSettings,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QImage,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from main import processar_pdf, ProcessamentoInterrompido
except ImportError:
    import time as _time

    class ProcessamentoInterrompido(RuntimeError):  # type: ignore[misc]
        pass

    def processar_pdf(pdf, cnpj, saida, **kwargs):  # type: ignore[misc]
        _time.sleep(2)
        with open(saida, "w") as _f:
            _f.write("Teste")
        return saida


try:
    from src.config.filiais import FiliaisManager
except ImportError:
    from src.config import FiliaisManager  # type: ignore[no-redef]

from .constants import UIConstants
from .progress_manager import ProgressManager
from .validators import FormValidator, somente_digitos
from .utils import downloads_dir, extrair_ano_padrao, extrair_mes_padrao, gerar_nome_arquivo_saida
from src.gerador.layout_constants import CNPJ_TAMANHO
from src.gerador.validators import validar_cnpj, validar_cpf
from src.processador.aprendizado_store import AprendizadoStore


def _recursos_dir() -> Path:
    """Retorna o diretório raiz de recursos (funciona em dev e no app compilado)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Paleta de cores (modo claro)
# ---------------------------------------------------------------------------
PALETA_CLARA: dict[str, str] = {
    "primaria":              "#21478A",
    "primaria_hover":        "#1A3970",
    "primaria_pressed":      "#15315E",
    "secundaria":            "#2B89D9",
    "fundo":                 "#F3F7FB",
    "sucesso":               "#1F7A63",
    "perigo":                "#B55045",
    "branco":                "#FFFFFF",
    "texto_padrao":          "#0F172A",
    "texto_mutado":          "#64748B",
    "texto_sutil":           "#94A3B8",
    "borda":                 "#D0E2EF",
    "borda_forte":           "#9BBDD4",
    "superficie_secundaria": "#F7FAFD",
    "superficie_alt":        "#EEF4F9",
    "info":                  "#2B89D9",
    "aviso":                 "#B7791F",
    "aviso_soft":            "#FFF5E4",
    "sucesso_soft":          "#EAEFF4",
    "perigo_soft":           "#FBEAE8",
    "badge_neutro":          "#EFF6FF",
    "badge_executando":      "#E0F2FE",
    "sombra_cor":            "rgba(15,23,42,0.094)",
    "btn_pri_bg":            "#21478A",
    "btn_pri_hover":         "#1A3970",
    "btn_pri_pressed":       "#15315E",
    "btn_pri_text":          "#FFFFFF",
    "input_bg":              "#FFFFFF",
    "input_border":          "#7AADC9",
    "input_focus":           "#21478A",
    "campo_bg":              "#EDF3F9",
    "campo_borda":           "#B8D0E4",
    "scroll_track":          "#EEF3F8",
    "scroll_track_borda":    "#D9E4EF",
    "scroll_handle":         "#8FA6BE",
    "scroll_handle_borda":   "#7D95AE",
    "scroll_handle_hover":   "#6F87A2",
    "scroll_handle_press":   "#5E7690",
    "kicker_bg":             "#EAF2FC",
    "kicker_text":           "#21478A",
}

PALETA_ESCURA: dict[str, str] = {
    "primaria":              "#3B82F6",
    "primaria_hover":        "#2563EB",
    "primaria_pressed":      "#1D4ED8",
    "secundaria":            "#60A5FA",
    "fundo":                 "#0B1120",
    "sucesso":               "#22C55E",
    "perigo":                "#EF4444",
    "branco":                "#111827",
    "texto_padrao":          "#E5E7EB",
    "texto_mutado":          "#9CA3AF",
    "texto_sutil":           "#94A3B8",
    "borda":                 "#1F2937",
    "borda_forte":           "#374151",
    "superficie_secundaria": "#1A2236",
    "superficie_alt":        "#1E2940",
    "info":                  "#60A5FA",
    "aviso":                 "#F59E0B",
    "aviso_soft":            "#1C1A0F",
    "sucesso_soft":          "#0F1A14",
    "perigo_soft":           "#1F1210",
    "badge_neutro":          "#1E2D4A",
    "badge_executando":      "#0C2A3B",
    "sombra_cor":            "rgba(0,0,0,0.35)",
    "btn_pri_bg":            "#3B82F6",
    "btn_pri_hover":         "#2563EB",
    "btn_pri_pressed":       "#1D4ED8",
    "btn_pri_text":          "#FFFFFF",
    "input_bg":              "#1F2937",
    "input_border":          "#374151",
    "input_focus":           "#3B82F6",
    "campo_bg":              "#161F2E",
    "campo_borda":           "#2D3F57",
    "scroll_track":          "#1A2236",
    "scroll_track_borda":    "#1F2937",
    "scroll_handle":         "#374151",
    "scroll_handle_borda":   "#4B5563",
    "scroll_handle_hover":   "#6B7280",
    "scroll_handle_press":   "#9CA3AF",
    "kicker_bg":             "#1E2D4A",
    "kicker_text":           "#3B82F6",
}

# Status badge colors: (fundo, texto, borda)
MAPA_CORES_STATUS: dict[str, tuple[str, str, str]] = {
    "Parado":       ("#F8FAFC", "#475569", "#CBD5E1"),
    "Executando":   ("#E8F1FF", "#1D4ED8", "#BFDBFE"),
    "Erro":         ("#FEF2F2", "#B42318", "#FECACA"),
    "Sucesso":      ("#ECFDF3", "#166534", "#BBF7D0"),
    "Processando":  ("#EFF6FF", "#1E40AF", "#BFDBFE"),
    "Atenção":      ("#FFFBEB", "#92400E", "#FDE68A"),
    "Interrompido": ("#F8FAFC", "#64748B", "#CBD5E1"),
}

# Cores dos logs no tema escuro (texto claro sobre fundo escuro)
LOG_CORES_ESCURO: dict[str, str] = {
    "INFO":    "#93C5FD",
    "SUCESSO": "#6EE7B7",
    "ERRO":    "#FCA5A5",
    "AVISO":   "#FCD34D",
    "DEBUG":   "#C4B5FD",
}

# ---------------------------------------------------------------------------
# Adaptador de log (interface unificada sobre LogManagerQt)
# ---------------------------------------------------------------------------
class LogManagerAdapter:
    """Wraps LogManagerQt, adding origem/etapa params (ignored in text display)."""

    def __init__(self, textbox: "QTextEdit") -> None:
        from .log_manager_qt import LogManagerQt
        self._inner = LogManagerQt(
            textbox,
            font_family="Consolas",
            font_size=UIConstants.LOG_FONT_SIZE_DEFAULT,
        )

    # Compatibilidade de interface
    def definir_etapa(self, etapa: str) -> None:
        pass  # no-op no modo texto

    def adicionar(
        self,
        mensagem: str,
        tipo: str = "INFO",
        origem: str = "Sistema",
        etapa: Optional[str] = None,
    ) -> None:
        prefixo = f"[{origem}] " if origem and origem not in ("Sistema",) else ""
        self._inner.adicionar(f"{prefixo}{mensagem}", tipo)

    def adicionar_erro(self, msg: str, origem: str = "Sistema") -> None:
        self.adicionar(msg, "ERRO", origem)

    def adicionar_sucesso(self, msg: str, origem: str = "Sistema") -> None:
        self.adicionar(msg, "SUCESSO", origem)

    def adicionar_info(self, msg: str, origem: str = "Sistema") -> None:
        self.adicionar(msg, "INFO", origem)

    def adicionar_aviso(self, msg: str, origem: str = "Sistema") -> None:
        self.adicionar(msg, "AVISO", origem)

    def adicionar_debug(self, msg: str) -> None:
        self._inner.adicionar_debug(msg)

    def adicionar_banner(self, titulo: str, tipo: str = "INFO") -> None:
        self._inner.adicionar_banner(titulo, tipo)

    def limpar(self) -> None:
        self._inner.limpar()

    def exportar(self, caminho: str) -> None:
        self._inner.exportar(caminho)

    def ajustar_fonte(self, delta: int) -> None:
        self._inner.ajustar_fonte(delta)

    def atualizar_cores_tema(self, tema: str) -> None:
        mapa = LOG_CORES_ESCURO if tema == "escuro" else {}
        self._inner.definir_cores_override(mapa)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sombra(widget: QWidget, blur: int = 24, y: int = 5) -> None:
    ef = QGraphicsDropShadowEffect(widget)
    ef.setBlurRadius(blur)
    ef.setOffset(0, y)
    ef.setColor(QColor(15, 23, 42, 24))
    widget.setGraphicsEffect(ef)


# ---------------------------------------------------------------------------
# Botão primário com animação de hover
# ---------------------------------------------------------------------------
class BotaoPrimarioQt(QPushButton):
    def __init__(self, texto: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(texto, parent)
        self.setObjectName("botaoPrimario")
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.valueChanged.connect(self._on_cor)
        self._cor_base = QColor("#21478A")
        self._cor_hover = QColor("#1A3970")
        self._cor_text = "#FFFFFF"
        self._habilitado = True

    def definir_paleta(self, cor_base: str, cor_hover: str, cor_text: str) -> None:
        self._cor_base = QColor(cor_base)
        self._cor_hover = QColor(cor_hover)
        self._cor_text = cor_text
        if self._habilitado:
            self._aplicar_cor(self._cor_base)

    def _on_cor(self, cor: QColor) -> None:
        if self._habilitado:
            self._aplicar_cor(cor)

    def _aplicar_cor(self, cor: QColor) -> None:
        self.setStyleSheet(f"""
            QPushButton {{
                background: {cor.name()};
                color: {self._cor_text};
                border: none;
                border-radius: 14px;
                padding: 14px 24px;
                font-size: 15px;
                font-weight: 700;
                min-width: 180px;
            }}
        """)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802
        self._habilitado = enabled
        super().setEnabled(enabled)
        if not enabled:
            self.setStyleSheet("""
                QPushButton {
                    background: #C8D6E8;
                    color: #8FA3BC;
                    border: none;
                    border-radius: 14px;
                    padding: 14px 24px;
                    font-size: 15px;
                    font-weight: 700;
                    min-width: 180px;
                }
            """)
        else:
            self._aplicar_cor(self._cor_base)

    def enterEvent(self, event) -> None:  # noqa: N802
        if self._habilitado:
            self._anim.stop()
            self._anim.setStartValue(self._cor_base)
            self._anim.setEndValue(self._cor_hover)
            self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._habilitado:
            self._anim.stop()
            self._anim.setStartValue(self._cor_hover)
            self._anim.setEndValue(self._cor_base)
            self._anim.start()
        super().leaveEvent(event)


# ===========================================================================
# Janela principal
# ===========================================================================
class JanelaConversor(QMainWindow):
    """Janela principal do Conversor SIPROQUIM — PySide6."""

    _sinal_thread: Signal = Signal(object)

    def __init__(self) -> None:
        super().__init__()

        # Estado de processamento
        self._is_busy = False
        self._flag_cancelamento = False
        self._thread_processamento: Optional[threading.Thread] = None
        self._thread_aprendizado: Optional[threading.Thread] = None

        # Gerenciadores
        self._filiais_manager = FiliaisManager()
        self._progress_manager = ProgressManager()
        self._historico_mgr: Optional[LogManagerAdapter] = None

        # Tema
        self._tema_atual: str = "claro"
        self._paleta_atual: dict = PALETA_CLARA
        self._logo_pixmap_original: Optional[QPixmap] = None

        # Fullscreen logs
        self._dialog_logs: Optional["QDialog"] = None
        self._layout_logs_card: Optional[QVBoxLayout] = None

        # Dados do pipeline
        self._ajustes_por_nf: dict = {}
        self._avisos_gerais: list = []
        self._alertas_operacionais: dict = {}
        self._total_registros_extraidos = 0
        self._total_nfs_dedup = 0
        self._ultima_estatistica: dict = {}

        try:
            self._aprendizado_store = AprendizadoStore.get_instance()
        except Exception:
            self._aprendizado_store = None

        self._sinal_thread.connect(self._executar_callback)

        self.setWindowTitle(UIConstants.WINDOW_TITLE)
        self.resize(1450, 960)
        self.setMinimumSize(UIConstants.WINDOW_MIN_WIDTH, UIConstants.WINDOW_MIN_HEIGHT)

        icon_path = _recursos_dir() / "public" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._aplicar_estilo_global()
        self._montar_interface()

        self._historico_mgr = LogManagerAdapter(self.txt_logs)
        self._carregar_tema_salvo()
        self._inicializar_logs()
        self._verificar_habilitar_botao()

    # ------------------------------------------------------------------
    # Thread-safety
    # ------------------------------------------------------------------
    def _executar_callback(self, func) -> None:
        func()

    def _depois(self, func) -> None:
        self._sinal_thread.emit(func)

    # ------------------------------------------------------------------
    # Estilo global
    # ------------------------------------------------------------------
    def _aplicar_estilo_global(self, paleta: Optional[dict] = None) -> None:
        p = paleta or self._paleta_atual
        qss = f"""
            * {{ font-family: 'Manrope', 'Segoe UI', Arial, sans-serif; }}
            QMainWindow, QWidget#widgetCentral {{
                background: {p['fundo']};
            }}
            QScrollArea#scrollPrincipal {{
                background: {p['fundo']};
                border: none;
            }}
            QScrollArea#scrollPrincipal > QWidget > QWidget {{
                background: {p['fundo']};
            }}

            /* ── Cards ── */
            QFrame#cabecalhoPainel {{
                background: {p['branco']};
                border: 1px solid {p['borda']};
                border-radius: 24px;
            }}
            QFrame#cabecalhoStatus {{
                background: {p['superficie_secundaria']};
                border: 1px solid {p['borda_forte']};
                border-radius: 20px;
            }}
            QFrame#cartaoPadrao,
            QFrame#cartaoAprendizado,
            QFrame#cartaoEstatistica,
            QFrame#containerHistorico {{
                background: {p['branco']};
                border: 1px solid {p['borda']};
                border-radius: 20px;
            }}
            QFrame#painelCampo {{
                background: {p['campo_bg']};
                border: 1px solid {p['campo_borda']};
                border-radius: 18px;
            }}
            QFrame#frameMemoria {{
                background: {p['superficie_alt']};
                border: 1px solid {p['borda']};
                border-radius: 14px;
            }}
            QFrame#frameResumoHistorico {{
                background: {p['superficie_alt']};
                border: 1px solid {p['borda']};
                border-radius: 14px;
            }}

            /* ── Labels especiais ── */
            QLabel#etiquetaTopo {{
                background: {p['kicker_bg']};
                color: {p['kicker_text']};
                border-radius: 11px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QLabel#logoFallback {{
                color: {p['primaria']};
                font-size: 24px;
                font-weight: 800;
            }}
            QLabel#rotuloPercentual {{
                color: {p['primaria']};
                font-size: 28px;
                font-weight: 800;
            }}
            QLabel#etiquetaStatusRobo {{
                border-radius: 25px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
                border: 1px solid;
            }}

            /* ── Botão primário (gerenciado inline via BotaoPrimarioQt) ── */

            /* ── Botão secundário ── */
            QPushButton#botaoSecundario {{
                background: {p['branco']};
                color: {p['primaria']};
                border: 2px solid {p['borda_forte']};
                border-radius: 12px;
                padding: 9px 18px;
                font-size: 13px;
                font-weight: 700;
                min-width: 100px;
            }}
            QPushButton#botaoSecundario:hover {{
                background: {p['badge_neutro']};
                border-color: {p['primaria']};
            }}
            QPushButton#botaoSecundario:pressed {{
                background: {p['borda']};
            }}
            QPushButton#botaoSecundario:disabled {{
                background: {p['superficie_alt']};
                color: {p['texto_sutil']};
                border-color: {p['borda']};
            }}

            /* ── Botão de perigo (cancelar) ── */
            QPushButton#botaoPerigo {{
                background: {p['branco']};
                color: {p['perigo']};
                border: 2px solid {p['perigo']};
                border-radius: 14px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 700;
                min-width: 160px;
            }}
            QPushButton#botaoPerigo:hover {{
                background: {p['perigo_soft']};
            }}
            QPushButton#botaoPerigo:disabled {{
                background: {p['superficie_alt']};
                color: {p['texto_sutil']};
                border-color: {p['borda']};
            }}

            /* ── Botão de tabela ── */
            QPushButton#botaoTabela {{
                background: #EFF5FD;
                color: {p['primaria']};
                border: 1px solid {p['borda_forte']};
                border-radius: 10px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton#botaoTabela:hover {{ background: #E4EEFA; }}
            QPushButton#botaoTabela:disabled {{
                background: #F1F5F9;
                color: {p['texto_sutil']};
                border-color: #E2E8F0;
            }}

            /* ── Botão de paginação ── */
            QPushButton#botaoPaginacao {{
                background: {p['branco']};
                color: {p['primaria']};
                border: 1px solid {p['borda_forte']};
                border-radius: 10px;
                min-width: 38px; max-width: 38px;
                min-height: 34px; max-height: 34px;
                font-weight: 800;
            }}
            QPushButton#botaoPaginacao:hover {{ background: #F8FBFF; }}
            QPushButton#botaoPaginacao:disabled {{
                color: {p['texto_sutil']};
                border-color: {p['borda']};
            }}

            /* ── Botão de controle ── */
            QPushButton#botaoControle {{
                background: {p['badge_neutro']};
                color: {p['primaria']};
                border: 1px solid {p['borda_forte']};
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 12px;
                font-weight: 700;
                min-width: 32px;
            }}
            QPushButton#botaoControle:hover {{
                background: {p['borda']};
                border-color: {p['primaria']};
            }}
            QPushButton#botaoControle:disabled {{
                background: {p['superficie_alt']};
                color: {p['texto_sutil']};
                border-color: {p['borda']};
            }}

            /* ── Desabilitado global ── */
            QPushButton:disabled {{
                background: {p['superficie_alt']};
                color: {p['texto_sutil']};
                border-color: {p['borda']};
            }}

            /* ── Inputs ── */
            QLineEdit {{
                background-color: {p['input_bg']};
                border: 2px solid {p['input_border']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                font-weight: 500;
                color: {p['texto_padrao']};
                min-height: 38px;
                selection-background-color: {p['primaria']};
            }}
            QLineEdit:focus {{ border-color: {p['input_focus']}; }}
            QLineEdit:read-only {{
                background: {p['input_bg']};
                color: {p['texto_mutado']};
                border-style: dashed;
            }}
            QLineEdit:disabled {{
                background: {p['superficie_alt']};
                color: {p['texto_sutil']};
                border-color: {p['borda']};
            }}

            /* ── ComboBox ── */
            QComboBox {{
                background-color: {p['input_bg']};
                border: 2px solid {p['input_border']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 13px;
                font-weight: 500;
                color: {p['texto_padrao']};
                min-height: 38px;
            }}
            QComboBox:focus {{ border-color: {p['input_focus']}; }}
            QComboBox::drop-down {{ border: none; width: 28px; }}
            QComboBox QAbstractItemView {{
                background: {p['branco']};
                border: 1px solid {p['borda_forte']};
                border-radius: 8px;
                selection-background-color: {p['badge_neutro']};
                selection-color: {p['texto_padrao']};
                color: {p['texto_padrao']};
                padding: 4px;
            }}

            /* ── Barra de progresso ── */
            QProgressBar#barraProgresso {{
                border: none;
                border-radius: 5px;
                background: {p['superficie_alt']};
                min-height: 10px;
                max-height: 10px;
                text-align: center;
            }}
            QProgressBar#barraProgresso::chunk {{
                border-radius: 5px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p['primaria']},
                    stop:1 {p['secundaria']}
                );
            }}

            /* ── Painel de logs ── */
            QTextEdit#texteLogs {{
                background: {p['branco']};
                border: none;
                color: {p['texto_padrao']};
                padding: 8px;
                selection-background-color: {p['primaria']};
                selection-color: {p['branco']};
            }}

            /* ── Rodapé ── */
            QFrame#rodapePainel {{
                background: {p['branco']};
                border: 1px solid {p['borda']};
                border-radius: 16px;
            }}

            /* ── Scrollbar ── */
            QScrollBar:vertical {{
                background: {p['scroll_track']};
                width: 14px;
                margin: 6px 2px 6px 2px;
                border: 1px solid {p['scroll_track_borda']};
                border-radius: 7px;
            }}
            QScrollBar::handle:vertical {{
                background: {p['scroll_handle']};
                border: 1px solid {p['scroll_handle_borda']};
                border-radius: 6px;
                min-height: 42px;
            }}
            QScrollBar::handle:vertical:hover   {{ background: {p['scroll_handle_hover']}; }}
            QScrollBar::handle:vertical:pressed {{ background: {p['scroll_handle_press']}; }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent; border: none; height: 0px;
            }}

            /* ── Labels categorizados ── */
            QLabel#labelMutado {{
                color: {p['texto_mutado']};
                background: transparent;
                border: none;
            }}
            QLabel#labelSutil {{
                color: {p['texto_sutil']};
                background: transparent;
                border: none;
            }}
            QLabel {{
                color: {p['texto_padrao']};
                background: transparent;
            }}

            /* ── Botão de tema ── */
            /* Dialogos e popups */
            QMessageBox,
            QInputDialog,
            QDialog {{
                background: {p['branco']};
                color: {p['texto_padrao']};
            }}
            QMessageBox QLabel,
            QInputDialog QLabel,
            QDialog QLabel {{
                color: {p['texto_padrao']};
                background: transparent;
            }}
            QMessageBox QPushButton,
            QInputDialog QPushButton,
            QDialog QPushButton {{
                background: {p['btn_pri_bg']};
                color: {p['btn_pri_text']};
                border: 1px solid {p['borda_forte']};
                border-radius: 8px;
                padding: 7px 16px;
                min-width: 78px;
                font-weight: 700;
            }}
            QMessageBox QPushButton:hover,
            QInputDialog QPushButton:hover,
            QDialog QPushButton:hover {{
                background: {p['btn_pri_hover']};
            }}
            QMessageBox QLineEdit,
            QInputDialog QLineEdit,
            QDialog QLineEdit {{
                background: {p['input_bg']};
                color: {p['texto_padrao']};
                border: 2px solid {p['input_border']};
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: {p['primaria']};
                selection-color: {p['btn_pri_text']};
            }}

            QPushButton#botaoTema {{
                background: {p['superficie_alt']};
                color: {p['texto_padrao']};
                border: 1px solid {p['borda_forte']};
                border-radius: 18px;
                font-size: 18px;
            }}
            QPushButton#botaoTema:hover {{
                background: {p['borda']};
                border-color: {p['primaria']};
            }}
        """
        self.setStyleSheet(qss)

    def _estilo_dialogo(self) -> str:
        p = self._paleta_atual
        return f"""
            QDialog, QMessageBox, QInputDialog {{
                background: {p['branco']};
                color: {p['texto_padrao']};
            }}
            QLabel {{
                color: {p['texto_padrao']};
                background: transparent;
                font-size: 13px;
            }}
            QLineEdit {{
                background: {p['input_bg']};
                color: {p['texto_padrao']};
                border: 2px solid {p['input_border']};
                border-radius: 8px;
                padding: 7px 10px;
                min-height: 30px;
                selection-background-color: {p['primaria']};
                selection-color: {p['btn_pri_text']};
            }}
            QLineEdit:focus {{
                border-color: {p['input_focus']};
            }}
            QPushButton {{
                background: {p['btn_pri_bg']};
                color: {p['btn_pri_text']};
                border: 1px solid {p['borda_forte']};
                border-radius: 8px;
                padding: 7px 16px;
                min-width: 78px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {p['btn_pri_hover']};
            }}
            QPushButton:pressed {{
                background: {p['primaria_pressed']};
            }}
        """

    def _preparar_dialogo(self, dialogo: QDialog) -> QDialog:
        dialogo.setStyleSheet(self._estilo_dialogo())
        if not self.windowIcon().isNull():
            dialogo.setWindowIcon(self.windowIcon())
        return dialogo

    def _mostrar_mensagem_qt(
        self,
        icone: QMessageBox.Icon,
        titulo: str,
        mensagem: str,
        botoes=QMessageBox.Ok,
        botao_padrao=QMessageBox.Ok,
    ):
        dialogo = QMessageBox(self)
        dialogo.setIcon(icone)
        dialogo.setWindowTitle(titulo)
        dialogo.setText(mensagem)
        dialogo.setStandardButtons(botoes)
        dialogo.setDefaultButton(botao_padrao)
        self._preparar_dialogo(dialogo)
        return dialogo.exec()

    def _mostrar_aviso(self, titulo: str, mensagem: str):
        return self._mostrar_mensagem_qt(QMessageBox.Warning, titulo, mensagem)

    def _mostrar_erro_popup(self, titulo: str, mensagem: str):
        return self._mostrar_mensagem_qt(QMessageBox.Critical, titulo, mensagem)

    def _mostrar_info(self, titulo: str, mensagem: str):
        return self._mostrar_mensagem_qt(QMessageBox.Information, titulo, mensagem)

    def _perguntar_popup(self, titulo: str, mensagem: str) -> bool:
        resposta = self._mostrar_mensagem_qt(
            QMessageBox.Question,
            titulo,
            mensagem,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        return resposta == QMessageBox.Yes

    def _pedir_texto_popup(self, titulo: str, mensagem: str) -> tuple[str, bool]:
        dialogo = QInputDialog(self)
        dialogo.setWindowTitle(titulo)
        dialogo.setLabelText(mensagem)
        dialogo.setInputMode(QInputDialog.TextInput)
        dialogo.setTextEchoMode(QLineEdit.Normal)
        self._preparar_dialogo(dialogo)
        ok = dialogo.exec() == QDialog.Accepted
        return dialogo.textValue(), ok

    # ------------------------------------------------------------------
    # Montagem da interface
    # ------------------------------------------------------------------
    def _montar_interface(self) -> None:
        scroll = QScrollArea()
        scroll.setObjectName("scrollPrincipal")
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(scroll)

        widget_central = QWidget()
        widget_central.setObjectName("widgetCentral")
        scroll.setWidget(widget_central)

        layout = QVBoxLayout(widget_central)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(20)

        layout.addWidget(self._criar_cabecalho())
        layout.addWidget(self._criar_secao_controles())
        layout.addWidget(self._criar_secao_aprendizado())
        layout.addLayout(self._criar_grade_estatisticas())
        layout.addWidget(self._criar_secao_progresso())
        layout.addWidget(self._criar_secao_logs(), 1)
        layout.addWidget(self._criar_rodape())

    # ------------------------------------------------------------------
    # Cabeçalho
    # ------------------------------------------------------------------
    def _criar_cabecalho(self) -> QFrame:
        p = self._paleta_atual
        card = QFrame()
        card.setObjectName("cabecalhoPainel")
        _sombra(card, blur=34, y=10)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(20)

        # Marca (logo + divisor + título)
        marca = QWidget()
        marca_layout = QHBoxLayout(marca)
        marca_layout.setContentsMargins(0, 0, 0, 0)
        marca_layout.setSpacing(16)

        self._logo_lbl = QLabel()
        self._logo_lbl.setAlignment(Qt.AlignVCenter)
        logo_path = _recursos_dir() / "public" / "logo.png"
        if logo_path.exists():
            px = QPixmap(str(logo_path))
            if not px.isNull():
                self._logo_pixmap_original = px
                self._logo_lbl.setPixmap(px.scaledToHeight(40, Qt.SmoothTransformation))
            else:
                self._logo_lbl.setObjectName("logoFallback")
                self._logo_lbl.setText("Rodogarcia")
        else:
            self._logo_lbl.setObjectName("logoFallback")
            self._logo_lbl.setText("Rodogarcia")
        marca_layout.addWidget(self._logo_lbl)

        self._header_divisor = QFrame()
        self._header_divisor.setFixedWidth(1)
        self._header_divisor.setStyleSheet(f"background: {p['borda_forte']}; border: none;")
        marca_layout.addWidget(self._header_divisor)

        bloco_titulo = QVBoxLayout()
        bloco_titulo.setSpacing(4)

        kicker = QLabel(UIConstants.TEXT_HEADER_KICKER)
        kicker.setObjectName("etiquetaTopo")

        titulo = QLabel(UIConstants.TEXT_TITLE)
        titulo.setStyleSheet("font-size: 20px; font-weight: 800;")

        subtitulo = QLabel(UIConstants.TEXT_SUBTITLE)
        subtitulo.setObjectName("labelMutado")
        subtitulo.setStyleSheet("font-size: 12px;")
        subtitulo.setWordWrap(True)

        bloco_titulo.addWidget(kicker)
        bloco_titulo.addWidget(titulo)
        bloco_titulo.addWidget(subtitulo)
        marca_layout.addLayout(bloco_titulo)
        marca_layout.addStretch(1)
        layout.addWidget(marca, 1)

        # Painel de status
        painel_status = QFrame()
        painel_status.setObjectName("cabecalhoStatus")
        painel_status.setMinimumWidth(200)

        layout_status = QVBoxLayout(painel_status)
        layout_status.setContentsMargins(16, 12, 16, 12)
        layout_status.setSpacing(4)

        lbl_st = QLabel(UIConstants.TEXT_HEADER_STATUS_TITLE)
        lbl_st.setObjectName("labelMutado")
        lbl_st.setStyleSheet("font-size: 11px; font-weight: 600;")

        # Badge de status em QFrame para suportar border-radius
        self.header_status_badge_frame = QFrame()
        self.header_status_badge_frame.setObjectName("etiquetaStatusRobo")
        self.header_status_badge_frame.setMinimumWidth(100)
        self.header_status_badge_frame.setFixedHeight(30)
        frame_layout = QHBoxLayout(self.header_status_badge_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)

        self.header_status_badge = QLabel("Parado")
        self.header_status_badge.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(self.header_status_badge)

        self._aplicar_estilo_badge(self.header_status_badge_frame, "Parado")

        self.header_status_detail = QLabel(UIConstants.TEXT_HEADER_STATUS_DETAIL)
        self.header_status_detail.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.header_status_detail.setWordWrap(True)

        self.header_status_time = QLabel("")
        self.header_status_time.setObjectName("labelMutado")
        self.header_status_time.setStyleSheet("font-size: 10px;")

        layout_status.addWidget(lbl_st)
        layout_status.addWidget(self.header_status_badge_frame)
        layout_status.addWidget(self.header_status_detail)
        layout_status.addWidget(self.header_status_time)
        layout.addWidget(painel_status)

        # Botão de alternância de tema
        self.btn_tema = QPushButton("☀")
        self.btn_tema.setObjectName("botaoTema")
        self.btn_tema.setFixedSize(36, 36)
        self.btn_tema.setCursor(Qt.PointingHandCursor)
        self.btn_tema.setToolTip("Alternar tema claro/escuro")
        self.btn_tema.clicked.connect(self._alternar_tema)
        layout.addWidget(self.btn_tema, alignment=Qt.AlignVCenter)

        return card

    def _aplicar_estilo_badge(self, widget, texto: str) -> None:
        """Aplica estilo de badge a um QFrame ou QLabel"""
        cf, ct, cb = MAPA_CORES_STATUS.get(texto, ("#F8FAFC", "#0F172A", "#D9E4F0"))
        name = widget.objectName() or "widget"

        # Se é QFrame, estiliza o frame e o label dentro
        if isinstance(widget, QFrame):
            sel_frame = f"QFrame#{name}"
            qss = f"{sel_frame} {{ background-color: {cf}; border: 1px solid {cb}; border-radius: 15px; }}"
            widget.setStyleSheet(qss)
            # Estiliza o label dentro do frame
            if widget.layout() and widget.layout().count() > 0:
                lbl = widget.layout().itemAt(0).widget()
                if isinstance(lbl, QLabel):
                    lbl.setStyleSheet(f"QLabel {{ color: {ct}; background: transparent; font-size: 12px; font-weight: 700; }}")
                    lbl.setText(texto)
        # Se é QLabel, estiliza como antes
        elif isinstance(widget, QLabel):
            sel = f"QLabel#{name}" if name != "widget" else "QLabel"
            qss = f"{sel} {{ background-color: {cf}; color: {ct}; border: 1px solid {cb}; border-radius: 15px; padding: 6px 14px; font-size: 12px; font-weight: 700; }}"
            widget.setStyleSheet(qss)
            widget.setText(texto)

    # ------------------------------------------------------------------
    # Seção de controles
    # ------------------------------------------------------------------
    def _criar_secao_controles(self) -> QFrame:
        p = self._paleta_atual
        card = QFrame()
        card.setObjectName("cartaoPadrao")
        _sombra(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)

        titulo = QLabel("Controles de execucao")
        titulo.setStyleSheet("font-size: 18px; font-weight: 700;")
        desc = QLabel("Selecione o PDF, defina a filial e o periodo antes de iniciar a conversao.")
        desc.setObjectName("labelMutado")
        desc.setStyleSheet("font-size: 13px;")
        layout.addWidget(titulo)
        layout.addWidget(desc)

        grade = QGridLayout()
        grade.setSpacing(16)
        grade.setColumnStretch(0, 1)
        grade.setColumnStretch(1, 1)
        grade.setColumnStretch(2, 1)

        # Painel 1 — PDF
        painel_pdf, content_pdf = self._criar_painel_campo(
            "1. Arquivo de origem",
            "Selecione o arquivo de frete que sera convertido.",
        )
        pdf_layout = QVBoxLayout(content_pdf)
        pdf_layout.setContentsMargins(0, 0, 0, 0)
        pdf_layout.setSpacing(8)

        row_pdf = QHBoxLayout()
        row_pdf.setSpacing(8)
        self.entry_pdf = QLineEdit()
        self.entry_pdf.setPlaceholderText(UIConstants.PLACEHOLDER_PDF)
        self.entry_pdf.setReadOnly(True)
        row_pdf.addWidget(self.entry_pdf, 1)

        self.btn_buscar = QPushButton(UIConstants.TEXT_BUTTON_BUSCAR_PDF)
        self.btn_buscar.setObjectName("botaoSecundario")
        self.btn_buscar.setFixedHeight(38)
        self.btn_buscar.setCursor(Qt.PointingHandCursor)
        self.btn_buscar.clicked.connect(self._choose_pdf)
        row_pdf.addWidget(self.btn_buscar)

        dica_pdf = QLabel(UIConstants.TEXT_ACTION_HINT)
        dica_pdf.setObjectName("labelSutil")
        dica_pdf.setStyleSheet("font-size: 11px;")
        dica_pdf.setWordWrap(True)

        pdf_layout.addLayout(row_pdf)
        pdf_layout.addWidget(dica_pdf)
        grade.addWidget(painel_pdf, 0, 0)

        # Painel 2 — CNPJ / Filial
        painel_cnpj, content_cnpj = self._criar_painel_campo(
            "2. Filial e CNPJ do mapa",
            "Busque a filial pelo CNPJ ou selecione na lista cadastrada.",
        )
        cnpj_layout = QVBoxLayout(content_cnpj)
        cnpj_layout.setContentsMargins(0, 0, 0, 0)
        cnpj_layout.setSpacing(8)

        lbl_cnpj = QLabel("CNPJ da filial")
        lbl_cnpj.setObjectName("labelMutado")
        lbl_cnpj.setStyleSheet("font-size: 11px; font-weight: 700;")

        row_cnpj = QHBoxLayout()
        row_cnpj.setSpacing(8)
        self.entry_cnpj = QLineEdit()
        self.entry_cnpj.setPlaceholderText(UIConstants.PLACEHOLDER_CNPJ)
        self.entry_cnpj.textChanged.connect(self._on_cnpj_changed)
        row_cnpj.addWidget(self.entry_cnpj, 1)

        self.btn_buscar_filial = QPushButton(UIConstants.TEXT_BUTTON_BUSCAR_FILIAL)
        self.btn_buscar_filial.setObjectName("botaoSecundario")
        self.btn_buscar_filial.setFixedHeight(38)
        self.btn_buscar_filial.setMinimumWidth(80)
        self.btn_buscar_filial.setCursor(Qt.PointingHandCursor)
        self.btn_buscar_filial.clicked.connect(self._buscar_filial_por_cnpj)
        row_cnpj.addWidget(self.btn_buscar_filial)

        lbl_combo = QLabel("Filial cadastrada")
        lbl_combo.setObjectName("labelMutado")
        lbl_combo.setStyleSheet("font-size: 11px; font-weight: 700;")

        self.combo_filial = QComboBox()
        self.combo_filial.setEditable(False)
        try:
            opcoes = self._filiais_manager.obter_opcoes_combo()
            self.combo_filial.addItem(UIConstants.PLACEHOLDER_COMBO_FILIAL)
            for op in opcoes:
                self.combo_filial.addItem(op)
        except Exception:
            self.combo_filial.addItem(UIConstants.PLACEHOLDER_COMBO_FILIAL)
        self.combo_filial.currentTextChanged.connect(self._on_filial_selecionada)

        self.lbl_filial_info = QLabel("")
        self.lbl_filial_info.setStyleSheet(f"color: {p['sucesso']}; font-size: 12px; font-weight: 600;")
        self.lbl_filial_info.setWordWrap(True)

        cnpj_layout.addWidget(lbl_cnpj)
        cnpj_layout.addLayout(row_cnpj)
        cnpj_layout.addWidget(lbl_combo)
        cnpj_layout.addWidget(self.combo_filial)
        cnpj_layout.addWidget(self.lbl_filial_info)
        grade.addWidget(painel_cnpj, 0, 1)

        # Painel 3 — Período
        painel_periodo, content_periodo = self._criar_painel_campo(
            "3. Periodo de referencia",
            "Defina o periodo que sera importado no SIPROQUIM.",
        )
        periodo_layout = QVBoxLayout(content_periodo)
        periodo_layout.setContentsMargins(0, 0, 0, 0)
        periodo_layout.setSpacing(8)

        lbl_mes = QLabel("Mes de referencia")
        lbl_mes.setObjectName("labelMutado")
        lbl_mes.setStyleSheet("font-size: 11px; font-weight: 700;")

        self.combo_mes = QComboBox()
        for m in UIConstants.MESES_ABREVIADOS:
            self.combo_mes.addItem(m)
        idx = self.combo_mes.findText(extrair_mes_padrao())
        if idx >= 0:
            self.combo_mes.setCurrentIndex(idx)
        self.combo_mes.currentTextChanged.connect(self._on_campo_changed)

        lbl_ano = QLabel("Ano de referencia")
        lbl_ano.setObjectName("labelMutado")
        lbl_ano.setStyleSheet("font-size: 11px; font-weight: 700;")

        self.entry_ano = QLineEdit()
        self.entry_ano.setPlaceholderText(UIConstants.PLACEHOLDER_ANO)
        self.entry_ano.setText(str(extrair_ano_padrao()))
        self.entry_ano.textChanged.connect(self._on_campo_changed)

        dica_periodo = QLabel(UIConstants.TEXT_DICA_MES_ANO)
        dica_periodo.setObjectName("labelSutil")
        dica_periodo.setStyleSheet("font-size: 11px;")
        dica_periodo.setWordWrap(True)

        periodo_layout.addWidget(lbl_mes)
        periodo_layout.addWidget(self.combo_mes)
        periodo_layout.addWidget(lbl_ano)
        periodo_layout.addWidget(self.entry_ano)
        periodo_layout.addWidget(dica_periodo)
        grade.addWidget(painel_periodo, 0, 2)

        layout.addLayout(grade)

        # Botões de ação
        row_acoes = QHBoxLayout()
        row_acoes.setSpacing(14)

        self.btn_converter = BotaoPrimarioQt(UIConstants.TEXT_BUTTON_CONVERTER)
        p_btn = self._paleta_atual
        self.btn_converter.definir_paleta(
            p_btn["btn_pri_bg"],
            p_btn["btn_pri_hover"],
            p_btn["btn_pri_text"],
        )
        self.btn_converter.setFixedHeight(UIConstants.HEIGHT_BUTTON_LARGE)
        self.btn_converter.setCursor(Qt.PointingHandCursor)
        self.btn_converter.clicked.connect(self._on_gerar)
        self.btn_converter.setEnabled(False)
        _sombra(self.btn_converter, blur=16, y=4)

        self.btn_cancelar = QPushButton("Cancelar processamento")
        self.btn_cancelar.setObjectName("botaoPerigo")
        self.btn_cancelar.setFixedHeight(UIConstants.HEIGHT_BUTTON_LARGE)
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self._cancelar_processamento)
        self.btn_cancelar.setVisible(False)

        row_acoes.addWidget(self.btn_converter)
        row_acoes.addWidget(self.btn_cancelar)
        row_acoes.addStretch(1)
        layout.addLayout(row_acoes)

        return card

    def _criar_painel_campo(self, titulo: str, descricao: str) -> tuple[QFrame, QWidget]:
        card = QFrame()
        card.setObjectName("painelCampo")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 16)
        card_layout.setSpacing(4)

        lbl_t = QLabel(titulo)
        lbl_t.setStyleSheet("font-size: 12px; font-weight: 700; background: transparent; border: none;")
        lbl_d = QLabel(descricao)
        lbl_d.setObjectName("labelMutado")
        lbl_d.setStyleSheet("font-size: 11px; background: transparent; border: none;")
        lbl_d.setWordWrap(True)

        content = QWidget()
        card_layout.addWidget(lbl_t)
        card_layout.addWidget(lbl_d)
        card_layout.addSpacing(6)
        card_layout.addWidget(content)
        return card, content

    # ------------------------------------------------------------------
    # Seção de aprendizado
    # ------------------------------------------------------------------
    def _criar_secao_aprendizado(self) -> QFrame:
        p = self._paleta_atual
        card = QFrame()
        card.setObjectName("cartaoAprendizado")
        _sombra(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        titulo = QLabel(UIConstants.TEXT_STEP_4)
        titulo.setStyleSheet("font-size: 18px; font-weight: 700;")
        dica = QLabel(UIConstants.TEXT_DICA_APRENDIZADO)
        dica.setObjectName("labelMutado")
        dica.setStyleSheet("font-size: 13px;")
        dica.setWordWrap(True)
        layout.addWidget(titulo)
        layout.addWidget(dica)

        row = QHBoxLayout()
        row.setSpacing(12)

        self.btn_aprender_txt = QPushButton(UIConstants.TEXT_BUTTON_APRENDER_TXT)
        self.btn_aprender_txt.setObjectName("botaoSecundario")
        self.btn_aprender_txt.setFixedHeight(UIConstants.HEIGHT_BUTTON_SMALL)
        self.btn_aprender_txt.setCursor(Qt.PointingHandCursor)
        self.btn_aprender_txt.clicked.connect(self._on_aprender_txt)
        if not self._aprendizado_store:
            self.btn_aprender_txt.setEnabled(False)

        self.btn_abrir_memoria = QPushButton(UIConstants.TEXT_BUTTON_ABRIR_MEMORIA)
        self.btn_abrir_memoria.setObjectName("botaoSecundario")
        self.btn_abrir_memoria.setFixedHeight(UIConstants.HEIGHT_BUTTON_SMALL)
        self.btn_abrir_memoria.setCursor(Qt.PointingHandCursor)
        self.btn_abrir_memoria.clicked.connect(self._abrir_pasta_memoria)
        if not self._aprendizado_store:
            self.btn_abrir_memoria.setEnabled(False)

        row.addWidget(self.btn_aprender_txt)
        row.addWidget(self.btn_abrir_memoria)
        row.addStretch(1)
        layout.addLayout(row)

        frame_mem = QFrame()
        frame_mem.setObjectName("frameMemoria")
        mem_lay = QVBoxLayout(frame_mem)
        mem_lay.setContentsMargins(14, 10, 14, 10)

        try:
            resumo = self._aprendizado_store.resumo_memoria()
            caminho = resumo.get("arquivo_db", "")
        except Exception:
            caminho = ""

        self.lbl_memoria_path = QLabel(self._formatar_texto_memoria(caminho))
        self.lbl_memoria_path.setObjectName("labelSutil")
        self.lbl_memoria_path.setStyleSheet("font-size: 11px; background: transparent; border: none;")
        self.lbl_memoria_path.setWordWrap(True)
        mem_lay.addWidget(self.lbl_memoria_path)
        layout.addWidget(frame_mem)
        return card

    # ------------------------------------------------------------------
    # Grade de estatísticas (métricas reais do pipeline)
    # ------------------------------------------------------------------
    def _criar_grade_estatisticas(self) -> QGridLayout:
        p = self._paleta_atual
        grade = QGridLayout()
        grade.setSpacing(18)

        dados = [
            (UIConstants.TEXT_METRIC_REGISTROS, p["primaria"],    "Leitura bruta do PDF"),
            (UIConstants.TEXT_METRIC_NFS,        p["secundaria"], "Apos deduplicacao"),
            (UIConstants.TEXT_METRIC_AJUSTES,    p["aviso"],      "Exigem revisao manual"),
            (UIConstants.TEXT_METRIC_CRITICOS,   p["perigo"],     "Pendencias criticas"),
        ]

        self._metric_labels: list[tuple[QLabel, QLabel]] = []

        for i, (titulo, cor, detalhe) in enumerate(dados):
            card = QFrame()
            card.setObjectName("cartaoEstatistica")
            card.setMinimumHeight(138)
            _sombra(card)

            v = QVBoxLayout(card)
            v.setContentsMargins(18, 18, 18, 18)
            v.setSpacing(12)

            topo = QHBoxLayout()
            topo.setSpacing(10)

            marcador = QFrame()
            marcador.setFixedSize(10, 10)
            marcador.setStyleSheet(f"background: {cor}; border: none; border-radius: 5px;")
            topo.addWidget(marcador)

            lbl_t = QLabel(titulo)
            lbl_t.setObjectName("labelMutado")
            lbl_t.setStyleSheet("font-size: 12px; font-weight: 700; letter-spacing: 0.4px;")
            topo.addWidget(lbl_t)
            topo.addStretch(1)
            v.addLayout(topo)

            lbl_val = QLabel("0")
            lbl_val.setStyleSheet("font-size: 30px; font-weight: 800;")
            v.addWidget(lbl_val)

            lbl_det = QLabel(detalhe)
            lbl_det.setObjectName("labelSutil")
            lbl_det.setStyleSheet("font-size: 12px;")
            v.addWidget(lbl_det)

            grade.addWidget(card, 0, i)
            self._metric_labels.append((lbl_val, lbl_det))

        return grade

    # ------------------------------------------------------------------
    # Seção de progresso
    # ------------------------------------------------------------------
    def _criar_secao_progresso(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cartaoPadrao")
        _sombra(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(6)

        # Linha 1: título + % à direita
        linha1 = QHBoxLayout()
        lbl_t = QLabel(UIConstants.TEXT_PROGRESS_TITLE)
        lbl_t.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.lbl_progress_context = QLabel(UIConstants.TEXT_PROGRESS_CONTEXT)
        self.lbl_progress_context.setObjectName("labelMutado")
        self.lbl_progress_context.setStyleSheet("font-size: 12px;")
        bloco = QVBoxLayout()
        bloco.setSpacing(2)
        bloco.addWidget(lbl_t)
        bloco.addWidget(self.lbl_progress_context)
        linha1.addLayout(bloco, 1)
        self.lbl_progress_percent = QLabel("0%")
        self.lbl_progress_percent.setObjectName("rotuloPercentual")
        self.lbl_progress_percent.setStyleSheet("font-size: 20px; font-weight: 800;")
        self.lbl_progress_percent.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        linha1.addWidget(self.lbl_progress_percent)
        layout.addLayout(linha1)

        # Linha 2: barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("barraProgresso")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Linha 3: status + tempo na mesma linha
        linha3 = QHBoxLayout()
        self.lbl_status = QLabel(UIConstants.TEXT_STATUS_DEFAULT)
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: 600;")
        self.lbl_status.setWordWrap(False)
        self.lbl_tempo = QLabel("")
        self.lbl_tempo.setObjectName("labelMutado")
        self.lbl_tempo.setStyleSheet("font-size: 11px;")
        self.lbl_tempo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        linha3.addWidget(self.lbl_status, 1)
        linha3.addWidget(self.lbl_tempo)
        layout.addLayout(linha3)

        return card

    # ------------------------------------------------------------------
    # Seção de logs
    # ------------------------------------------------------------------
    def _criar_secao_logs(self) -> QFrame:
        card = QFrame()
        card.setObjectName("containerHistorico")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card.setMinimumHeight(520)
        _sombra(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        # ── Cabeçalho do card
        cab = QHBoxLayout()
        bloco = QVBoxLayout()
        bloco.setSpacing(6)
        lbl_t = QLabel(UIConstants.TEXT_LOGS_TITLE)
        lbl_t.setStyleSheet("font-size: 18px; font-weight: 700;")
        lbl_s = QLabel(UIConstants.TEXT_LOGS_SUBTITLE)
        lbl_s.setObjectName("labelMutado")
        lbl_s.setStyleSheet("font-size: 13px;")
        bloco.addWidget(lbl_t)
        bloco.addWidget(lbl_s)
        cab.addLayout(bloco, 1)

        # Controles: A−, A+, Tela cheia, Exportar
        self.btn_zoom_menos = QPushButton("A−")
        self.btn_zoom_menos.setObjectName("botaoControle")
        self.btn_zoom_menos.setFixedHeight(32)
        self.btn_zoom_menos.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_menos.clicked.connect(self._zoom_logs_menos)

        self.btn_zoom_mais = QPushButton("A+")
        self.btn_zoom_mais.setObjectName("botaoControle")
        self.btn_zoom_mais.setFixedHeight(32)
        self.btn_zoom_mais.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_mais.clicked.connect(self._zoom_logs_mais)

        self.btn_tela_cheia = QPushButton(UIConstants.TEXT_BUTTON_LOGS_FULLSCREEN)
        self.btn_tela_cheia.setObjectName("botaoControle")
        self.btn_tela_cheia.setFixedHeight(32)
        self.btn_tela_cheia.setCursor(Qt.PointingHandCursor)
        self.btn_tela_cheia.clicked.connect(self._toggle_tela_cheia)

        self.btn_exportar_logs = QPushButton(UIConstants.TEXT_BUTTON_EXPORTAR_LOG)
        self.btn_exportar_logs.setObjectName("botaoControle")
        self.btn_exportar_logs.setFixedHeight(32)
        self.btn_exportar_logs.setCursor(Qt.PointingHandCursor)
        self.btn_exportar_logs.clicked.connect(self._exportar_logs)

        cab.addWidget(self.btn_zoom_menos)
        cab.addWidget(self.btn_zoom_mais)
        cab.addWidget(self.btn_tela_cheia)
        cab.addWidget(self.btn_exportar_logs)
        layout.addLayout(cab)

        # ── QTextEdit de logs
        self.txt_logs = QTextEdit()
        self.txt_logs.setObjectName("texteLogs")
        self.txt_logs.setReadOnly(True)
        self.txt_logs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.txt_logs, 1)

        self._layout_logs_card = layout
        return card

    # ------------------------------------------------------------------
    # Controles do painel de logs
    # ------------------------------------------------------------------
    def _zoom_logs_menos(self) -> None:
        if self._historico_mgr:
            self._historico_mgr.ajustar_fonte(-UIConstants.LOG_FONT_SIZE_STEP)

    def _zoom_logs_mais(self) -> None:
        if self._historico_mgr:
            self._historico_mgr.ajustar_fonte(UIConstants.LOG_FONT_SIZE_STEP)

    def _toggle_tela_cheia(self) -> None:
        if self._dialog_logs is not None:
            self._fechar_logs_fullscreen()
        else:
            self._abrir_logs_fullscreen()

    def _abrir_logs_fullscreen(self) -> None:
        from PySide6.QtWidgets import QDialog
        dlg = QDialog(self, Qt.Window)
        dlg.setWindowTitle("Histórico de Execução")
        dlg.setWindowFlags(
            Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
        )
        dlg.setStyleSheet(self.styleSheet())

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        btn_voltar = QPushButton("← Voltar")
        btn_voltar.setObjectName("botaoControle")
        btn_voltar.setFixedHeight(32)
        btn_voltar.setCursor(Qt.PointingHandCursor)
        btn_voltar.clicked.connect(self._fechar_logs_fullscreen)
        outer.addWidget(btn_voltar, alignment=Qt.AlignLeft)

        # Move o txt_logs para o diálogo (reparenting nativo Qt)
        outer.addWidget(self.txt_logs, 1)

        dlg.finished.connect(lambda _: self._fechar_logs_fullscreen())
        self._dialog_logs = dlg
        self.btn_tela_cheia.setText("Restaurar")
        dlg.showMaximized()

    def _fechar_logs_fullscreen(self) -> None:
        if self._dialog_logs is None:
            return
        dlg = self._dialog_logs
        self._dialog_logs = None
        # Devolve o txt_logs ao layout original antes de fechar o diálogo
        if self._layout_logs_card is not None:
            self._layout_logs_card.addWidget(self.txt_logs, 1)
        dlg.hide()
        dlg.deleteLater()
        self.btn_tela_cheia.setText(UIConstants.TEXT_BUTTON_LOGS_FULLSCREEN)

    # ------------------------------------------------------------------
    # Inicialização dos logs
    # ------------------------------------------------------------------
    def _inicializar_logs(self) -> None:
        if not self._historico_mgr:
            return
        try:
            self._historico_mgr.adicionar_banner("SISTEMA INICIALIZADO", "INFO")
            self._historico_mgr.adicionar_sucesso("Sistema inicializado com sucesso!")
            self._historico_mgr.adicionar_info("Versao: SIPROQUIM Converter by valentelucass")
            try:
                total = len(self._filiais_manager.obter_opcoes_combo())
                self._historico_mgr.adicionar_info(f"Total de filiais cadastradas: {total}")
            except Exception:
                self._historico_mgr.adicionar_aviso("Nao foi possivel contar filiais.")
            if self._aprendizado_store:
                r = self._aprendizado_store.resumo_memoria()
                self._historico_mgr.adicionar_info(f"Memoria ativa: {r.get('arquivo_db', '')}")
                self._historico_mgr.adicionar_info(
                    f"Memoria carregada: {r.get('total_pares', 0)} par(es) "
                    f"(ativos={r.get('pares_ativos', 0)}, quarentena={r.get('pares_quarentena', 0)})"
                )
            self._historico_mgr.adicionar_info("Aguardando acao do usuario...")
        except Exception as e:
            self._historico_mgr.adicionar_erro(f"Erro na inicializacao: {e}")

    # ------------------------------------------------------------------
    # Atualização da UI
    # ------------------------------------------------------------------
    def _atualizar_metricas(self) -> None:
        total = self._total_registros_extraidos or 0
        nfs = self._total_nfs_dedup or self._ultima_estatistica.get("total_aprovados", 0) or 0
        ajustes = self._ultima_estatistica.get("total_ajustes_manuais", 0) or 0
        corrigidos = self._ultima_estatistica.get("total_corrigidos", 0) or 0
        criticos = self._ultima_estatistica.get("total_com_erros_criticos", 0) or 0
        for (lv, ld), (val, det) in zip(self._metric_labels, [
            (str(total), "Leitura bruta do PDF"),
            (str(nfs), "Apos deduplicacao de notas"),
            (str(ajustes), f"Correcoes automaticas: {corrigidos}"),
            (str(criticos), "Pendencias que exigem revisao"),
        ]):
            lv.setText(val)
            ld.setText(det)

    def _atualizar_progresso(self, progresso: float, contexto: Optional[str] = None) -> None:
        p = max(0.0, min(1.0, float(progresso)))
        self.progress_bar.setValue(int(p * 100))
        self.lbl_progress_percent.setText(f"{int(p * 100):02d}%")
        if contexto is not None:
            self.lbl_progress_context.setText(contexto)

    def _atualizar_status_badge(self, texto_status: str) -> None:
        texto = (texto_status or "").strip()
        u = texto.upper()
        badge = "Parado"
        if any(k in u for k in ["INTERROMPIDO"]):
            badge = "Interrompido"
        elif any(k in u for k in ["ERRO", "FALHA", "CRITIC", "PENDENCIAS CRITICAS"]):
            badge = "Erro"
        elif any(k in u for k in ["SUCESSO", "CONCLUID", "FINALIZADO"]):
            badge = "Sucesso"
        elif any(k in u for k in ["ATENCAO", "ATENÇÃO", "AJUSTE", "PENDENCIA", "REVISAO"]):
            badge = "Atenção"
        elif any(k in u for k in ["ABRINDO", "EXTRAINDO", "GERANDO", "PROCESSANDO", "VALIDANDO", "DEDUPLICANDO", "APRENDENDO"]):
            badge = "Executando"
        self._aplicar_estilo_badge(self.header_status_badge_frame, badge)
        self.header_status_detail.setText(texto or UIConstants.TEXT_HEADER_STATUS_DETAIL)
        self.header_status_time.setText(f"Atualizado em {datetime.now().strftime('%H:%M:%S')}")

    def _set_status(self, texto: str) -> None:
        self.lbl_status.setText(texto)
        self._atualizar_status_badge(texto)

    # ------------------------------------------------------------------
    # Validação do formulário
    # ------------------------------------------------------------------
    def _verificar_habilitar_botao(self) -> None:
        pdf = self.entry_pdf.text().strip()
        cnpj = somente_digitos(self.entry_cnpj.text())
        mes = self.combo_mes.currentText()
        ano = somente_digitos(self.entry_ano.text())
        pdf_ok, _ = FormValidator.validar_pdf(pdf)
        cnpj_ok, _ = FormValidator.validar_cnpj(cnpj)
        mes_ok, _, _ = FormValidator.validar_mes(mes)
        ano_ok, _, _ = FormValidator.validar_ano(ano)
        self.btn_converter.setEnabled(pdf_ok and cnpj_ok and mes_ok and ano_ok)

    def _on_campo_changed(self, *_) -> None:
        self._verificar_habilitar_botao()

    # ------------------------------------------------------------------
    # Callbacks de formulário
    # ------------------------------------------------------------------
    def _on_cnpj_changed(self, texto: str) -> None:
        cnpj = somente_digitos(texto)
        if len(cnpj) > CNPJ_TAMANHO:
            self.entry_cnpj.blockSignals(True)
            self.entry_cnpj.setText(cnpj[:CNPJ_TAMANHO])
            self.entry_cnpj.blockSignals(False)
            cnpj = cnpj[:CNPJ_TAMANHO]
        if len(cnpj) == CNPJ_TAMANHO:
            try:
                nome = self._filiais_manager.buscar_por_cnpj(cnpj)
                self.lbl_filial_info.setText(
                    UIConstants.TEXT_INFO_CNPJ_ENCONTRADO.format(nome=nome, cnpj=cnpj) if nome
                    else UIConstants.TEXT_AVISO_CNPJ_NAO_ENCONTRADO.format(cnpj=cnpj)
                )
            except Exception:
                pass
        self._verificar_habilitar_botao()

    def _buscar_filial_por_cnpj(self) -> None:
        cnpj = somente_digitos(self.entry_cnpj.text())
        valido, erro = FormValidator.validar_cnpj(cnpj)
        if not valido:
            if self._historico_mgr:
                self._historico_mgr.adicionar_aviso(f"CNPJ invalido: {erro}")
            self._mostrar_aviso(
                UIConstants.DIALOG_TITLE_AVISO,
                UIConstants.TEXT_AVISO_CNPJ_DIGITOS.format(digitos=CNPJ_TAMANHO),
            )
            return
        try:
            nome = self._filiais_manager.buscar_por_cnpj(cnpj)
            if nome:
                if self._historico_mgr:
                    self._historico_mgr.adicionar_sucesso(f"Filial encontrada: {nome}")
                self.lbl_filial_info.setText(UIConstants.TEXT_INFO_CNPJ_ENCONTRADO.format(nome=nome, cnpj=cnpj))
                for i in range(self.combo_filial.count()):
                    if cnpj in self.combo_filial.itemText(i):
                        self.combo_filial.setCurrentIndex(i)
                        break
            else:
                if self._historico_mgr:
                    self._historico_mgr.adicionar_aviso(f"CNPJ nao encontrado: {cnpj}")
                self.lbl_filial_info.setText(UIConstants.TEXT_AVISO_CNPJ_NAO_ENCONTRADO.format(cnpj=cnpj))
            self._verificar_habilitar_botao()
        except Exception as e:
            self._mostrar_erro_popup("Erro", f"Erro ao buscar filial: {e}")

    def _on_filial_selecionada(self, choice: str) -> None:
        if choice and choice != UIConstants.PLACEHOLDER_COMBO_FILIAL:
            partes = choice.split(" - ")
            if len(partes) >= 2:
                cnpj = partes[-1]
                nome = " - ".join(partes[:-1])
                self.entry_cnpj.blockSignals(True)
                self.entry_cnpj.setText(cnpj)
                self.entry_cnpj.blockSignals(False)
                self.lbl_filial_info.setText(
                    UIConstants.TEXT_INFO_CNPJ_ENCONTRADO.format(nome=nome, cnpj=cnpj)
                )
            self._verificar_habilitar_botao()
        elif choice == UIConstants.PLACEHOLDER_COMBO_FILIAL:
            self.entry_cnpj.clear()
            self.lbl_filial_info.clear()
            self._verificar_habilitar_botao()

    def _choose_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, UIConstants.DIALOG_TITLE_PDF, "",
            "Arquivos PDF (*.pdf);;Todos os arquivos (*.*)",
        )
        if path:
            self.entry_pdf.setText(path)
            self._set_status(f"Arquivo selecionado: {Path(path).name}")
            self._verificar_habilitar_botao()

    # ------------------------------------------------------------------
    # Aprendizado de TXT
    # ------------------------------------------------------------------
    def _on_aprender_txt(self) -> None:
        if not self._aprendizado_store:
            self._mostrar_erro_popup(UIConstants.DIALOG_TITLE_ERRO, "Memoria de aprendizado indisponivel.")
            return
        if self._is_busy:
            if self._historico_mgr:
                self._historico_mgr.adicionar_aviso("Aguarde a operacao atual terminar.")
            return
        caminho_txt, _ = QFileDialog.getOpenFileName(
            self, UIConstants.DIALOG_TITLE_TXT, "",
            "Arquivos TXT (*.txt);;Todos os arquivos (*.*)",
        )
        if not caminho_txt:
            return
        self._set_aprendizado_busy(True)
        self._set_status("Aprendendo com TXT corrigido...")
        if self._historico_mgr:
            self._historico_mgr.definir_etapa("Aprendizado")
            self._historico_mgr.adicionar_banner("APRENDIZADO", "STATUS")
            self._historico_mgr.adicionar_info(f"Arquivo: {Path(caminho_txt).name}", origem="Memória")
        self._thread_aprendizado = threading.Thread(
            target=self._run_aprendizado_txt, args=(caminho_txt,), daemon=True
        )
        self._thread_aprendizado.start()

    def _run_aprendizado_txt(self, caminho_txt: str) -> None:
        try:
            resultado = self._aprendizado_store.aprender_com_txt(caminho_txt)
            self._depois(lambda r=resultado: self._log_resumo_aprendizado(r))
            replay = bool(resultado.get("replay_detectado", False))
            msg_status = ("Aprendizado ignorado: arquivo ja processado." if replay else
                          f"Aprendizado concluido: +{resultado.get('aprendidos_novos', 0)} novos.")
            self._depois(lambda m=msg_status: self._set_status(m))

            def _dialogo(r=resultado, rep=replay):
                if rep:
                    self._mostrar_info(
                        UIConstants.DIALOG_TITLE_SUCESSO,
                        f"Aprendizado ignorado: arquivo ja processado.\nMemoria: {r.get('arquivo_db', '')}",
                    )
                else:
                    self._mostrar_info(
                        UIConstants.DIALOG_TITLE_SUCESSO,
                        f"Aprendizado concluido!\n"
                        f"Novos pares: {r.get('aprendidos_novos', 0)}\n"
                        f"Promovidos: {r.get('promovidos', 0)}\n"
                        f"Memoria: {r.get('arquivo_db', '')}",
                    )
            self._depois(_dialogo)
        except Exception as exc:
            m = f"Falha ao aprender com TXT: {exc}"
            self._depois(lambda msg=m: self._historico_mgr and self._historico_mgr.adicionar_erro(msg, origem="Memória"))
            self._depois(lambda: self._set_status("Falha no aprendizado."))
            self._depois(lambda msg=m: self._mostrar_erro_popup(UIConstants.DIALOG_TITLE_ERRO, msg))
        finally:
            self._depois(lambda: self._set_aprendizado_busy(False))

    def _log_resumo_aprendizado(self, resultado: dict) -> None:
        if not self._historico_mgr:
            return
        replay = bool(resultado.get("replay_detectado", False))
        status_aprendizado = "Atenção" if replay else "Sucesso"
        resumo = (
            f"Replay detectado — arquivo ja processado." if replay else
            f"Novos={resultado.get('aprendidos_novos', 0)} | "
            f"Promovidos={resultado.get('promovidos', 0)} | "
            f"Quarentena={resultado.get('quarentena_sessao', 0)}"
        )
        tipo_aprendizado = "AVISO" if replay else "SUCESSO"
        self._historico_mgr.adicionar(resumo, tipo_aprendizado, origem="Memória")
        self._historico_mgr.adicionar_info(
            f"Memoria salva em: {resultado.get('arquivo_db', '')}", origem="Memória"
        )
        try:
            r = self._aprendizado_store.resumo_memoria()
            self.lbl_memoria_path.setText(self._formatar_texto_memoria(r.get("arquivo_db", "")))
        except Exception:
            pass

    def _abrir_pasta_memoria(self) -> None:
        try:
            if not self._aprendizado_store:
                raise RuntimeError("Memoria indisponivel.")
            pasta = self._aprendizado_store.memory_folder
            pasta.mkdir(parents=True, exist_ok=True)
            if self._historico_mgr:
                self._historico_mgr.adicionar_info(f"Abrindo pasta de memoria: {pasta}", origem="Memória")
            try:
                os.startfile(str(pasta))
            except Exception:
                subprocess.run(["explorer", str(pasta)])
        except Exception as exc:
            self._mostrar_erro_popup(UIConstants.DIALOG_TITLE_ERRO, f"Falha ao abrir pasta: {exc}")

    def _set_aprendizado_busy(self, busy: bool) -> None:
        self._is_busy = busy
        h = not busy
        self.btn_aprender_txt.setEnabled(h and bool(self._aprendizado_store))
        self.btn_aprender_txt.setText(
            UIConstants.TEXT_BUTTON_APRENDENDO_TXT if busy else UIConstants.TEXT_BUTTON_APRENDER_TXT
        )
        self.btn_abrir_memoria.setEnabled(h and bool(self._aprendizado_store))
        self.btn_converter.setEnabled(False if busy else True)
        self.btn_buscar.setEnabled(h)
        self.entry_cnpj.setEnabled(h)
        if not busy:
            self._verificar_habilitar_botao()

    @staticmethod
    def _formatar_texto_memoria(caminho: str) -> str:
        c = str(caminho or "").strip()
        return f"Memoria ativa (SQLite):\n{c}" if c else "Memoria ativa (SQLite): indisponivel"

    # ------------------------------------------------------------------
    # Processamento principal
    # ------------------------------------------------------------------
    def _on_gerar(self) -> None:
        if self._historico_mgr:
            self._historico_mgr.limpar()
            self._historico_mgr.adicionar_banner("INICIO DO PROCESSAMENTO - SIPROQUIM", "SYSTEM")

        self._ajustes_por_nf = {}
        self._avisos_gerais = []
        self._alertas_operacionais = {}
        self._total_registros_extraidos = 0
        self._total_nfs_dedup = 0
        self._ultima_estatistica = {}

        pdf = self.entry_pdf.text().strip()
        cnpj = somente_digitos(self.entry_cnpj.text())
        mes_str = self.combo_mes.currentText()
        ano_str = somente_digitos(self.entry_ano.text())

        valido, erro_msg, dados = FormValidator.validar_formulario_completo(pdf, cnpj, mes_str, ano_str)
        if not valido:
            if self._historico_mgr:
                self._historico_mgr.adicionar_erro(f"Validacao falhou: {erro_msg}")
            self._mostrar_erro_popup("Erro", erro_msg or UIConstants.TEXT_ERRO_PDF_INVALIDO)
            return

        if self._historico_mgr:
            self._historico_mgr.adicionar("Formulario validado! [OK]", "STATUS")
            self._historico_mgr.adicionar(f"ARQUIVO: {Path(dados['pdf']).name}", "CONFIG")
            self._historico_mgr.adicionar(
                f"CNPJ: {dados['cnpj']} | PERIODO: {dados['mes_numero']:02d}/{dados['ano_numero']}", "CONFIG")

        saida_path = downloads_dir() / gerar_nome_arquivo_saida(
            dados["ano_numero"], dados["mes_abreviado"], dados["cnpj"],
            nome_pdf=Path(dados["pdf"]).name)
        self._set_busy(True)
        self._thread_processamento = threading.Thread(
            target=self._run_conversion,
            args=(dados["pdf"], dados["cnpj"], str(saida_path), dados["mes_numero"], dados["ano_numero"]),
            daemon=True,
        )
        self._thread_processamento.start()

    def _set_busy(self, busy: bool) -> None:
        self._is_busy = busy
        if busy:
            self._flag_cancelamento = False
            self._total_registros_extraidos = 0
            self._total_nfs_dedup = 0
            self._ultima_estatistica = {}
            self._atualizar_metricas()
            self.btn_converter.setEnabled(False)
            self.btn_converter.setText(UIConstants.TEXT_BUTTON_PROCESSANDO)
            self.btn_cancelar.setVisible(True)
            self.btn_cancelar.setEnabled(True)
            self.btn_buscar.setEnabled(False)
            self.entry_cnpj.setEnabled(False)
            self.btn_aprender_txt.setEnabled(False)
            self.btn_abrir_memoria.setEnabled(False)
            self._progress_manager.iniciar()
            self._atualizar_progresso(UIConstants.PROGRESSO_INICIAL, UIConstants.TEXT_STATUS_ABRINDO_PDF)
            self.lbl_tempo.setText(UIConstants.TEXT_STATUS_INICIANDO)
            self._set_status(UIConstants.TEXT_STATUS_ABRINDO_PDF)
        else:
            self.btn_converter.setEnabled(True)
            self.btn_converter.setText(UIConstants.TEXT_BUTTON_CONVERTER)
            self.btn_cancelar.setVisible(False)
            self.btn_cancelar.setEnabled(False)
            self.btn_buscar.setEnabled(True)
            self.entry_cnpj.setEnabled(True)
            self.btn_aprender_txt.setEnabled(bool(self._aprendizado_store))
            self.btn_abrir_memoria.setEnabled(bool(self._aprendizado_store))
            self._progress_manager.finalizar()
            self._verificar_habilitar_botao()

    def _cancelar_processamento(self) -> None:
        self._flag_cancelamento = True
        self.btn_cancelar.setEnabled(False)
        self.btn_cancelar.setText("Cancelando...")
        self._set_status("Cancelamento solicitado — aguardando etapa atual...")
        if self._historico_mgr:
            self._historico_mgr.adicionar_aviso("Cancelamento solicitado pelo usuario.")

    def _documento_valido_pendencia(self, documento: str, aceita_cpf: bool) -> bool:
        digitos = somente_digitos(documento)
        if len(digitos) == 14:
            return validar_cnpj(digitos)
        if aceita_cpf and len(digitos) == 11:
            return validar_cpf(digitos)
        return False

    def _resolver_pendencias_documentos(self, pendencias: list[dict]) -> dict:
        evento = threading.Event()
        resultado: dict = {"valor": {"cancelado": True}}

        def executar_popup() -> None:
            resposta = {"autorizadas": [], "documentos": []}
            try:
                for pendencia in pendencias:
                    nf = str(pendencia.get("nf", "N/A"))
                    campo = pendencia.get("campo")
                    label = pendencia.get("campo_label", "Documento")
                    nome = pendencia.get("nome") or "Nome nao identificado"

                    if pendencia.get("pode_autorizar_vazio"):
                        msg = (
                            f"NF {nf}: {label} sem CPF/CNPJ no PDF.\n\n"
                            f"Nome: {nome}\n\n"
                            "O PDF indica destino no exterior. Deseja gerar o TXT mantendo "
                            "o campo CPF/CNPJ Destino em branco para esta NF?"
                        )
                        if not self._perguntar_popup("Autorizar documento vazio", msg):
                            resposta["cancelado"] = True
                            break
                        resposta["autorizadas"].append({"nf": nf, "campo": campo})
                        continue

                    esperado = "CPF/CNPJ" if pendencia.get("aceita_cpf") else "CNPJ"
                    while True:
                        msg = (
                            f"NF {nf}: {label} nacional com documento nao extraido.\n\n"
                            f"Nome: {nome}\n\n"
                            f"Informe o {esperado} para continuar ou cancele a geracao."
                        )
                        valor, ok = self._pedir_texto_popup("Documento obrigatorio", msg)
                        if not ok:
                            resposta["cancelado"] = True
                            break
                        digitos = somente_digitos(valor)
                        if self._documento_valido_pendencia(digitos, bool(pendencia.get("aceita_cpf"))):
                            resposta["documentos"].append({
                                "nf": nf,
                                "campo": campo,
                                "documento": digitos,
                            })
                            break
                        self._mostrar_erro_popup(
                            "Documento invalido",
                            f"Informe um {esperado} valido para a NF {nf}.",
                        )
                    if resposta.get("cancelado"):
                        break
            finally:
                resultado["valor"] = resposta
                evento.set()

        self._depois(executar_popup)
        evento.wait()
        return resultado["valor"]

    def _run_conversion(self, pdf: str, cnpj: str, saida_path: str, mes: int, ano: int) -> None:
        mgr = self._historico_mgr

        _STATUS_TIPO = {
            "Processando": "INFO", "Sucesso": "SUCESSO",
            "Erro": "ERRO", "Atenção": "AVISO", "Interrompido": "AVISO",
        }

        def _adicionar(origem: str, etapa: str, status: str, detalhe: str, tem_acao: bool = False) -> None:
            tipo = _STATUS_TIPO.get(status, "INFO")
            self._depois(lambda d=detalhe, t=tipo, o=origem: (
                mgr and mgr.adicionar(d, t, origem=o)
            ))

        def cb(etapa_ev: str, detalhes: dict) -> None:
            try:
                if etapa_ev == "abrir":
                    arquivo = detalhes.get("arquivo", "")
                    if mgr:
                        mgr.definir_etapa("Extração")
                    self._depois(lambda a=arquivo: self._atualizar_status_extracao("Abrindo PDF...", a))
                    _adicionar("Sistema", "Extração", "Processando", f"Abrindo PDF: {arquivo}")

                elif etapa_ev == "extrair":
                    pag = detalhes.get("pagina_atual", 0)
                    tot = detalhes.get("total_paginas", 0)
                    self._progress_manager.total_paginas = tot
                    self._progress_manager.pagina_atual = pag
                    prog = self._progress_manager.calcular_progresso_extracao(pag, tot)
                    self._depois(lambda p=pag, t=tot, pr=prog: self._atualizar_progresso_extracao(p, t, pr))

                elif etapa_ev == "deduplicar":
                    tr = detalhes.get("total_registros", 0)
                    tn = detalhes.get("total_nfs", 0)
                    self._total_registros_extraidos = tr
                    self._total_nfs_dedup = tn
                    if mgr:
                        mgr.definir_etapa("Deduplicação")
                    self._depois(lambda a=tr, b=tn: (
                        self._atualizar_metricas(),
                        self._atualizar_progresso(UIConstants.PROGRESSO_DEDUPLICAR, f"{b} NFs apos deduplicacao"),
                    ))
                    _adicionar("Sistema", "Deduplicação", "Sucesso",
                               f"{tr} registros extraidos → {tn} NFs unicas apos deduplicacao")

                elif etapa_ev == "processar":
                    if "total_registros" in detalhes:
                        t = detalhes.get("total_registros", 0)
                        if mgr:
                            mgr.definir_etapa("Validação")
                        _adicionar("Sistema", "Validação", "Processando", f"Validando {t} registros...")
                    else:
                        self._ultima_estatistica = {
                            "total_aprovados": detalhes.get("total_aprovados"),
                            "total_corrigidos": detalhes.get("total_corrigidos", 0),
                            "total_com_erros": detalhes.get("total_com_erros", 0),
                            "total_com_erros_criticos": detalhes.get("total_com_erros_criticos", 0),
                            "total_ajustes_manuais": detalhes.get("total_ajustes_manuais", 0),
                        }
                        aj = self._ultima_estatistica.get("total_ajustes_manuais", 0)
                        crit = self._ultima_estatistica.get("total_com_erros_criticos", 0)
                        v_status = "Erro" if crit > 0 else ("Atenção" if aj > 0 else "Sucesso")
                        self._depois(self._atualizar_metricas)
                        _adicionar("Sistema", "Validação", v_status,
                                   f"Validacao concluida. Ajustes manuais: {aj} | Criticos: {crit}",
                                   tem_acao=(aj > 0 or crit > 0))

                elif etapa_ev == "gerar":
                    tn = detalhes.get("total_nfs", 0)
                    if mgr:
                        mgr.definir_etapa("Geração")
                    self._depois(lambda t=tn: self._atualizar_progresso(
                        UIConstants.PROGRESSO_GERAR, f"Montando com {t} NFs"))
                    _adicionar("Sistema", "Geração", "Processando", f"Gerando TXT com {tn} NFs")

                elif etapa_ev == "aviso":
                    mensagem = detalhes.get("mensagem", "")
                    tipo = detalhes.get("tipo", "AVISO")
                    if mensagem:
                        if tipo in ("ERRO", "CRITICO"):
                            self._depois(lambda m=mensagem: mgr and mgr.adicionar_erro(m))
                        elif tipo in ("ATENCAO", "ACAO", "ACAO_NECESSARIA", "ALERTA"):
                            self._registrar_ajuste(None, tipo, mensagem)
                        else:
                            self._depois(lambda m=mensagem: mgr and mgr.adicionar(m, "INFO"))

                elif etapa_ev == "ajuste_manual":
                    self._registrar_ajuste(
                        detalhes.get("nf"), detalhes.get("tipo", "AVISO"), detalhes.get("mensagem", ""))

                elif etapa_ev == "processar_log":
                    msg_raw = detalhes.get("mensagem", "")
                    tp = detalhes.get("tipo", "INFO")
                    norm = self._normalizar_log_processador(tp, msg_raw)
                    if norm:
                        tn_tipo, mn = norm
                        nf = self._extrair_nf_msg(mn)
                        origem = f"NF {nf}" if nf else "Sistema"
                        self._depois(lambda m=mn, t=tn_tipo, o=origem: (
                            mgr and mgr.adicionar(m, t, origem=o)
                        ))

                elif etapa_ev == "finalizar":
                    if mgr:
                        mgr.definir_etapa("Exportação")
                    self._depois(lambda: self._atualizar_progresso(
                        UIConstants.PROGRESSO_COMPLETO, "Arquivo TXT validado e pronto para envio."))

            except Exception as e:
                self._depois(lambda m=str(e): mgr and mgr.adicionar_erro(f"Erro no callback: {m}"))

        try:
            caminho_final = processar_pdf(
                pdf, cnpj, saida_path,
                callback_progresso=cb,
                mes=mes, ano=ano,
                callback_cancelamento=lambda: self._flag_cancelamento,
                callback_resolver_pendencias=self._resolver_pendencias_documentos,
            )
            self._depois(self._log_resumo_analista)
            self._depois(self._log_relatorio_final)
            tc = self._ultima_estatistica.get("total_com_erros_criticos", 0)
            if tc > 0:
                _adicionar("Sistema", "Exportação", "Atenção",
                           "Processamento concluido com pendencias criticas.", tem_acao=True)
            else:
                _adicionar("Sistema", "Exportação", "Sucesso", "Processamento concluido com sucesso!")
            _adicionar("Sistema", "Exportação", "Sucesso", f"ARQUIVO GERADO: {caminho_final}")
            self._depois(lambda c=caminho_final, x=tc: self._on_sucesso(c, tem_criticos=(x > 0)))

        except ProcessamentoInterrompido:
            self._depois(self._on_interrompido)

        except FileNotFoundError as e:
            m = f"Arquivo nao encontrado: {e}"
            self._depois(lambda msg=m: mgr and mgr.adicionar_erro(msg))
            self._depois(lambda msg=m: self._on_erro(msg))

        except ValueError as e:
            m = f"Erro de validacao: {e}"
            self._depois(lambda msg=m: mgr and mgr.adicionar_erro(msg))
            self._depois(lambda msg=m: self._on_erro(msg))

        except Exception as e:
            tb = traceback.format_exc()
            m = f"Erro inesperado: {e}"
            self._depois(lambda msg=m: mgr and mgr.adicionar_erro(msg))
            for linha in tb.split("\n")[:15]:
                if linha.strip():
                    self._depois(lambda l=linha: mgr and mgr.adicionar_debug(f"  {l}"))
            self._depois(lambda msg=m: self._on_erro(msg))

    def _atualizar_status_extracao(self, acao: str, detalhe: str = "") -> None:
        self._set_status(f"{acao} {detalhe}".strip())

    def _atualizar_progresso_extracao(self, pag: int, total: int, prog: float) -> None:
        self._atualizar_progresso(prog, f"Leitura do PDF: pagina {pag}/{total}")
        td = self._progress_manager.obter_tempo_decorrido()
        if td is not None:
            tr = self._progress_manager.estimar_tempo_restante(pag, total)
            if tr is not None:
                self.lbl_tempo.setText(
                    f"Pagina {pag}/{total} | Tempo: {self._progress_manager.formatar_tempo(td)} | "
                    f"Restante: {self._progress_manager.formatar_tempo(tr)}")
            else:
                self.lbl_tempo.setText(f"Tempo decorrido: {self._progress_manager.formatar_tempo(td)}")

    def _on_sucesso(self, caminho: str, tem_criticos: bool = False) -> None:
        self._set_busy(False)
        td = self._progress_manager.obter_tempo_decorrido()
        if td:
            ts = self._progress_manager.formatar_tempo(td)
            self._set_status(
                f"Conversao concluida em {ts}." if not tem_criticos
                else f"Finalizado em {ts} com pendencias criticas.")
            self.lbl_tempo.setText(f"Tempo total: {ts}")
        else:
            self._set_status(UIConstants.TEXT_SUCESSO_CONVERSAO if not tem_criticos
                             else "Processamento finalizado com pendencias criticas.")
        self._atualizar_progresso(UIConstants.PROGRESSO_COMPLETO, "Lote finalizado.")
        caminho_abs = Path(caminho).absolute()
        if tem_criticos:
            self._mostrar_aviso(
                UIConstants.DIALOG_TITLE_AVISO,
                f"Arquivo gerado com pendencias criticas.\nRevise o log antes de enviar ao SIPROQUIM.\n\n"
                f"{UIConstants.TEXT_SUCESSO_ARQUIVO_SALVO}\n{caminho_abs}",
            )
        abrir_downloads = self._perguntar_popup(
            UIConstants.DIALOG_TITLE_SUCESSO,
            f"{UIConstants.TEXT_SUCESSO_ARQUIVO_SALVO}\n{caminho_abs}\n\n{UIConstants.TEXT_SUCESSO_ABRIR_DOWNLOADS}",
        )
        if abrir_downloads:
            try:
                os.startfile(downloads_dir())
            except Exception:
                subprocess.run(["explorer", str(downloads_dir())])

    def _on_erro(self, erro: str) -> None:
        self._set_busy(False)
        self._set_status(UIConstants.TEXT_ERRO_CONVERSAO)
        self._atualizar_progresso(0.0, "Falha no processamento. Consulte o historico.")
        self.lbl_tempo.setText("")
        self._mostrar_erro_popup(
            UIConstants.DIALOG_TITLE_ERRO,
            UIConstants.TEXT_ERRO_DETALHES.format(erro=erro),
        )

    def _on_interrompido(self) -> None:
        self._set_busy(False)
        self._flag_cancelamento = False
        self.btn_cancelar.setText("Cancelar processamento")
        self._atualizar_progresso(0.0, "Processamento cancelado pelo usuario.")
        self.lbl_tempo.setText("")
        self._set_status("Processamento interrompido.")
        self._aplicar_estilo_badge(self.header_status_badge, "Interrompido")
        if self._historico_mgr:
            self._historico_mgr.adicionar_aviso("Processamento interrompido pelo usuario.")
            self._historico_mgr.adicionar_aviso("Processamento cancelado pelo usuario antes da conclusao.")

    # ------------------------------------------------------------------
    # Exportar logs
    # ------------------------------------------------------------------
    def _exportar_logs(self) -> None:
        if not self._historico_mgr:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Exportar logs", f"logs_siproquim_{ts}.txt", "Arquivo de texto (*.txt)")
        if caminho:
            self._historico_mgr.exportar(caminho)
            self._historico_mgr.adicionar_info(f"Logs exportados para: {caminho}")

    # ------------------------------------------------------------------
    # Auxiliares
    # ------------------------------------------------------------------
    @staticmethod
    def _extrair_nf_msg(mensagem: str) -> Optional[str]:
        m = re.match(r"^NF\s+(\d+)", (mensagem or "").strip())
        return m.group(1) if m else None

    def _formatar_barra_progresso(self, p: float, w: int = 20) -> str:
        try:
            p = max(0.0, min(1.0, float(p)))
        except (TypeError, ValueError):
            p = 0.0
        ch = int(p * w) if p < 1.0 else w
        return f"[{'#' * ch}{'-' * max(0, w - ch)}]"

    def _formatar_check(self, label: str, valor: str, largura: int = 32) -> str:
        base = f"{label}:"
        return f"{base}{('.' * (largura - len(base)))} {valor}" if len(base) < largura else f"{base} {valor}"

    def _normalizar_texto(self, texto: str) -> str:
        texto = unicodedata.normalize("NFD", (texto or "").lower())
        return "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")

    def _normalizar_log_processador(self, tipo: str, mensagem: str) -> Optional[tuple]:
        if not mensagem:
            return None
        msg = mensagem.strip()
        tp = (tipo or "INFO").upper()
        if tp in ("ACAO_NECESSARIA", "ATENCAO", "ALERTA"):
            return None
        if msg.startswith("="):
            return None
        mn = self._normalizar_texto(msg)
        skip = ("relatorio final", "total de registros processados", "registros corrigidos",
                "registros com erros", "total de erros encontrados",
                "ajustes manuais necessarios", "total exportado para txt")
        if any(mn.startswith(s) for s in skip):
            return None
        if "validacao robusta" in mn or "sistema de validacao" in mn:
            return None
        if mn.startswith("estrutura do pdf validada"):
            return ("STATUS", "Estrutura do PDF validada... [OK]")
        if tp == "CRITICO":
            tp = "ERRO"
        if tp == "VALIDACAO":
            tp = "INFO"
        if tp not in UIConstants.LOG_TIPOS:
            tp = "INFO"
        return (tp, msg)

    def _limpar_prefixo_mensagem(self, mensagem: str, nf: Optional[str] = None) -> str:
        msg = (mensagem or "").strip()
        if nf and msg.startswith(f"NF {nf}:"):
            msg = msg[len(f"NF {nf}:"):].strip()
        for pref in ("AVISO:", "ALERTA:", "ATENCAO:", "ATENÇÃO:", "WARNING:", "WARN:"):
            if msg.upper().startswith(pref):
                msg = msg[len(pref):].strip()
        return msg

    def _classificar_ajuste(self, mensagem: str) -> dict:
        detalhe = " ".join((mensagem or "").split())
        texto = self._normalizar_texto(detalhe)
        tipo, acao, manual = "REVISAO", "Verifique e ajuste manualmente no TXT.", True
        if "recebedor suspeito" in texto:
            if "substituido por" in texto or "substituido automaticamente" in texto:
                tipo, acao, manual = "RECEBEDOR AUTOAJUSTADO", "Ajuste automatico aplicado.", False
            else:
                tipo, acao = "RECEBEDOR", "Verifique o recebedor."
        elif "contratante" in texto and "igual ao" in texto:
            tipo, acao, manual = "REGRA NEGOCIO", "Aviso operacional.", False
        elif "cpf" in texto and "ao inves de cnpj" in texto:
            tipo, acao = "CPF DETECTADO", "Substitua por CNPJ valido."
        elif "cnpj" in texto and "invalido" in texto:
            tipo, acao = "CNPJ INVALIDO", "Corrija o CNPJ."
        elif "nome" in texto and "vazio" in texto:
            tipo, acao = "DADO AUSENTE", "Preencha o nome manualmente."
        return {"tipo": tipo, "detalhe": detalhe, "acao": acao, "manual": manual}

    def _registrar_alerta_operacional(self, tipo: str, nf: Optional[str], detalhe: str) -> None:
        bucket = self._alertas_operacionais.setdefault(tipo, {"nfs": set(), "amostras": []})
        if nf and nf not in ("N/A", "NA"):
            bucket["nfs"].add(str(nf))
        d = (detalhe or "").strip()
        if d and d not in bucket["amostras"] and len(bucket["amostras"]) < 3:
            bucket["amostras"].append(d)

    def _registrar_ajuste(self, nf: Optional[str], tipo: str, mensagem: str) -> None:
        if not mensagem:
            return
        if nf and nf not in ("N/A", "NA"):
            chave = str(nf)
            msg = self._limpar_prefixo_mensagem(mensagem, chave)
            info = self._classificar_ajuste(msg)
            if not info.get("manual", True):
                self._registrar_alerta_operacional(info.get("tipo", "ALERTA"), chave, info.get("detalhe", ""))
                return
            self._ajustes_por_nf.setdefault(chave, [])
            if info not in self._ajustes_por_nf[chave]:
                self._ajustes_por_nf[chave].append(info)
            resumo = info.get("detalhe", msg)
            detalhe_completo = f"{resumo} > ACAO: {info.get('acao', '')}"
            mgr = self._historico_mgr
            self._depois(lambda d=detalhe_completo, c=chave: (
                mgr and mgr.adicionar(d, "AVISO", origem=f"NF {c}")
            ))
        else:
            msg = self._limpar_prefixo_mensagem(mensagem)
            info = self._classificar_ajuste(msg)
            if not info.get("manual", True):
                self._registrar_alerta_operacional(info.get("tipo", "ALERTA"), None, info.get("detalhe", ""))
                return
            if msg and msg not in self._avisos_gerais:
                self._avisos_gerais.append(msg)

    def _log_resumo_analista(self) -> None:
        if not self._historico_mgr:
            return
        total_nfs = len(self._ajustes_por_nf)
        if total_nfs == 0 and not self._alertas_operacionais:
            self._historico_mgr.adicionar_sucesso("Revisao manual: nenhum ajuste detectado.")
            return
        if total_nfs > 0:
            self._historico_mgr.adicionar_aviso(f"Revisao manual necessaria: {total_nfs} notas")
            for nf in sorted(self._ajustes_por_nf.keys(), key=lambda x: int(x) if x.isdigit() else x):
                itens = self._ajustes_por_nf[nf]
                if not itens:
                    continue
                p = itens[0]
                acoes = list({i.get("acao") for i in itens if i.get("acao")})
                resumo = f"[{p.get('tipo','REVISAO')}] {p.get('detalhe','')} | ACAO: {' | '.join(acoes)}"
                self._historico_mgr.adicionar(resumo, "AVISO", origem=f"NF {nf}")

    def _log_relatorio_final(self) -> None:
        if not self._historico_mgr:
            return
        s = self._ultima_estatistica or {}
        ta = s.get("total_aprovados") or self._total_nfs_dedup or 0
        tc = s.get("total_corrigidos", 0)
        te = s.get("total_com_erros", 0)
        tcr = s.get("total_com_erros_criticos", 0)
        taj = max(s.get("total_ajustes_manuais", 0), len(self._ajustes_por_nf))
        tipo_final = "ERRO" if tcr > 0 else ("AVISO" if taj > 0 or te > 0 else "SUCESSO")
        detalhe = (f"Status: {'FALHA' if tcr > 0 else 'SUCESSO'} | Total: {ta} NFs | "
                   f"Corrigidos: {tc} | Ajustes manuais: {taj} | Criticos: {tcr}")
        self._historico_mgr.adicionar(detalhe, tipo_final)
        if self._avisos_gerais:
            for av in self._avisos_gerais:
                self._historico_mgr.adicionar_aviso(av)

    # ------------------------------------------------------------------
    # Tema claro / escuro
    # ------------------------------------------------------------------
    def _carregar_tema_salvo(self) -> None:
        cfg = QSettings("valentelucass", "SIPROQUIMConverter")
        tema = cfg.value("theme", "claro")
        if tema == "escuro":
            self._aplicar_tema("escuro")

    def _alternar_tema(self) -> None:
        novo = "escuro" if self._tema_atual == "claro" else "claro"
        self._aplicar_tema(novo)
        cfg = QSettings("valentelucass", "SIPROQUIMConverter")
        cfg.setValue("theme", novo)

    def _aplicar_tema(self, tema: str) -> None:
        self._tema_atual = tema
        self._paleta_atual = PALETA_ESCURA if tema == "escuro" else PALETA_CLARA
        self._aplicar_estilo_global(self._paleta_atual)

        # Atualiza ícone do botão
        # Sempre mostra ☀
        self.btn_tema.setText("☀")

        # Atualiza elementos com estilos inline
        p = self._paleta_atual
        self._header_divisor.setStyleSheet(
            f"background: {p['borda_forte']}; border: none;"
        )
        self.btn_converter.definir_paleta(
            p["btn_pri_bg"], p["btn_pri_hover"], p["btn_pri_text"]
        )

        # Atualiza cores dos logs
        if self._historico_mgr:
            self._historico_mgr.atualizar_cores_tema(tema)

        # Re-aplica badge (especificidade CSS do QSS global pode sobrescrever)
        self._aplicar_estilo_badge(self.header_status_badge_frame, self.header_status_badge.text())

        # Atualiza logo (inversão no modo escuro)
        self._atualizar_logo_tema(tema)

    def _atualizar_logo_tema(self, tema: str) -> None:
        if self._logo_pixmap_original is None or self._logo_pixmap_original.isNull():
            return
        from PySide6.QtGui import QPainter
        px = self._logo_pixmap_original
        if tema == "escuro":
            # brightness(0) invert(1) — silhueta branca preservando alpha
            orig = px.toImage().convertToFormat(QImage.Format_ARGB32)
            branco = QImage(orig.size(), QImage.Format_ARGB32)
            branco.fill(0)
            p2 = QPainter(branco)
            p2.fillRect(branco.rect(), QColor(255, 255, 255))
            p2.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            p2.drawImage(0, 0, orig)
            p2.end()
            px = QPixmap.fromImage(branco)
        self._logo_lbl.setPixmap(px.scaledToHeight(40, Qt.SmoothTransformation))

    # ------------------------------------------------------------------
    # Rodapé institucional
    # ------------------------------------------------------------------
    def _criar_rodape(self) -> QFrame:
        p = self._paleta_atual
        rodape = QFrame()
        rodape.setObjectName("rodapePainel")

        layout = QHBoxLayout(rodape)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(20)

        # Bloco esquerdo
        esq = QVBoxLayout()
        esq.setSpacing(3)
        lbl_nome = QLabel("CONVERSOR SIPROQUIM")
        lbl_nome.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {p['primaria']};")
        lbl_desc = QLabel("Automação desktop para conversão de PDF para TXT no formato SIPROQUIM.")
        lbl_desc.setObjectName("labelSutil")
        lbl_desc.setStyleSheet("font-size: 11px;")
        esq.addWidget(lbl_nome)
        esq.addWidget(lbl_desc)
        layout.addLayout(esq, 1)

        # Separador vertical
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Plain)
        sep.setStyleSheet(f"color: {p['borda']}; background: {p['borda']}; max-width: 1px;")
        layout.addWidget(sep)

        # Bloco direito
        dir_lay = QVBoxLayout()
        dir_lay.setSpacing(3)
        lbl_dev = QLabel(
            'Desenvolvido por <a href="https://www.linkedin.com/in/dev-lucasandrade/" '
            f'style="color: {p["primaria"]}; text-decoration: none; font-weight: 700;">@valentelucass</a>'
        )
        lbl_dev.setOpenExternalLinks(True)
        lbl_dev.setStyleSheet("font-size: 11px;")
        lbl_email = QLabel("Suporte: lucasmac.dev@gmail.com")
        lbl_email.setObjectName("labelSutil")
        lbl_email.setStyleSheet("font-size: 11px;")
        dir_lay.addWidget(lbl_dev, alignment=Qt.AlignRight)
        dir_lay.addWidget(lbl_email, alignment=Qt.AlignRight)
        layout.addLayout(dir_lay)

        return rodape


# ===========================================================================
# Bootstrap
# ===========================================================================
def _configurar_fonte(app: QApplication) -> None:
    fonte_path = _recursos_dir() / "public" / "fonts" / "Manrope-Variable.ttf"
    if fonte_path.exists():
        fid = QFontDatabase.addApplicationFont(str(fonte_path))
        familias = QFontDatabase.applicationFontFamilies(fid)
        if familias:
            f = QFont(familias[0], 10)
            f.setStyleStrategy(QFont.PreferAntialias)
            app.setFont(f)
            return

    familias_disponiveis = QFontDatabase.families()
    for nome in ("Segoe UI Variable", "Segoe UI", "Aptos", "Bahnschrift", "Calibri", "Arial"):
        if nome in familias_disponiveis:
            f = QFont(nome, 10)
            f.setStyleStrategy(QFont.PreferAntialias)
            app.setFont(f)
            return


def criar_app_qt() -> tuple["QApplication", "JanelaConversor"]:
    """Cria e configura o QApplication + JanelaConversor."""
    from PySide6.QtCore import Qt

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    _configurar_fonte(app)

    caminho_icone = _recursos_dir() / "public" / "icon.ico"
    if caminho_icone.exists():
        app.setWindowIcon(QIcon(str(caminho_icone)))

    janela = JanelaConversor()
    return app, janela
