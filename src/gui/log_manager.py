"""
Gerenciador de logs da interface gráfica.
"""

import time
import re
import customtkinter as ctk
from typing import Optional
from .constants import UIConstants


class LogManager:
    """Gerenciador de logs para a interface gráfica."""
    
    def __init__(self, textbox: ctk.CTkTextbox, frame_logs: ctk.CTkFrame,
                 font_family: str, font_size: int):
        """
        Inicializa o gerenciador de logs.
        
        Args:
            textbox: Widget CTkTextbox para exibir logs
            frame_logs: Frame que contém o textbox (para mostrar/ocultar)
            font_family: Família da fonte dos logs
            font_size: Tamanho inicial da fonte dos logs
        """
        self.textbox = textbox
        self.frame_logs = frame_logs
        self.logs = []
        self.font_family = font_family
        self.font_size = font_size
        self._font_normal = None
        self._font_bold = None
        self._aplicar_fonte()
        self._configurar_tags()
    
    def _configurar_tags(self):
        """Configura tags de cor para cada tipo de log."""
        for tipo, cor in UIConstants.LOG_TIPOS.items():
            tag_name = f"tag_{tipo}"
            self.textbox.tag_config(tag_name, foreground=cor)
        # CTkTextbox não permite configurar fonte por tag (incompatível com scaling)
        if self._font_bold:
            self.textbox.tag_config("tag_nf", foreground=UIConstants.COLOR_LOG_NF)
            self.textbox.tag_config("tag_acao", foreground=UIConstants.COLOR_LOG_ACTION)
    
    def _aplicar_fonte(self):
        """Aplica fonte atual no textbox de logs."""
        self._font_normal = ctk.CTkFont(family=self.font_family, size=self.font_size)
        self._font_bold = ctk.CTkFont(family=self.font_family, size=self.font_size, weight="bold")
        self.textbox.configure(font=self._font_normal)

    def ajustar_fonte(self, delta: int):
        """Ajusta o tamanho da fonte dos logs."""
        novo_tamanho = self.font_size + delta
        novo_tamanho = max(UIConstants.LOG_FONT_SIZE_MIN, min(UIConstants.LOG_FONT_SIZE_MAX, novo_tamanho))
        if novo_tamanho != self.font_size:
            self.font_size = novo_tamanho
            self._aplicar_fonte()
            self._configurar_tags()

    def adicionar_banner(self, titulo: str, tipo: str = "INFO"):
        """Adiciona um banner visual para separar seções."""
        linha = "=" * 60
        self.adicionar(linha, tipo)
        self.adicionar(titulo, tipo)
        self.adicionar(linha, tipo)

    def exportar(self, caminho: str):
        """Exporta logs para um arquivo de texto."""
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            for linha in self.logs:
                f.write(linha)
    
    def adicionar(self, mensagem: str, tipo: str = "INFO"):
        """
        Adiciona uma mensagem de log.
        
        Args:
            mensagem: Mensagem a ser adicionada (pode conter quebras de linha \n)
            tipo: Tipo do log (ERRO, SUCESSO, INFO, DEBUG, AVISO)
        """
        timestamp = time.strftime("%H:%M:%S")
        
        # Se a mensagem contém quebras de linha, divide em múltiplas linhas de log
        # Cada linha terá o timestamp e tipo
        linhas_mensagem = mensagem.split('\n')
        
        self.textbox.configure(state="normal")
        
        for i, linha_msg in enumerate(linhas_mensagem):
            if linha_msg.strip():  # Ignora linhas vazias
                # Primeira linha tem timestamp e tipo, linhas seguintes são continuação
                if i == 0:
                    log_entry = f"[{timestamp}] [{tipo}] {linha_msg}\n"
                else:
                    # Linhas seguintes são continuação (sem timestamp duplicado)
                    log_entry = f"  | {linha_msg}\n"
                
                self.logs.append(log_entry)
                
                # Adiciona com tag para colorir
                pos_inicio = self.textbox.index("end-1c")
                self.textbox.insert("end", log_entry)
                pos_fim = self.textbox.index("end-1c")
                
                # Configura tag para colorir
                tag_name = f"tag_{tipo}"
                cor = UIConstants.LOG_TIPOS.get(tipo, "#FFFFFF")
                self.textbox.tag_config(tag_name, foreground=cor)
                self.textbox.tag_add(tag_name, pos_inicio, pos_fim)
                self._aplicar_destaques(log_entry, pos_inicio)
        
        self.textbox.configure(state="disabled")
        self.textbox.see("end")  # Scroll to bottom
        # Frame de logs sempre visível no novo layout horizontal
    
    def _aplicar_destaques(self, log_entry: str, pos_inicio: str) -> None:
        """Aplica destaques para NF e ACAO dentro da linha."""
        if not log_entry:
            return
        linha_limpa = log_entry.rstrip("\n")
        for match in re.finditer(r"\bNF\s+\d+\b", linha_limpa, flags=re.IGNORECASE):
            start = self.textbox.index(f"{pos_inicio}+{match.start()}c")
            end = self.textbox.index(f"{pos_inicio}+{match.end()}c")
            self.textbox.tag_add("tag_nf", start, end)
        match_acao = re.search(r">\s*ACAO:", linha_limpa, flags=re.IGNORECASE)
        if match_acao:
            start = self.textbox.index(f"{pos_inicio}+{match_acao.start()}c")
            end = self.textbox.index(f"{pos_inicio}+{len(linha_limpa)}c")
            self.textbox.tag_add("tag_acao", start, end)

    def limpar(self):
        """Limpa todos os logs."""
        self.logs = []
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        # Frame de logs sempre visível no novo layout horizontal
    
    def adicionar_erro(self, mensagem: str):
        """Adiciona mensagem de erro."""
        self.adicionar(mensagem, "ERRO")
    
    def adicionar_sucesso(self, mensagem: str):
        """Adiciona mensagem de sucesso."""
        self.adicionar(mensagem, "SUCESSO")
    
    def adicionar_info(self, mensagem: str):
        """Adiciona mensagem informativa."""
        self.adicionar(mensagem, "INFO")
    
    def adicionar_aviso(self, mensagem: str):
        """Adiciona mensagem de aviso."""
        self.adicionar(mensagem, "AVISO")
    
    def adicionar_debug(self, mensagem: str):
        """Adiciona mensagem de debug."""
        self.adicionar(mensagem, "DEBUG")
