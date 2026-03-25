"""
Gerenciador de logs para a interface PySide6.
"""

import re
import time
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from .constants import UIConstants


class LogManagerQt:
    """Gerenciador de logs para a interface PySide6."""

    def __init__(
        self,
        textbox: QTextEdit,
        font_family: str,
        font_size: int,
        on_log_added=None,
    ):
        self.textbox = textbox
        self.logs: list[str] = []
        # Cada entrada: (texto_da_linha, tipo, primeira_linha_da_mensagem)
        self._entradas: list[tuple[str, str, bool]] = []
        self.font_family = font_family
        self.font_size = font_size
        self.on_log_added = on_log_added
        self._cores_override: dict[str, str] = {}
        self._aplicar_fonte()

    def definir_cores_override(self, mapa: dict[str, str]) -> None:
        """Substitui as cores para o tema atual e re-renderiza todos os logs."""
        self._cores_override = mapa or {}
        self._re_renderizar()

    # ------------------------------------------------------------------
    # Configuração
    # ------------------------------------------------------------------

    def _aplicar_fonte(self) -> None:
        font = QFont(self.font_family, self.font_size)
        font.setStyleHint(QFont.Monospace)
        self.textbox.setFont(font)

    def ajustar_fonte(self, delta: int) -> None:
        novo = max(
            UIConstants.LOG_FONT_SIZE_MIN,
            min(UIConstants.LOG_FONT_SIZE_MAX, self.font_size + delta),
        )
        if novo != self.font_size:
            self.font_size = novo
            self._aplicar_fonte()

    # ------------------------------------------------------------------
    # Inserção
    # ------------------------------------------------------------------

    def adicionar(self, mensagem: str, tipo: str = "INFO") -> None:
        timestamp = time.strftime("%H:%M:%S")
        cor = self._resolver_cor(tipo)

        linhas = str(mensagem or "").split("\n")
        for i, linha in enumerate(linhas):
            if not linha.strip():
                continue
            primeira = i == 0
            if primeira:
                entry = f"[{timestamp}] [{tipo}] {linha}\n"
            else:
                entry = f"  | {linha}\n"
            self.logs.append(entry)
            self._entradas.append((entry, tipo, primeira))
            self._inserir_texto(entry, cor, tipo, primeira)

        if self.on_log_added:
            try:
                self.on_log_added(timestamp, tipo, mensagem)
            except Exception:
                pass

    def _resolver_cor(self, tipo: str) -> str:
        cor = self._cores_override.get(tipo)
        if not cor:
            cor = UIConstants.LOG_TIPOS.get(tipo, UIConstants.COLOR_LOG_INFO)
            if isinstance(cor, tuple):
                cor = cor[0]
        return cor

    def _inserir_texto(self, texto: str, cor: str, tipo: str, primeira_linha: bool) -> None:
        cursor = self.textbox.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(cor))
        cursor.setCharFormat(fmt)
        cursor.insertText(texto)

        if primeira_linha:
            self._destacar_padroes(cursor, texto)

        self.textbox.setTextCursor(cursor)
        self.textbox.ensureCursorVisible()

    def _re_renderizar(self) -> None:
        """Limpa e re-insere todos os logs com as cores do tema atual."""
        if not self._entradas:
            return
        self.textbox.clear()
        for entry, tipo, primeira_linha in self._entradas:
            cor = self._resolver_cor(tipo)
            self._inserir_texto(entry, cor, tipo, primeira_linha)

    def _destacar_padroes(self, cursor: QTextCursor, texto: str) -> None:
        """Aplica cor diferenciada para NF XXXX e > ACAO: dentro da linha."""
        doc = self.textbox.document()
        bloco = doc.lastBlock()
        if not bloco.isValid():
            return

        bloco_texto = bloco.text()
        offset = bloco.position()

        cor_nf = UIConstants.COLOR_LOG_NF
        if isinstance(cor_nf, tuple):
            cor_nf = cor_nf[0]
        cor_acao = UIConstants.COLOR_LOG_ACTION
        if isinstance(cor_acao, tuple):
            cor_acao = cor_acao[0]

        for match in re.finditer(r"\bNF\s+\d+\b", bloco_texto, re.IGNORECASE):
            c = self.textbox.textCursor()
            c.setPosition(offset + match.start())
            c.setPosition(offset + match.end(), QTextCursor.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(cor_nf))
            c.setCharFormat(fmt)

        match_acao = re.search(r">\s*ACAO:", bloco_texto, re.IGNORECASE)
        if match_acao:
            c = self.textbox.textCursor()
            c.setPosition(offset + match_acao.start())
            c.setPosition(offset + len(bloco_texto), QTextCursor.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(cor_acao))
            c.setCharFormat(fmt)

    # ------------------------------------------------------------------
    # Atalhos semânticos
    # ------------------------------------------------------------------

    def adicionar_banner(self, titulo: str, tipo: str = "INFO") -> None:
        linha = "=" * 60
        self.adicionar(linha, tipo)
        self.adicionar(titulo, tipo)
        self.adicionar(linha, tipo)

    def adicionar_erro(self, mensagem: str) -> None:
        self.adicionar(mensagem, "ERRO")

    def adicionar_sucesso(self, mensagem: str) -> None:
        self.adicionar(mensagem, "SUCESSO")

    def adicionar_info(self, mensagem: str) -> None:
        self.adicionar(mensagem, "INFO")

    def adicionar_aviso(self, mensagem: str) -> None:
        self.adicionar(mensagem, "AVISO")

    def adicionar_debug(self, mensagem: str) -> None:
        self.adicionar(mensagem, "DEBUG")

    # ------------------------------------------------------------------
    # Limpeza / exportação
    # ------------------------------------------------------------------

    def limpar(self) -> None:
        self.logs.clear()
        self._entradas.clear()
        self.textbox.clear()

    def exportar(self, caminho: str) -> None:
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            for linha in self.logs:
                f.write(linha)
