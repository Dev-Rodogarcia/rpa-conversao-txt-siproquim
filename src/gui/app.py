"""
Aplicação principal da interface gráfica.
Classe App que gerencia toda a interface do usuário.
"""

from __future__ import annotations

import os
import threading
import subprocess
import traceback
import unicodedata
from datetime import datetime
from pathlib import Path
from tkinter import StringVar, filedialog, messagebox
from typing import Optional
import customtkinter as ctk

# Importações da lógica principal
try:
    from main import processar_pdf
except ImportError:
    # Fallback apenas para teste visual se o main.py não estiver presente
    import time
    def processar_pdf(pdf, cnpj, saida, **kwargs):
        time.sleep(3)  # Simula processamento
        with open(saida, 'w') as f:
            f.write("Teste")
        return saida

# Importa FiliaisManager - sempre do módulo real, nunca do fallback
try:
    from src.config.filiais import FiliaisManager
except ImportError:
    # Se falhar, tenta importar de src.config
    from src.config import FiliaisManager

# Importações do módulo GUI refatorado
from .constants import UIConstants
from .validators import FormValidator, somente_digitos
from .log_manager import LogManager
from .progress_manager import ProgressManager
from .utils import downloads_dir, gerar_nome_arquivo_saida, extrair_ano_padrao, extrair_mes_padrao
from src.gerador.layout_constants import CNPJ_TAMANHO  # Constante compartilhada

# Configurações Globais de Tema
ctk.set_appearance_mode(UIConstants.THEME_MODE)
ctk.set_default_color_theme(UIConstants.THEME_COLOR)


class App(ctk.CTk):
    """Aplicação principal da interface gráfica."""
    
    def __init__(self) -> None:
        super().__init__()
        
        # Configurações da Janela
        self.title(UIConstants.WINDOW_TITLE)
        self.geometry(UIConstants.WINDOW_SIZE)
        self.resizable(UIConstants.WINDOW_RESIZABLE, UIConstants.WINDOW_RESIZABLE)
        self.minsize(UIConstants.WINDOW_MIN_WIDTH, UIConstants.WINDOW_MIN_HEIGHT)
        
        # Variáveis de controle
        self.pdf_path = StringVar(value="")
        self.cnpj_mapa = StringVar(value="")
        self.filial_selecionada = StringVar(value="")
        self.nome_filial = StringVar(value="")
        # Define mês e ano padrão baseado na data atual do sistema
        self.mes_selecionado = StringVar(value=extrair_mes_padrao())
        self.ano_selecionado = StringVar(value=str(extrair_ano_padrao()))
        self.status = StringVar(value=UIConstants.TEXT_STATUS_DEFAULT)
        
        # Gerenciadores
        self._is_busy = False
        self._thread_processamento = None
        self._filiais_manager = FiliaisManager()
        self._progress_manager = ProgressManager()
        self._log_manager = None  # Será inicializado após criar a UI
        self._ajustes_por_nf = {}
        self._avisos_gerais = []
        self._total_registros_extraidos = 0
        self._total_nfs_dedup = 0
        self._ultima_estatistica = {}
        self._logs_fullscreen = False
        self._logs_grid_info = None
        self._logs_prev_geom = None
        self._logs_animando = False
        
        self._build_ui()
        
        # Inicializa gerenciador de logs após criar os widgets
        # Passa frame_logs_col para mostrar/ocultar toda a coluna de logs se necessário
        self._log_manager = LogManager(
            self.textbox_logs,
            self.frame_logs_col,
            UIConstants.FONT_FAMILY_LOGS,
            UIConstants.LOG_FONT_SIZE_DEFAULT
        )
        
        # Log inicial de inicialização
        try:
            self._log_manager.adicionar_banner("SISTEMA INICIALIZADO", "INFO")
            self._log_manager.adicionar_sucesso("Sistema inicializado com sucesso!")
            self._log_manager.adicionar_info(f"Versão: SIPROQUIM Converter V5 by valentelucass")
            
            # Verifica filiais
            if hasattr(self._filiais_manager, 'listar_todas'):
                total_filiais = len(self._filiais_manager.listar_todas())
                self._log_manager.adicionar_info(f"Total de filiais cadastradas: {total_filiais}")
            else:
                # Se não tiver o método, conta pelo dicionário interno ou pelo método obter_opcoes_combo
                if hasattr(self._filiais_manager, 'obter_opcoes_combo'):
                    total_filiais = len(self._filiais_manager.obter_opcoes_combo())
                elif hasattr(self._filiais_manager, 'filiais'):
                    total_filiais = len(self._filiais_manager.filiais)
                else:
                    total_filiais = 0
                self._log_manager.adicionar_info(f"Total de filiais cadastradas: {total_filiais}")
                if not hasattr(self._filiais_manager, 'listar_todas'):
                    self._log_manager.adicionar_aviso("FiliaisManager não possui método listar_todas - usando contagem alternativa")
            
            # Verifica se combo foi populado corretamente
            opcoes_combo = self.combo_filial.cget("values")
            if opcoes_combo and len(opcoes_combo) > 1:  # Mais de 1 porque tem o placeholder
                self._log_manager.adicionar_sucesso(f"Combo de filiais carregado: {len(opcoes_combo) - 1} filiais disponíveis")
            else:
                self._log_manager.adicionar_aviso("Atenção: Combo de filiais não foi populado corretamente!")
                self._log_manager.adicionar_debug(f"Opções no combo: {opcoes_combo}")
            
            self._log_manager.adicionar_info("Aguardando ação do usuário...")
        except Exception as e:
            # Se houver erro na inicialização dos logs, tenta adicionar de forma segura
            try:
                self._log_manager.adicionar_erro(f"Erro na inicialização: {str(e)}")
            except:
                pass  # Se nem isso funcionar, ignora

    def _build_ui(self) -> None:
        """Constrói toda a interface gráfica."""
        # Layout Principal (Grid 1x1 expandido)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame Principal (Card centralizado)
        self.main_frame = ctk.CTkFrame(
            self, 
            corner_radius=UIConstants.CORNER_RADIUS_MAIN
        )
        self.main_frame.grid(
            row=0, column=0, sticky="nsew", 
            padx=UIConstants.PADDING_MAIN, 
            pady=UIConstants.PADDING_MAIN
        )
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)  # Linha 2 (conteúdo) expande

        # ============================================================================
        # LINHA 1: TÍTULO (1 coluna)
        # ============================================================================
        self.lbl_titulo = ctk.CTkLabel(
            self.main_frame,
            text=UIConstants.TEXT_TITLE,
            font=ctk.CTkFont(
                family=UIConstants.FONT_FAMILY_TITLE,
                size=UIConstants.FONT_SIZE_TITLE,
                weight="bold"
            ),
            text_color=UIConstants.COLOR_TEXT_PRIMARY
        )
        self.lbl_titulo.grid(row=0, column=0, columnspan=2, pady=(15, 5), sticky="n")

        self.lbl_subtitulo = ctk.CTkLabel(
            self.main_frame,
            text=UIConstants.TEXT_SUBTITLE,
            font=ctk.CTkFont(
                family=UIConstants.FONT_FAMILY_TITLE,
                size=UIConstants.FONT_SIZE_SUBTITLE
            ),
            text_color=UIConstants.COLOR_TEXT_SECONDARY
        )
        self.lbl_subtitulo.grid(row=1, column=0, columnspan=2, pady=(0, 15), sticky="n")

        # ============================================================================
        # LINHA 2: CONTEÚDO (2 colunas: Formulário | Logs)
        # ============================================================================
        
        # --- Coluna 1: Formulário (Itens 1, 2, 3) ---
        self.frame_formulario = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frame_formulario.grid(
            row=2, column=0, sticky="nsew",
            padx=(UIConstants.PADDING_FRAME, 15),
            pady=(0, 0)
        )
        self.frame_formulario.columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1, minsize=500)  # Coluna 1: formulário
        
        # --- Passo 1: Arquivo PDF ---
        self.frame_pdf = ctk.CTkFrame(self.frame_formulario, fg_color="transparent")
        self.frame_pdf.grid(
            row=0, column=0, sticky="ew",
            pady=(0, 12)
        )
        self.frame_pdf.columnconfigure(0, weight=1)

        self.lbl_step1 = ctk.CTkLabel(
            self.frame_pdf,
            text=UIConstants.TEXT_STEP_1,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_HEADING, weight="bold"),
            anchor="w"
        )
        self.lbl_step1.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.entry_pdf = ctk.CTkEntry(
            self.frame_pdf,
            textvariable=self.pdf_path,
            placeholder_text=UIConstants.PLACEHOLDER_PDF,
            state="readonly",
            height=UIConstants.HEIGHT_ENTRY
        )
        self.entry_pdf.grid(row=1, column=0, sticky="ew", padx=(0, UIConstants.PADDING_INTERNAL))

        self.btn_buscar = ctk.CTkButton(
            self.frame_pdf,
            text=UIConstants.TEXT_BUTTON_BUSCAR_PDF,
            command=self._choose_pdf,
            width=UIConstants.WIDTH_BUTTON_SMALL,
            height=UIConstants.HEIGHT_BUTTON_SMALL,
            fg_color=UIConstants.COLOR_SECONDARY,
            hover_color=UIConstants.COLOR_SECONDARY_HOVER
        )
        self.btn_buscar.grid(row=1, column=1)

        # --- Passo 2: Seleção de Filial/CNPJ ---
        self.frame_cnpj = ctk.CTkFrame(self.frame_formulario, fg_color="transparent")
        self.frame_cnpj.grid(
            row=1, column=0, sticky="ew",
            pady=(0, 12)
        )
        self.frame_cnpj.columnconfigure(0, weight=1)
        self.frame_cnpj.columnconfigure(1, weight=0)

        self.lbl_step2 = ctk.CTkLabel(
            self.frame_cnpj,
            text=UIConstants.TEXT_STEP_2,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_HEADING, weight="bold"),
            anchor="w"
        )
        self.lbl_step2.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # Campo de busca/entrada de CNPJ
        self.frame_busca = ctk.CTkFrame(self.frame_cnpj, fg_color="transparent")
        self.frame_busca.grid(row=1, column=0, sticky="ew", columnspan=2)
        self.frame_busca.columnconfigure(0, weight=1)
        self.frame_busca.columnconfigure(1, weight=0)

        self.entry_cnpj = ctk.CTkEntry(
            self.frame_busca,
            textvariable=self.cnpj_mapa,
            placeholder_text=UIConstants.PLACEHOLDER_CNPJ,
            height=UIConstants.HEIGHT_ENTRY
        )
        self.entry_cnpj.grid(row=0, column=0, sticky="ew", padx=(0, UIConstants.PADDING_INTERNAL))

        # Botão de busca
        self.btn_buscar_filial = ctk.CTkButton(
            self.frame_busca,
            text=UIConstants.TEXT_BUTTON_BUSCAR_FILIAL,
            command=self._buscar_filial_por_cnpj,
            width=UIConstants.WIDTH_BUTTON_SMALL,
            height=UIConstants.HEIGHT_BUTTON_SMALL,
            fg_color=UIConstants.COLOR_SECONDARY,
            hover_color=UIConstants.COLOR_SECONDARY_HOVER
        )
        self.btn_buscar_filial.grid(row=0, column=1)

        # ComboBox de seleção de filial
        try:
            # Garante que o FiliaisManager está funcionando
            if not hasattr(self._filiais_manager, 'obter_opcoes_combo'):
                raise AttributeError("FiliaisManager não possui método obter_opcoes_combo")
            
            opcoes_filiais = self._filiais_manager.obter_opcoes_combo()
            # Adiciona opção vazia no início para placeholder
            if opcoes_filiais and len(opcoes_filiais) > 0:
                opcoes_combo = [UIConstants.PLACEHOLDER_COMBO_FILIAL] + opcoes_filiais
                print(f"[DEBUG] Combo populado com {len(opcoes_filiais)} filiais")
            else:
                opcoes_combo = [UIConstants.PLACEHOLDER_COMBO_FILIAL]
                print("[DEBUG] Nenhuma filial encontrada, usando apenas placeholder")
        except Exception as e:
            # Em caso de erro, cria combo vazio com placeholder
            opcoes_combo = [UIConstants.PLACEHOLDER_COMBO_FILIAL]
            # Não pode usar _log_manager aqui pois ainda não foi inicializado
            print(f"[ERRO] Erro ao carregar filiais no combo: {e}")
            import traceback
            traceback.print_exc()
        
        self.combo_filial = ctk.CTkComboBox(
            self.frame_cnpj,
            values=opcoes_combo,
            variable=self.filial_selecionada,
            height=UIConstants.HEIGHT_ENTRY,
            command=self._on_filial_selecionada,
            state="readonly",
            dropdown_font=ctk.CTkFont(size=UIConstants.FONT_SIZE_NORMAL)
        )
        # Define valor inicial como placeholder
        if opcoes_combo:
            self.filial_selecionada.set(UIConstants.PLACEHOLDER_COMBO_FILIAL)
        self.combo_filial.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 8))

        # Label para mostrar nome da filial e CNPJ selecionado
        self.lbl_filial_info = ctk.CTkLabel(
            self.frame_cnpj,
            textvariable=self.nome_filial,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_NORMAL, weight="bold"),
            text_color=UIConstants.COLOR_TEXT_SUCCESS,
            anchor="w"
        )
        self.lbl_filial_info.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 5))
        
        # Dica visual
        self.lbl_dica = ctk.CTkLabel(
            self.frame_cnpj,
            text=UIConstants.TEXT_DICA_CNPJ,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_SMALL),
            text_color=UIConstants.COLOR_TEXT_HINT,
            anchor="w"
        )
        self.lbl_dica.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 0))

        # --- Passo 3: Mês e Ano ---
        self.frame_mes_ano = ctk.CTkFrame(self.frame_formulario, fg_color="transparent")
        self.frame_mes_ano.grid(
            row=2, column=0, sticky="ew",
            pady=(0, 12)
        )
        self.frame_mes_ano.columnconfigure(0, weight=1)
        self.frame_mes_ano.columnconfigure(1, weight=1)

        self.lbl_step3 = ctk.CTkLabel(
            self.frame_mes_ano,
            text=UIConstants.TEXT_STEP_3,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_HEADING, weight="bold"),
            anchor="w"
        )
        self.lbl_step3.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # Mês (dropdown)
        self.combo_mes = ctk.CTkComboBox(
            self.frame_mes_ano,
            values=UIConstants.MESES_ABREVIADOS,
            variable=self.mes_selecionado,
            width=UIConstants.WIDTH_COMBO_MES,
            height=UIConstants.HEIGHT_ENTRY,
            state="readonly"
        )
        self.combo_mes.grid(row=1, column=0, sticky="w", padx=(0, UIConstants.PADDING_INTERNAL))

        # Ano (entry)
        self.entry_ano = ctk.CTkEntry(
            self.frame_mes_ano,
            textvariable=self.ano_selecionado,
            placeholder_text=UIConstants.PLACEHOLDER_ANO,
            width=UIConstants.WIDTH_COMBO_ANO,
            height=UIConstants.HEIGHT_ENTRY
        )
        self.entry_ano.grid(row=1, column=1, sticky="w")
        
        # Dica visual
        self.lbl_dica_mes_ano = ctk.CTkLabel(
            self.frame_mes_ano,
            text=UIConstants.TEXT_DICA_MES_ANO,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_SMALL),
            text_color=UIConstants.COLOR_TEXT_HINT,
            anchor="w"
        )
        self.lbl_dica_mes_ano.grid(row=2, column=0, columnspan=2, sticky="w", pady=(5, 0))

        # --- Coluna 2: Logs e Status ---
        self.frame_logs_col = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.frame_logs_col.grid(
            row=2, column=1, sticky="nsew",
            padx=(15, UIConstants.PADDING_FRAME),
            pady=(0, 0)
        )
        self.frame_logs_col.columnconfigure(0, weight=1)
        self.frame_logs_col.rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1, minsize=400)  # Coluna 2: logs
        
        # Cabeçalho dos Logs (título + controles de fonte)
        self.frame_logs_header = ctk.CTkFrame(self.frame_logs_col, fg_color="transparent")
        self.frame_logs_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.frame_logs_header.columnconfigure(0, weight=1)
        self.frame_logs_header.columnconfigure(1, weight=0)
        
        self.lbl_logs_title = ctk.CTkLabel(
            self.frame_logs_header,
            text=UIConstants.TEXT_LOGS_TITLE,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_HEADING, weight="bold"),
            anchor="w"
        )
        self.lbl_logs_title.grid(row=0, column=0, sticky="w")
        
        self.frame_font_controls = ctk.CTkFrame(self.frame_logs_header, fg_color="transparent")
        self.frame_font_controls.grid(row=0, column=1, sticky="e")
        
        self.btn_font_minus = ctk.CTkButton(
            self.frame_font_controls,
            text="A-",
            width=40,
            height=24,
            command=lambda: self._ajustar_fonte_logs(-UIConstants.LOG_FONT_SIZE_STEP),
            fg_color=UIConstants.COLOR_SECONDARY,
            hover_color=UIConstants.COLOR_SECONDARY_HOVER
        )
        self.btn_font_minus.grid(row=0, column=0, padx=(0, 6))
        
        self.btn_font_plus = ctk.CTkButton(
            self.frame_font_controls,
            text="A+",
            width=40,
            height=24,
            command=lambda: self._ajustar_fonte_logs(UIConstants.LOG_FONT_SIZE_STEP),
            fg_color=UIConstants.COLOR_SECONDARY,
            hover_color=UIConstants.COLOR_SECONDARY_HOVER
        )
        self.btn_font_plus.grid(row=0, column=1)

        self.btn_export_logs = ctk.CTkButton(
            self.frame_font_controls,
            text="Exportar",
            width=80,
            height=24,
            command=self._exportar_logs,
            fg_color=UIConstants.COLOR_SECONDARY,
            hover_color=UIConstants.COLOR_SECONDARY_HOVER
        )
        self.btn_export_logs.grid(row=0, column=2, padx=(8, 0))

        self.btn_logs_fullscreen = ctk.CTkButton(
            self.frame_font_controls,
            text="Tela cheia",
            width=90,
            height=24,
            command=self._toggle_logs_fullscreen,
            fg_color=UIConstants.COLOR_SECONDARY,
            hover_color=UIConstants.COLOR_SECONDARY_HOVER
        )
        self.btn_logs_fullscreen.grid(row=0, column=3, padx=(8, 0))
        
        # Legenda dos Logs
        self.lbl_logs_legend = ctk.CTkLabel(
            self.frame_logs_col,
            text=UIConstants.TEXT_LOGS_LEGEND,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_TINY),
            text_color=UIConstants.COLOR_TEXT_HINT,
            anchor="w"
        )
        self.lbl_logs_legend.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        
        # Frame de logs (scrollable)
        self.frame_logs = ctk.CTkFrame(
            self.frame_logs_col,
            fg_color=UIConstants.COLOR_BG_FRAME_LOGS,
            corner_radius=UIConstants.CORNER_RADIUS_LOGS
        )
        self.frame_logs.grid(row=2, column=0, sticky="nsew")
        self.frame_logs.columnconfigure(0, weight=1)
        self.frame_logs.rowconfigure(0, weight=1)
        
        # Textbox para logs (scrollable)
        self.textbox_logs = ctk.CTkTextbox(
            self.frame_logs,
            font=ctk.CTkFont(family=UIConstants.FONT_FAMILY_LOGS, size=UIConstants.LOG_FONT_SIZE_DEFAULT),
            text_color=UIConstants.COLOR_LOG_ERROR,
            fg_color=UIConstants.COLOR_BG_TEXTBOX
        )
        self.textbox_logs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.textbox_logs.configure(state="disabled")  # Read-only
        
        # --- Área de Status e Progresso (dentro do formulário) ---
        self.frame_status = ctk.CTkFrame(
            self.frame_formulario,
            fg_color=UIConstants.COLOR_BG_FRAME,
            corner_radius=UIConstants.CORNER_RADIUS_FRAME
        )
        self.frame_status.grid(
            row=3, column=0, sticky="ew",
            pady=(12, 0)
        )
        self.frame_status.columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(
            self.frame_status,
            textvariable=self.status,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_NORMAL)
        )
        self.lbl_status.grid(row=0, column=0, pady=(12, 8), padx=15)

        self.progress_bar = ctk.CTkProgressBar(
            self.frame_status,
            height=UIConstants.HEIGHT_PROGRESS_BAR
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 8))

        # Label para tempo decorrido e estimado
        self.lbl_tempo = ctk.CTkLabel(
            self.frame_status,
            text="",
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_TINY),
            text_color=UIConstants.COLOR_TEXT_SECONDARY
        )
        self.lbl_tempo.grid(row=2, column=0, pady=(0, 12), padx=15)

        # ============================================================================
        # LINHA 3: BOTÃO CONVERTER (1 coluna, ocupa ambas as colunas)
        # ============================================================================
        self.btn_converter = ctk.CTkButton(
            self.main_frame,
            text=UIConstants.TEXT_BUTTON_CONVERTER,
            command=self._on_gerar,
            height=UIConstants.HEIGHT_BUTTON_LARGE,
            font=ctk.CTkFont(size=UIConstants.FONT_SIZE_BUTTON, weight="bold"),
            fg_color=UIConstants.COLOR_PRIMARY,
            hover_color=UIConstants.COLOR_PRIMARY_HOVER,
            state="disabled"
        )
        self.btn_converter.grid(
            row=3, column=0, columnspan=2, sticky="ew",
            padx=UIConstants.PADDING_FRAME,
            pady=(15, 15)
        )

        # Triggers
        self.cnpj_mapa.trace_add("write", self._on_cnpj_changed)
        self.ano_selecionado.trace_add("write", self._on_campo_changed)
        self.mes_selecionado.trace_add("write", self._on_campo_changed)

    def _verificar_habilitar_botao(self) -> None:
        """Verifica se o formulário está válido e habilita/desabilita o botão."""
        pdf = (self.pdf_path.get() or "").strip()
        cnpj = somente_digitos(self.cnpj_mapa.get())
        mes = self.mes_selecionado.get()
        ano_str = somente_digitos(self.ano_selecionado.get())
        
        # Validações usando FormValidator
        pdf_valido, _ = FormValidator.validar_pdf(pdf)
        cnpj_valido, _ = FormValidator.validar_cnpj(cnpj)
        mes_valido, _, _ = FormValidator.validar_mes(mes)
        ano_valido, _, _ = FormValidator.validar_ano(ano_str)
        
        valid = pdf_valido and cnpj_valido and mes_valido and ano_valido
        
        if valid:
            self.btn_converter.configure(
                state="normal",
                fg_color=UIConstants.COLOR_PRIMARY
            )
        else:
            self.btn_converter.configure(
                state="disabled",
                fg_color=UIConstants.COLOR_DISABLED
            )

    def _on_campo_changed(self, *args) -> None:
        """Callback quando mês ou ano são alterados."""
        self._verificar_habilitar_botao()

    def _buscar_filial_por_cnpj(self) -> None:
        """Busca filial pelo CNPJ digitado."""
        try:
            cnpj = somente_digitos(self.cnpj_mapa.get())
            cnpj_valido, erro_msg = FormValidator.validar_cnpj(cnpj)
            
            if not cnpj_valido:
                if self._log_manager:
                    self._log_manager.adicionar_aviso(f"CNPJ inválido: {cnpj} - {erro_msg}")
                messagebox.showwarning(
                    UIConstants.DIALOG_TITLE_AVISO,
                    UIConstants.TEXT_AVISO_CNPJ_DIGITOS.format(digitos=CNPJ_TAMANHO)
                )
                return
            
            if self._log_manager:
                self._log_manager.adicionar_info(f"Buscando filial com CNPJ: {cnpj}")
            
            nome_filial = self._filiais_manager.buscar_por_cnpj(cnpj)
            if nome_filial:
                if self._log_manager:
                    self._log_manager.adicionar_sucesso(f"Filial encontrada: {nome_filial}")
                self.nome_filial.set(UIConstants.TEXT_INFO_CNPJ_ENCONTRADO.format(nome=nome_filial, cnpj=cnpj))
                # Seleciona no combo também se existir
                opcoes = self.combo_filial.cget("values")
                for opcao in opcoes:
                    if cnpj in opcao:
                        self.filial_selecionada.set(opcao)
                        break
                self._verificar_habilitar_botao()
            else:
                if self._log_manager:
                    self._log_manager.adicionar_aviso(f"CNPJ não encontrado no cadastro de filiais: {cnpj}")
                self.nome_filial.set(UIConstants.TEXT_AVISO_CNPJ_NAO_ENCONTRADO.format(cnpj=cnpj))
                self._verificar_habilitar_botao()
        except Exception as e:
            erro_msg = f"Erro ao buscar filial: {str(e)}"
            if self._log_manager:
                self._log_manager.adicionar_erro(erro_msg)
                self._log_manager.adicionar_debug(f"Traceback: {traceback.format_exc()[:300]}")
            messagebox.showerror("Erro", erro_msg)
    
    def _on_filial_selecionada(self, choice: str) -> None:
        """Callback quando uma filial é selecionada no combo."""
        try:
            if choice and choice != UIConstants.PLACEHOLDER_COMBO_FILIAL:
                # Extrai CNPJ da string formatada: "NOME - CNPJ"
                partes = choice.split(" - ")
                if len(partes) >= 2:
                    cnpj = partes[-1]  # Última parte é o CNPJ
                    nome = " - ".join(partes[:-1])  # Resto é o nome
                    if self._log_manager:
                        self._log_manager.adicionar_info(f"Filial selecionada: {nome} ({cnpj})")
                    self.cnpj_mapa.set(cnpj)
                    self.nome_filial.set(UIConstants.TEXT_INFO_CNPJ_ENCONTRADO.format(nome=nome, cnpj=cnpj))
                else:
                    if self._log_manager:
                        self._log_manager.adicionar_aviso(f"Formato de filial inválido: {choice}")
                    self.nome_filial.set(f"✓ {choice}")
                self._verificar_habilitar_botao()
            else:
                # Se for placeholder ou vazio, limpa campos
                if choice == UIConstants.PLACEHOLDER_COMBO_FILIAL:
                    self.cnpj_mapa.set("")
                self.nome_filial.set("")
                self._verificar_habilitar_botao()
        except Exception as e:
            erro_msg = f"Erro ao processar seleção de filial: {str(e)}"
            if self._log_manager:
                self._log_manager.adicionar_erro(erro_msg)
                self._log_manager.adicionar_debug(f"Traceback: {traceback.format_exc()[:300]}")
            messagebox.showerror("Erro", erro_msg)

    def _on_cnpj_changed(self, *args) -> None:
        """Callback quando CNPJ é alterado no campo."""
        cnpj = somente_digitos(self.cnpj_mapa.get())
        if len(cnpj) > CNPJ_TAMANHO:
            self.cnpj_mapa.set(cnpj[:CNPJ_TAMANHO])
            cnpj = cnpj[:CNPJ_TAMANHO]  # Atualiza a variável local
        
        # Se CNPJ tem CNPJ_TAMANHO dígitos, tenta buscar automaticamente
        if len(cnpj) == CNPJ_TAMANHO:
            nome_filial = self._filiais_manager.buscar_por_cnpj(cnpj)
            if nome_filial:
                self.nome_filial.set(UIConstants.TEXT_INFO_CNPJ_ENCONTRADO.format(nome=nome_filial, cnpj=cnpj))
            else:
                self.nome_filial.set(UIConstants.TEXT_AVISO_CNPJ_NAO_ENCONTRADO.format(cnpj=cnpj))
        
        self._verificar_habilitar_botao()

    def _choose_pdf(self) -> None:
        """Abre diálogo para seleção de arquivo PDF."""
        path = filedialog.askopenfilename(
            title=UIConstants.DIALOG_TITLE_PDF,
            filetypes=UIConstants.FILE_TYPES_PDF,
        )
        if path:
            self.pdf_path.set(path)
            self.status.set(f"Arquivo selecionado: {Path(path).name}")
            self._verificar_habilitar_botao()

    def _on_gerar(self) -> None:
        """Inicia o processamento de conversão do PDF."""
        try:
            # Limpa logs anteriores
            if self._log_manager:
                self._log_manager.limpar()
                self._log_manager.adicionar_banner("INICIO DO PROCESSAMENTO - RPA SIPROQUIM", "SYSTEM")
                self._log_manager.adicionar("Validando formulario...", "STATUS")
            
            # Reseta ajustes para novo processamento
            self._ajustes_por_nf = {}
            self._avisos_gerais = []
            self._total_registros_extraidos = 0
            self._total_nfs_dedup = 0
            self._ultima_estatistica = {}

            pdf = self.pdf_path.get()
            cnpj = somente_digitos(self.cnpj_mapa.get())
            mes_str = self.mes_selecionado.get()
            ano_str = somente_digitos(self.ano_selecionado.get())

            # Validações finais usando FormValidator
            valido, erro_msg, dados = FormValidator.validar_formulario_completo(pdf, cnpj, mes_str, ano_str)
            if not valido:
                if self._log_manager:
                    self._log_manager.adicionar_erro(f"Validação falhou: {erro_msg or UIConstants.TEXT_ERRO_PDF_INVALIDO}")
                messagebox.showerror("Erro", erro_msg or UIConstants.TEXT_ERRO_PDF_INVALIDO)
                return
            
            if self._log_manager:
                self._log_manager.adicionar("Formulario validado com sucesso! [OK]", "STATUS")
                self._log_manager.adicionar(
                    f"ARQUIVO: {Path(dados['pdf']).name}",
                    "CONFIG"
                )
                self._log_manager.adicionar(
                    f"CNPJ: {dados['cnpj']} | PERIODO: {dados['mes_numero']:02d}/{dados['ano_numero']}",
                    "CONFIG"
                )
        except Exception as e:
            erro_msg = f"Erro ao validar formulário: {str(e)}"
            if self._log_manager:
                self._log_manager.adicionar_erro(erro_msg)
                self._log_manager.adicionar_debug(f"Traceback: {traceback.format_exc()[:300]}")
            messagebox.showerror("Erro", erro_msg)
            return

        # Prepara caminhos com nomenclatura: M + ANO + MÊS + CNPJ + NOME_PDF
        saida_dir = downloads_dir()
        nome_pdf = Path(dados['pdf']).name
        nome_saida = gerar_nome_arquivo_saida(
            dados['ano_numero'],
            dados['mes_abreviado'],
            dados['cnpj'],
            nome_pdf=nome_pdf
        )
        saida_path = saida_dir / nome_saida

        # UI Busy State
        self._set_busy(True)
        
        # Thread de processamento
        self._thread_processamento = threading.Thread(
            target=self._run_conversion,
            args=(dados['pdf'], dados['cnpj'], str(saida_path), dados['mes_numero'], dados['ano_numero']),
            daemon=True
        )
        self._thread_processamento.start()

    def _adicionar_log_erro(self, mensagem: str, tipo: str = "ERRO"):
        """Adiciona uma mensagem ao log (deprecated - usar _log_manager)."""
        if self._log_manager:
            self._log_manager.adicionar(mensagem, tipo)

    def _limpar_logs(self):
        """Limpa todos os logs (deprecated - usar _log_manager)."""
        if self._log_manager:
            self._log_manager.limpar()
    
    def _ajustar_fonte_logs(self, delta: int) -> None:
        """Ajusta o tamanho da fonte do log para melhor visualização."""
        if self._log_manager:
            self._log_manager.ajustar_fonte(delta)

    def _exportar_logs(self) -> None:
        """Exporta os logs para um arquivo .txt."""
        if not self._log_manager:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_padrao = f"logs_siproquim_{timestamp}.txt"
        caminho = filedialog.asksaveasfilename(
            title="Exportar logs",
            defaultextension=".txt",
            initialfile=nome_padrao,
            filetypes=[("Arquivo de texto", "*.txt")]
        )
        if caminho:
            self._log_manager.exportar(caminho)
            self._log_manager.adicionar_info(f"Logs exportados para: {caminho}")

    def _toggle_logs_fullscreen(self) -> None:
        """Alterna o modo de tela cheia dos logs."""
        if self._logs_fullscreen:
            self._sair_logs_fullscreen()
        else:
            self._entrar_logs_fullscreen()

    def _entrar_logs_fullscreen(self) -> None:
        """Expande a coluna de logs para ocupar todo o layout."""
        if self._logs_fullscreen or not self.frame_logs_col:
            return

        self.update_idletasks()
        self._logs_fullscreen = True
        if self.btn_logs_fullscreen:
            self.btn_logs_fullscreen.configure(text="Voltar")

        # Esconde outros blocos para liberar espaco total
        self.lbl_titulo.grid_remove()
        self.lbl_subtitulo.grid_remove()
        self.frame_formulario.grid_remove()
        self.btn_converter.grid_remove()

        # Ajusta grid principal para fullscreen
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=0)
        self.main_frame.grid_rowconfigure(2, weight=0)
        self.main_frame.grid_rowconfigure(3, weight=0)
        self.main_frame.grid_columnconfigure(0, weight=1, minsize=0)
        self.main_frame.grid_columnconfigure(1, weight=1, minsize=0)

        # Move logs para ocupar toda a area
        self.frame_logs_col.grid_forget()
        self.frame_logs_col.grid(
            row=0, column=0, rowspan=4, columnspan=2,
            sticky="nsew", padx=0, pady=0
        )
        self.frame_logs_col.rowconfigure(2, weight=1)
        self.frame_logs_col.columnconfigure(0, weight=1)
        self.frame_logs_col.lift()
        self.textbox_logs.focus_set()

    def _sair_logs_fullscreen(self) -> None:
        """Restaura o layout normal dos logs."""
        if not self._logs_fullscreen or not self.frame_logs_col:
            return

        self.update_idletasks()
        self._logs_fullscreen = False
        if self.btn_logs_fullscreen:
            self.btn_logs_fullscreen.configure(text="Tela cheia")

        # Restaura grid principal
        self.main_frame.grid_rowconfigure(0, weight=0)
        self.main_frame.grid_rowconfigure(1, weight=0)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=0)
        self.main_frame.grid_columnconfigure(0, weight=1, minsize=500)
        self.main_frame.grid_columnconfigure(1, weight=1, minsize=400)

        # Restaura logs para posicao original (grid explicito)
        self.frame_logs_col.grid_forget()
        self.frame_logs_col.grid(
            row=2, column=1, sticky="nsew",
            padx=(15, UIConstants.PADDING_FRAME), pady=(0, 0)
        )

        # Restaura outros blocos (grid explicito)
        self.lbl_titulo.grid(row=0, column=0, columnspan=2, pady=(15, 5), sticky="n")
        self.lbl_subtitulo.grid(row=1, column=0, columnspan=2, pady=(0, 15), sticky="n")
        self.frame_formulario.grid(
            row=2, column=0, sticky="nsew",
            padx=(UIConstants.PADDING_FRAME, 15), pady=(0, 0)
        )
        self.btn_converter.grid(
            row=3, column=0, columnspan=2, sticky="ew",
            padx=UIConstants.PADDING_FRAME, pady=(15, 15)
        )
        self.update_idletasks()

    def _animar_logs(self, inicio, fim, passos: int = 10, duracao_ms: int = 160, ao_final=None) -> None:
        """Anima a transiÃ§Ã£o do frame de logs."""
        if self._logs_animando:
            return
        self._logs_animando = True
        try:
            x0, y0, w0, h0 = inicio
            x1, y1, w1, h1 = fim
        except Exception:
            self._logs_animando = False
            if ao_final:
                ao_final()
            return

        if passos <= 0:
            passos = 1
        intervalo = max(10, int(duracao_ms / passos))

        def step(i: int):
            if not self._logs_animando:
                return
            t = i / passos
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            w = int(w0 + (w1 - w0) * t)
            h = int(h0 + (h1 - h0) * t)
            self.frame_logs_col.place(x=x, y=y, width=w, height=h)
            if i < passos:
                self.after(intervalo, lambda: step(i + 1))
            else:
                self._logs_animando = False
                if ao_final:
                    ao_final()

        step(1)

    def _formatar_barra_progresso(self, progresso: float, largura: int = 20) -> str:
        """Formata uma barra de progresso textual."""
        try:
            progresso = float(progresso)
        except (TypeError, ValueError):
            progresso = 0.0
        progresso = max(0.0, min(1.0, progresso))
        cheios = int(progresso * largura)
        if progresso >= 1.0:
            cheios = largura
        vazios = max(0, largura - cheios)
        return f"[{'#' * cheios}{'-' * vazios}]"

    def _formatar_check(self, label: str, valor: str, largura: int = 32) -> str:
        """Formata linhas do relatorio final com alinhamento pontilhado."""
        base = f"{label}:"
        if len(base) >= largura:
            return f"{base} {valor}"
        pontos = "." * (largura - len(base))
        return f"{base}{pontos} {valor}"

    def _normalizar_texto(self, texto: str) -> str:
        """Remove acentos e normaliza texto para classificacao."""
        texto = texto or ""
        texto = unicodedata.normalize("NFD", texto.lower())
        return "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")

    def _limpar_prefixo_mensagem(self, mensagem: str, nf: Optional[str] = None) -> str:
        """Remove prefixos padrao e o prefixo NF de mensagens."""
        msg = (mensagem or "").strip()
        if nf:
            prefixo_nf = f"NF {nf}:"
            if msg.startswith(prefixo_nf):
                msg = msg[len(prefixo_nf):].strip()
        for prefixo in ("AVISO:", "ALERTA:", "ATENCAO:", "ATENÇÃO:", "WARNING:", "WARN:"):
            if msg.upper().startswith(prefixo):
                msg = msg[len(prefixo):].strip()
        return msg

    def _classificar_ajuste(self, mensagem: str) -> dict:
        """Classifica um ajuste para resumo do analista."""
        detalhe = " ".join((mensagem or "").split())
        texto = self._normalizar_texto(detalhe)

        tipo = "REVISAO"
        acao = "Verifique e ajuste manualmente no TXT, se necessario."

        if "recebedor suspeito" in texto:
            tipo = "RECEBEDOR"
            acao = "Verifique o recebedor e ajuste se necessario."
        elif "contratante" in texto and "igual ao" in texto and "destino" in texto:
            tipo = "REGRA NEGOCIO"
            acao = "Valide se o SIPROQUIM aceita operacao para o mesmo CNPJ."
        elif "cpf" in texto and "ao inves de cnpj" in texto:
            tipo = "CPF DETECTADO"
            acao = "Substitua por um CNPJ valido no TXT."
        elif "cpf" in texto and "nao passa" in texto and "cnpj" in texto:
            tipo = "VALIDACAO"
            acao = "SIPROQUIM pode rejeitar; substitua por CNPJ valido."
        elif "cpf" in texto and "invalido" in texto:
            tipo = "CPF INVALIDO"
            acao = "Corrija o CPF no TXT."
        elif "cnpj" in texto and "invalido" in texto:
            tipo = "CNPJ INVALIDO"
            acao = "Corrija o CNPJ no TXT."
        elif "tamanho" in texto and "digito" in texto:
            tipo = "DOCUMENTO"
            acao = "Corrija o documento no TXT."
        elif "nome" in texto and "vazio" in texto:
            tipo = "DADO AUSENTE"
            acao = "Preencha manualmente no TXT."
        elif "documento" in texto and "vazio" in texto:
            tipo = "DADO AUSENTE"
            acao = "Preencha manualmente no TXT."
        elif "sem nome" in texto:
            tipo = "DADO AUSENTE"
            acao = "Preencha o nome manualmente."
        elif "linha cc" in texto and "nao gerada" in texto:
            tipo = "CTE"
            acao = "Verifique os dados do CTe no PDF."

        return {"tipo": tipo, "detalhe": detalhe, "acao": acao}

    def _normalizar_log_processador(self, tipo: str, mensagem: str) -> Optional[tuple]:
        """Normaliza logs do processador para reduzir ruído e melhorar layout."""
        if not mensagem:
            return None
        msg = mensagem.strip()
        tipo_norm = (tipo or "INFO").upper()

        # Suprime avisos que serão agrupados no resumo manual
        if tipo_norm in ("ACAO_NECESSARIA", "ATENCAO", "ALERTA"):
            return None

        # Suprime separadores e relatorios duplicados do processador
        if msg.startswith("="):
            return None
        msg_norm = self._normalizar_texto(msg)
        relatorio_prefixos = (
            "relatorio final",
            "total de registros processados",
            "registros corrigidos",
            "registros com erros",
            "total de erros encontrados",
            "ajustes manuais necessarios",
            "total exportado para txt",
        )
        if any(msg_norm.startswith(prefixo) for prefixo in relatorio_prefixos):
            return None

        if "validacao robusta" in msg_norm or "sistema de validacao" in msg_norm:
            return None

        if msg_norm.startswith("estrutura do pdf validada"):
            return ("STATUS", "Estrutura do PDF validada... [OK]")

        if tipo_norm == "CRITICO":
            tipo_norm = "ERRO"
        if tipo_norm == "VALIDACAO":
            tipo_norm = "INFO"
        if tipo_norm not in UIConstants.LOG_TIPOS:
            tipo_norm = "INFO"

        return (tipo_norm, msg)

    def _registrar_ajuste(self, nf: Optional[str], tipo: str, mensagem: str) -> None:
        """Armazena ajustes para resumo final da analista."""
        if not mensagem:
            return
        if nf and nf not in ("N/A", "NA"):
            chave = str(nf)
            msg = self._limpar_prefixo_mensagem(mensagem, chave)
            info = self._classificar_ajuste(msg)
            if info.get("tipo") == "REVISAO" and tipo:
                info["tipo"] = tipo.replace("_", " ").strip()
            self._ajustes_por_nf.setdefault(chave, [])
            if info not in self._ajustes_por_nf[chave]:
                self._ajustes_por_nf[chave].append(info)
        else:
            msg = self._limpar_prefixo_mensagem(mensagem, None)
            if msg and msg not in self._avisos_gerais:
                self._avisos_gerais.append(msg)

    def _log_resumo_analista(self) -> None:
        """Exibe um resumo final para a analista."""
        if not self._log_manager:
            return
        total_nfs = len(self._ajustes_por_nf)

        if total_nfs == 0:
            self._log_manager.adicionar_banner("REVISAO MANUAL", "CHECK")
            self._log_manager.adicionar_sucesso("Nenhum ajuste manual detectado.")
            return

        self._log_manager.adicionar("-" * 80, "SYSTEM")
        self._log_manager.adicionar(
            f"REVISAO MANUAL NECESSARIA - {total_nfs} NOTAS COM PENDENCIAS",
            "AVISO"
        )
        self._log_manager.adicionar("-" * 80, "SYSTEM")

        if total_nfs > 0:
            def _key_nf(x):
                return int(x) if x.isdigit() else x

            linhas = []
            for nf in sorted(self._ajustes_por_nf.keys(), key=_key_nf):
                itens = self._ajustes_por_nf[nf]
                if not itens:
                    continue
                primeiro = itens[0]
                tipo_pri = primeiro.get("tipo", "REVISAO")
                detalhe_pri = primeiro.get("detalhe", "")
                linhas.append(f"NF {nf:<6} [{tipo_pri}] {detalhe_pri}")

                for item in itens[1:]:
                    tipo = item.get("tipo", "REVISAO")
                    detalhe = item.get("detalhe", "")
                    linhas.append(f"          [{tipo}] {detalhe}")

                acoes = [item.get("acao") for item in itens if item.get("acao")]
                acoes_unicas = []
                for acao in acoes:
                    if acao and acao not in acoes_unicas:
                        acoes_unicas.append(acao)
                if acoes_unicas:
                    linhas.append(f"          > ACAO: {' | '.join(acoes_unicas)}")

            if linhas:
                self._log_manager.adicionar("\n".join(linhas), "INFO")

    def _log_relatorio_final(self) -> None:
        """Exibe o relatorio final com os principais indicadores."""
        if not self._log_manager:
            return

        stats = self._ultima_estatistica or {}
        total_aprovados = stats.get('total_aprovados')
        if total_aprovados is None:
            total_aprovados = self._total_nfs_dedup or 0
        total_corrigidos = stats.get('total_corrigidos', 0)
        total_com_erros = stats.get('total_com_erros', 0)
        total_criticos = stats.get('total_com_erros_criticos', 0)
        total_ajustes = stats.get('total_ajustes_manuais', 0)

        if total_criticos > 0:
            status_final = "FALHA (Erros criticos)"
        elif total_ajustes > 0 or total_com_erros > 0:
            status_final = "SUCESSO (Com ressalvas)"
        else:
            status_final = "SUCESSO"

        self._log_manager.adicionar_banner("FINALIZACAO DO PROCESSO", "RELATORIO")
        self._log_manager.adicionar(
            f"Status Final: {status_final} | Total: {total_aprovados} NFs",
            "CHECK"
        )
        self._log_manager.adicionar(self._formatar_check("Total Processado", str(total_aprovados)), "CHECK")
        self._log_manager.adicionar(self._formatar_check("Ajustes Automaticos", str(total_corrigidos)), "CHECK")
        self._log_manager.adicionar(self._formatar_check("Ajustes Manuais", str(total_ajustes)), "CHECK")
        self._log_manager.adicionar(self._formatar_check("Erros Criticos", str(total_criticos)), "CHECK")
        self._log_manager.adicionar(self._formatar_check("Total Exportado", str(total_aprovados)), "CHECK")

        if self._avisos_gerais:
            self._log_manager.adicionar("Avisos gerais:", "ALERTA")
            for aviso in self._avisos_gerais:
                self._log_manager.adicionar(aviso, "ALERTA")

    def _run_conversion(self, pdf, cnpj, saida_path, mes, ano):
        """Executa a conversao do PDF em thread separada."""
        try:
            self.after(0, lambda: self._log_manager.adicionar("Iniciando processamento...", "SYSTEM"))

            # Callback de progresso para atualizar UI
            def callback_progresso(etapa, detalhes):
                try:
                    if etapa == 'abrir':
                        arquivo = detalhes.get('arquivo', '')
                        self.after(0, lambda: self._atualizar_status('Abrindo PDF...', arquivo))
                        self.after(0, lambda: self._log_manager.adicionar(f"Abrindo PDF: {arquivo}", "STATUS"))
                    elif etapa == 'extrair':
                        pagina_atual = detalhes.get('pagina_atual', 0)
                        total_paginas = detalhes.get('total_paginas', 0)
                        self._progress_manager.total_paginas = total_paginas
                        self._progress_manager.pagina_atual = pagina_atual
                        progresso = self._progress_manager.calcular_progresso_extracao(pagina_atual, total_paginas)
                        self.after(0, lambda: self._atualizar_progresso_extracao(pagina_atual, total_paginas, progresso))

                        if self._progress_manager.deve_logar_pagina(pagina_atual, total_paginas):
                            barra = self._formatar_barra_progresso(progresso)
                            percentual = int(progresso * 100)
                            msg = f"Extraindo dados: {barra} {percentual}% (Pag {pagina_atual}/{total_paginas})"
                            self.after(0, lambda m=msg: self._log_manager.adicionar(m, "PROGRESSO"))
                    elif etapa == 'deduplicar':
                        total = detalhes.get('total_registros', 0)
                        total_nfs = detalhes.get('total_nfs', 0)
                        self._total_registros_extraidos = total
                        self._total_nfs_dedup = total_nfs
                        self.after(0, lambda: self._atualizar_status('Deduplicando registros...', f'{total} registros encontrados'))
                        self.after(0, lambda: self.progress_bar.set(UIConstants.PROGRESSO_DEDUPLICAR))
                        self.after(0, lambda: self._log_manager.adicionar(
                            f"Registros encontrados: {total} | Apos deduplicacao: {total_nfs}",
                            "INFO"
                        ))
                    elif etapa == 'processar':
                        if 'total_registros' in detalhes:
                            total = detalhes.get('total_registros', 0)
                            self.after(0, lambda: self._log_manager.adicionar(f"Validando {total} registros...", "STATUS"))
                            self.after(0, lambda: self._log_manager.adicionar(
                                "Aplicando Validacao Robusta (CHECKSUM + INTEGRIDADE)",
                                "INFO"
                            ))
                        else:
                            self._ultima_estatistica = {
                                'total_aprovados': detalhes.get('total_aprovados'),
                                'total_corrigidos': detalhes.get('total_corrigidos', 0),
                                'total_com_erros': detalhes.get('total_com_erros', 0),
                                'total_com_erros_criticos': detalhes.get('total_com_erros_criticos', 0),
                                'total_ajustes_manuais': detalhes.get('total_ajustes_manuais', 0),
                            }
                            ajustes = self._ultima_estatistica.get('total_ajustes_manuais', 0)
                            self.after(0, lambda: self._log_manager.adicionar(
                                f"Validacao concluida. Ajustes manuais: {ajustes}",
                                "STATUS"
                            ))
                    elif etapa == 'gerar':
                        total_nfs = detalhes.get('total_nfs', 0)
                        self.after(0, lambda: self._atualizar_status('Gerando arquivo TXT...', f'{total_nfs} NFs unicas'))
                        self.after(0, lambda: self.progress_bar.set(UIConstants.PROGRESSO_GERAR))
                        self.after(0, lambda: self._log_manager.adicionar(
                            f"Gerando TXT com {total_nfs} NFs unicas...",
                            "STATUS"
                        ))
                    elif etapa == 'aviso':
                        mensagem = detalhes.get('mensagem', '')
                        tipo = detalhes.get('tipo', 'AVISO')
                        if mensagem:
                            if tipo in ('ERRO', 'CRITICO'):
                                self.after(0, lambda: self._log_manager.adicionar_erro(mensagem))
                            elif tipo in ('ATENCAO', 'ACAO', 'ACAO_NECESSARIA', 'ALERTA'):
                                self._registrar_ajuste(None, tipo, mensagem)
                            else:
                                self.after(0, lambda: self._log_manager.adicionar(mensagem, "INFO"))
                    elif etapa == 'ajuste_manual':
                        nf = detalhes.get('nf')
                        tipo = detalhes.get('tipo', 'AVISO')
                        mensagem = detalhes.get('mensagem', '')
                        self._registrar_ajuste(nf, tipo, mensagem)
                    elif etapa == 'processar_log':
                        mensagem = detalhes.get('mensagem', '')
                        tipo = detalhes.get('tipo', 'INFO')
                        normalizado = self._normalizar_log_processador(tipo, mensagem)
                        if normalizado:
                            tipo_norm, msg_norm = normalizado
                            if tipo_norm == 'ERRO':
                                self.after(0, lambda: self._log_manager.adicionar_erro(msg_norm))
                            elif tipo_norm == 'SUCESSO':
                                self.after(0, lambda: self._log_manager.adicionar_sucesso(msg_norm))
                            elif tipo_norm in ('AVISO', 'ALERTA', 'ATENCAO', 'ACAO_NECESSARIA'):
                                self.after(0, lambda: self._log_manager.adicionar_aviso(msg_norm))
                            else:
                                self.after(0, lambda: self._log_manager.adicionar(msg_norm, tipo_norm))
                    elif etapa == 'finalizar':
                        self.after(0, lambda: self.progress_bar.set(UIConstants.PROGRESSO_COMPLETO))
                except Exception as e:
                    self.after(0, lambda: self._log_manager.adicionar_erro(f"Erro no callback: {str(e)}"))

            # Processa o PDF
            caminho_final = processar_pdf(
                pdf, cnpj, saida_path,
                callback_progresso=callback_progresso,
                mes=mes, ano=ano
            )
            self.after(0, self._log_resumo_analista)
            self.after(0, self._log_relatorio_final)
            self.after(0, lambda: self._log_manager.adicionar("Processamento concluido com sucesso!", "SUCESSO"))
            self.after(0, lambda: self._log_manager.adicionar(f"ARQUIVO GERADO: {caminho_final}", "EXPORT"))
            self.after(0, lambda: self._log_manager.adicionar("=" * 60, "SYSTEM"))
            self.after(0, lambda: self._on_sucesso(caminho_final))

        except FileNotFoundError as e:
            erro_msg = f"Arquivo nao encontrado: {str(e)}"
            self.after(0, lambda: self._log_manager.adicionar_erro(erro_msg))
            self.after(0, lambda: self._on_erro(erro_msg))
        except ValueError as e:
            erro_msg = f"Erro de validacao: {str(e)}"
            self.after(0, lambda: self._log_manager.adicionar_erro(erro_msg))
            self.after(0, lambda: self._on_erro(erro_msg))
        except Exception as e:
            erro_completo = traceback.format_exc()
            erro_msg = f"Erro inesperado: {str(e)}"
            self.after(0, lambda: self._log_manager.adicionar_erro(erro_msg))
            self.after(0, lambda: self._log_manager.adicionar_erro("=" * 60))
            self.after(0, lambda: self._log_manager.adicionar_debug(f"Detalhes do erro:"))
            # Divide o traceback em linhas para melhor legibilidade
            linhas_traceback = erro_completo.split('\n')
            for linha in linhas_traceback[:15]:
                if linha.strip():
                    self.after(0, lambda l=linha: self._log_manager.adicionar_debug(f"  {l}"))
            if len(linhas_traceback) > 15:
                self.after(0, lambda: self._log_manager.adicionar_debug(
                    f"  ... ({len(linhas_traceback) - 15} linhas omitidas)"
                ))
            self.after(0, lambda: self._log_manager.adicionar_erro("=" * 60))
            self.after(0, lambda: self._log_manager.adicionar("Verifique os logs acima para mais detalhes.", "INFO"))
            self.after(0, lambda: self._on_erro(erro_msg))

    def _atualizar_progresso_extracao(self, pagina_atual, total_paginas, progresso):
        """Atualiza progresso durante extração de páginas."""
        self.progress_bar.set(progresso)
        
        # Calcula tempo decorrido e estimado usando ProgressManager
        tempo_decorrido = self._progress_manager.obter_tempo_decorrido()
        if tempo_decorrido is not None:
            tempo_restante = self._progress_manager.estimar_tempo_restante(pagina_atual, total_paginas)
            
            if tempo_restante is not None:
                tempo_decorrido_str = self._progress_manager.formatar_tempo(tempo_decorrido)
                tempo_restante_str = self._progress_manager.formatar_tempo(tempo_restante)
                
                self.lbl_tempo.configure(
                    text=f"Página {pagina_atual}/{total_paginas} | "
                         f"Tempo: {tempo_decorrido_str} | "
                         f"Estimado restante: {tempo_restante_str}"
                )
                self.status.set(f"Extraindo dados... Página {pagina_atual} de {total_paginas}")
            else:
                tempo_decorrido_str = self._progress_manager.formatar_tempo(tempo_decorrido)
                self.lbl_tempo.configure(text=f"Tempo decorrido: {tempo_decorrido_str}")
    
    def _atualizar_status(self, acao, detalhes=""):
        """Atualiza mensagem de status."""
        if detalhes:
            self.status.set(f"{acao} {detalhes}")
        else:
            self.status.set(acao)

    def _on_sucesso(self, caminho: str) -> None:
        """Callback chamado quando conversão é concluída com sucesso."""
        self._set_busy(False)
        
        # Calcula tempo total usando ProgressManager
        tempo_total = self._progress_manager.obter_tempo_decorrido()
        if tempo_total is not None:
            tempo_str = self._progress_manager.formatar_tempo(tempo_total)
            self.status.set(f"✅ Conversão concluída em {tempo_str}!")
            self.lbl_tempo.configure(text=f"Tempo total: {tempo_str}")
        else:
            self.status.set(UIConstants.TEXT_SUCESSO_CONVERSAO)
        
        self.progress_bar.set(UIConstants.PROGRESSO_COMPLETO)

        caminho_abs = Path(caminho).absolute()
        msg = f"{UIConstants.TEXT_SUCESSO_ARQUIVO_SALVO}\n{caminho_abs}\n\n{UIConstants.TEXT_SUCESSO_ABRIR_DOWNLOADS}"
        
        if messagebox.askyesno(UIConstants.DIALOG_TITLE_SUCESSO, msg):
            try:
                os.startfile(downloads_dir())
            except:
                subprocess.run(["explorer", str(downloads_dir())])

    def _on_erro(self, erro: str) -> None:
        """Callback chamado quando ocorre erro na conversão."""
        self._set_busy(False)
        self.status.set(UIConstants.TEXT_ERRO_CONVERSAO)
        self.progress_bar.set(0)
        self.lbl_tempo.configure(text="")
        
        # Mostra mensagem de erro
        msg_completa = UIConstants.TEXT_ERRO_DETALHES.format(erro=erro)
        messagebox.showerror(UIConstants.DIALOG_TITLE_ERRO, msg_completa)

    def _set_busy(self, busy: bool):
        """Define o estado de processamento (busy/ocioso)."""
        self._is_busy = busy
        if busy:
            self.btn_converter.configure(state="disabled", text=UIConstants.TEXT_BUTTON_PROCESSANDO)
            self.btn_buscar.configure(state="disabled")
            self.entry_cnpj.configure(state="disabled")
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(UIConstants.PROGRESSO_INICIAL)
            self._progress_manager.iniciar()
            self.lbl_tempo.configure(text=UIConstants.TEXT_STATUS_INICIANDO)
            self.status.set(UIConstants.TEXT_STATUS_ABRINDO_PDF)
        else:
            self.btn_converter.configure(state="normal", text=UIConstants.TEXT_BUTTON_CONVERTER)
            self.btn_buscar.configure(state="normal")
            self.entry_cnpj.configure(state="normal")
            self.progress_bar.set(UIConstants.PROGRESSO_COMPLETO)
            self._progress_manager.finalizar()
            self._verificar_habilitar_botao()
