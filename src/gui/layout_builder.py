"""
Builder da interface institucional da Rodogarcia.
"""

from __future__ import annotations

import traceback
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from .constants import UIConstants


def _font(size: int, weight: str = "normal", family: str | None = None) -> ctk.CTkFont:
    return ctk.CTkFont(
        family=family or UIConstants.FONT_FAMILY_TEXT,
        size=size,
        weight=weight,
    )


def _input_kwargs() -> dict:
    return {
        "height": UIConstants.HEIGHT_ENTRY,
        "corner_radius": UIConstants.CORNER_RADIUS_BUTTON,
        "fg_color": "transparent",
        "border_color": UIConstants.COLOR_BORDER_STRONG,
        "border_width": 2,
        "text_color": UIConstants.COLOR_TEXT_PRIMARY,
        "placeholder_text_color": UIConstants.COLOR_TEXT_HINT,
        "font": _font(UIConstants.FONT_SIZE_NORMAL),
    }


def _secondary_button_kwargs() -> dict:
    return {
        "height": UIConstants.HEIGHT_BUTTON_SMALL,
        "fg_color": "transparent",
        "hover_color": UIConstants.COLOR_BG_BADGE_NEUTRAL,
        "border_width": 2,
        "border_color": UIConstants.COLOR_PRIMARY,
        "text_color": UIConstants.COLOR_PRIMARY,
        "font": _font(UIConstants.FONT_SIZE_SMALL, "bold"),
    }


def _combo_kwargs() -> dict:
    return {
        "height": UIConstants.HEIGHT_ENTRY,
        "corner_radius": UIConstants.CORNER_RADIUS_BUTTON,
        "fg_color": "transparent",
        "border_color": UIConstants.COLOR_BORDER_STRONG,
        "border_width": 2,
        "button_color": "transparent",
        "button_hover_color": UIConstants.COLOR_BORDER,
        "text_color": UIConstants.COLOR_TEXT_PRIMARY,
        "dropdown_fg_color": UIConstants.COLOR_BG_FRAME,
        "dropdown_hover_color": UIConstants.COLOR_BG_SURFACE_ALT,
        "dropdown_text_color": UIConstants.COLOR_TEXT_PRIMARY,
        "font": _font(UIConstants.FONT_SIZE_NORMAL),
        "dropdown_font": _font(UIConstants.FONT_SIZE_NORMAL),
    }


def _badge(parent, texto: str, fg_color: str, text_color: str):
    return ctk.CTkLabel(
        parent,
        text=texto,
        fg_color=fg_color,
        text_color=text_color,
        corner_radius=UIConstants.CORNER_RADIUS_BADGE,
        font=_font(UIConstants.FONT_SIZE_BADGE, "bold"),
        padx=12,
        pady=6,
    )


def _field_panel(parent, titulo: str, descricao: str | None = None):
    card = ctk.CTkFrame(
        parent,
        fg_color=UIConstants.COLOR_BG_FIELD_PANEL,
        border_width=2,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=18,
    )
    card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        card,
        text=titulo,
        font=_font(UIConstants.FONT_SIZE_SMALL, "bold"),
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        anchor="w",
    ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))

    if descricao:
        ctk.CTkLabel(
            card,
            text=descricao,
            font=_font(UIConstants.FONT_SIZE_TINY),
            text_color=UIConstants.COLOR_TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=300,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

    content = ctk.CTkFrame(card, fg_color="transparent")
    content.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
    content.grid_columnconfigure(0, weight=1)
    return card, content


def _metric_card(parent, titulo: str, cor_indicador: str, detalhe: str):
    card = ctk.CTkFrame(
        parent,
        fg_color=UIConstants.COLOR_BG_FRAME,
        border_width=2,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=UIConstants.CORNER_RADIUS_FRAME,
    )
    card.grid_columnconfigure(0, weight=1)

    topo = ctk.CTkFrame(card, fg_color="transparent")
    topo.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
    topo.grid_columnconfigure(1, weight=1)

    indicador = ctk.CTkFrame(topo, width=10, height=10, fg_color=cor_indicador, corner_radius=999)
    indicador.grid(row=0, column=0, sticky="w", padx=(0, 10))
    indicador.grid_propagate(False)

    ctk.CTkLabel(
        topo,
        text=titulo,
        font=_font(UIConstants.FONT_SIZE_TINY, "bold"),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    ).grid(row=0, column=1, sticky="w")

    valor_lbl = ctk.CTkLabel(
        card,
        text="0",
        font=_font(UIConstants.FONT_SIZE_METRIC, "bold"),
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        anchor="w",
    )
    valor_lbl.grid(row=1, column=0, sticky="w", padx=18)

    detalhe_lbl = ctk.CTkLabel(
        card,
        text=detalhe,
        font=_font(UIConstants.FONT_SIZE_TINY),
        text_color=UIConstants.COLOR_TEXT_HINT,
        anchor="w",
        justify="left",
    )
    detalhe_lbl.grid(row=2, column=0, sticky="w", padx=18, pady=(2, 16))

    return card, valor_lbl, detalhe_lbl


def _load_logo(app):
    logo_path = Path(__file__).resolve().parents[2] / "public" / "logo.png"
    if not logo_path.exists():
        return None

    try:
        with Image.open(logo_path) as imagem_logo:
            logo_copia = imagem_logo.copy()
        app._ui_images["logo"] = ctk.CTkImage(
            light_image=logo_copia,
            dark_image=logo_copia,
            size=(214, 40),
        )
        return app._ui_images["logo"]
    except Exception:
        return None


def setup_ui(app) -> None:
    """Monta a interface principal com a identidade da Rodogarcia."""
    app.configure(fg_color=UIConstants.COLOR_BG_APP)
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(0, weight=1)

    app.main_frame = ctk.CTkScrollableFrame(
        app,
        fg_color="transparent",
        corner_radius=0,
        border_width=0,
    )
    app.main_frame.grid(row=0, column=0, sticky="nsew")
    app.main_frame.grid_columnconfigure(0, weight=1)

    app.container = ctk.CTkFrame(app.main_frame, fg_color="transparent")
    app.container.grid(row=0, column=0, sticky="nsew", padx=UIConstants.PADDING_MAIN, pady=UIConstants.PADDING_MAIN)
    app.container.grid_columnconfigure(0, weight=1)

    app.header_card = ctk.CTkFrame(
        app.container,
        fg_color=UIConstants.COLOR_BG_FRAME,
        border_width=2,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=UIConstants.CORNER_RADIUS_HEADER,
    )
    app.header_card.grid(row=0, column=0, sticky="ew", pady=(0, 20))
    app.header_card.grid_columnconfigure(1, weight=1)

    app.logo_image = _load_logo(app)
    app.header_logo_wrap = ctk.CTkFrame(app.header_card, fg_color="transparent")
    app.header_logo_wrap.grid(row=0, column=0, sticky="w", padx=(22, 14), pady=10)
    if app.logo_image:
        app.lbl_logo = ctk.CTkLabel(app.header_logo_wrap, text="", image=app.logo_image)
    else:
        app.lbl_logo = ctk.CTkLabel(app.header_logo_wrap, text="RODOGARCIA", font=_font(20, "bold"), text_color=UIConstants.COLOR_PRIMARY)
    app.lbl_logo.grid(row=0, column=0, sticky="w")

    app.header_content = ctk.CTkFrame(app.header_card, fg_color="transparent")
    app.header_content.grid(row=0, column=1, sticky="nsew", padx=14, pady=10)
    app.header_content.grid_columnconfigure(0, weight=1)

    app.header_kicker = _badge(
        app.header_content,
        UIConstants.TEXT_HEADER_KICKER,
        UIConstants.COLOR_BG_BADGE_NEUTRAL,
        UIConstants.COLOR_PRIMARY,
    )
    app.header_kicker.grid(row=0, column=0, sticky="w")

    app.lbl_titulo = ctk.CTkLabel(
        app.header_content,
        text=UIConstants.TEXT_TITLE,
        font=_font(UIConstants.FONT_SIZE_TITLE, "bold", UIConstants.FONT_FAMILY_TITLE),
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        anchor="w",
    )
    app.lbl_titulo.grid(row=1, column=0, sticky="w", pady=(6, 0))

    app.lbl_subtitulo = ctk.CTkLabel(
        app.header_content,
        text=UIConstants.TEXT_SUBTITLE,
        font=_font(UIConstants.FONT_SIZE_SUBTITLE),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
        justify="left",
        wraplength=760,
    )
    app.lbl_subtitulo.grid(row=2, column=0, sticky="w", pady=(2, 0))

    app.header_tools = ctk.CTkFrame(
        app.header_card,
        fg_color=UIConstants.COLOR_BG_SURFACE_ALT,
        border_width=2,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=16,
    )
    app.header_tools.grid(row=0, column=2, sticky="ne", padx=(10, 16), pady=10)

    ctk.CTkLabel(
        app.header_tools,
        text=UIConstants.TEXT_THEME_LABEL,
        font=_font(UIConstants.FONT_SIZE_TINY, "bold"),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

    app.theme_toggle = ctk.CTkSegmentedButton(
        app.header_tools,
        values=UIConstants.THEME_OPTIONS,
        command=app._on_theme_change,
        fg_color=UIConstants.COLOR_BG_BADGE_NEUTRAL,
        selected_color=UIConstants.COLOR_BORDER_STRONG,
        selected_hover_color=UIConstants.COLOR_BORDER,
        unselected_color=UIConstants.COLOR_BG_BADGE_NEUTRAL,
        unselected_hover_color=UIConstants.COLOR_BG_SURFACE_ALT,
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        font=_font(UIConstants.FONT_SIZE_SMALL, "bold"),
        corner_radius=12,
        height=32,
        width=180,
    )
    app.theme_toggle.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
    app.theme_toggle.set(app.theme_choice.get())

    app.frame_logs_col = ctk.CTkFrame(
        app.container,
        fg_color="transparent",
        border_width=0,
    )
    app.grid_principal = ctk.CTkFrame(
        app.container,
        fg_color="transparent",
        corner_radius=0,
        border_width=0,
    )
    app.grid_principal.grid(row=1, column=0, sticky="nsew")
    app.grid_principal.grid_columnconfigure(0, weight=1)
    app.grid_principal.grid_columnconfigure(1, weight=1)

    app.left_column = ctk.CTkFrame(app.grid_principal, fg_color="transparent")
    app.left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    app.left_column.grid_columnconfigure(0, weight=1)

    app.right_column = ctk.CTkFrame(app.grid_principal, fg_color="transparent")
    app.right_column.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    app.right_column.grid_columnconfigure(0, weight=1)

    app.controls_card = ctk.CTkFrame(
        app.left_column,
        fg_color=UIConstants.COLOR_BG_FRAME,
        border_width=2,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=UIConstants.CORNER_RADIUS_FRAME,
    )
    app.controls_card.grid(row=0, column=0, sticky="ew")
    app.controls_card.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        app.controls_card,
        text="Controles de execucao",
        font=_font(UIConstants.FONT_SIZE_HEADING, "bold"),
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        anchor="w",
    ).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 4))

    ctk.CTkLabel(
        app.controls_card,
        text="Selecione o PDF, defina a filial e o periodo do mapa antes de iniciar a conversao.",
        font=_font(UIConstants.FONT_SIZE_SMALL),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 16))

    app.controls_grid = ctk.CTkFrame(app.controls_card, fg_color="transparent")
    app.controls_grid.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 22))
    app.controls_grid.grid_columnconfigure(0, weight=1)
    app.controls_grid.grid_columnconfigure(1, weight=1)
    app.controls_grid.grid_columnconfigure(2, weight=1)

    app.pdf_panel, app.frame_pdf = _field_panel(
        app.controls_grid,
        UIConstants.TEXT_STEP_1,
        "Selecione o arquivo de frete que sera convertido para o layout posicional.",
    )
    app.pdf_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    app.frame_pdf.grid_columnconfigure(0, weight=1)

    app.entry_pdf = ctk.CTkEntry(
        app.frame_pdf,
        textvariable=app.pdf_path,
        placeholder_text=UIConstants.PLACEHOLDER_PDF,
        state="readonly",
        **_input_kwargs(),
    )
    app.entry_pdf.grid(row=0, column=0, sticky="ew", padx=(0, UIConstants.PADDING_INTERNAL))

    app.btn_buscar = ctk.CTkButton(
        app.frame_pdf,
        text=UIConstants.TEXT_BUTTON_BUSCAR_PDF,
        command=app._choose_pdf,
        width=150,
        **_secondary_button_kwargs(),
    )
    app.btn_buscar.grid(row=0, column=1, sticky="e")

    ctk.CTkLabel(
        app.frame_pdf,
        text=UIConstants.TEXT_ACTION_HINT,
        font=_font(UIConstants.FONT_SIZE_TINY),
        text_color=UIConstants.COLOR_TEXT_HINT,
        anchor="w",
        justify="left",
        wraplength=290,
    ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 10))

    app.btn_converter = ctk.CTkButton(
        app.controls_card,
        text=UIConstants.TEXT_BUTTON_CONVERTER,
        command=app._on_gerar,
        height=UIConstants.HEIGHT_BUTTON_LARGE,
        corner_radius=UIConstants.CORNER_RADIUS_BUTTON,
        font=_font(UIConstants.FONT_SIZE_BUTTON, "bold"),
        fg_color=UIConstants.COLOR_PRIMARY,
        hover_color=UIConstants.COLOR_PRIMARY_HOVER,
        text_color=UIConstants.COLOR_TEXT_ON_PRIMARY,
        state="disabled",
    )
    app.btn_converter.grid(row=3, column=0, sticky="ew", padx=22, pady=(10, 20))

    app.cnpj_panel, app.frame_cnpj = _field_panel(
        app.controls_grid,
        UIConstants.TEXT_STEP_2,
        "Busque a filial pelo CNPJ ou use a lista cadastrada para preencher o mapa com menos erro operacional.",
    )
    app.cnpj_panel.grid(row=0, column=1, sticky="nsew", padx=8)
    app.frame_cnpj.grid_columnconfigure(0, weight=1)
    app.frame_cnpj.grid_columnconfigure(1, weight=0)

    ctk.CTkLabel(
        app.frame_cnpj,
        text="CNPJ da filial",
        font=_font(UIConstants.FONT_SIZE_TINY, "bold"),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    app.frame_busca = ctk.CTkFrame(app.frame_cnpj, fg_color="transparent")
    app.frame_busca.grid(row=1, column=0, columnspan=2, sticky="ew")
    app.frame_busca.grid_columnconfigure(0, weight=1)
    app.frame_busca.grid_columnconfigure(1, weight=0)

    app.entry_cnpj = ctk.CTkEntry(
        app.frame_busca,
        textvariable=app.cnpj_mapa,
        placeholder_text=UIConstants.PLACEHOLDER_CNPJ,
        **_input_kwargs(),
    )
    app.entry_cnpj.grid(row=0, column=0, sticky="ew", padx=(0, UIConstants.PADDING_INTERNAL))

    app.btn_buscar_filial = ctk.CTkButton(
        app.frame_busca,
        text=UIConstants.TEXT_BUTTON_BUSCAR_FILIAL,
        command=app._buscar_filial_por_cnpj,
        width=110,
        **_secondary_button_kwargs(),
    )
    app.btn_buscar_filial.grid(row=0, column=1)

    ctk.CTkLabel(
        app.frame_cnpj,
        text="Filial cadastrada",
        font=_font(UIConstants.FONT_SIZE_TINY, "bold"),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(12, 8))

    try:
        if not hasattr(app._filiais_manager, "obter_opcoes_combo"):
            raise AttributeError("FiliaisManager nao possui metodo obter_opcoes_combo")
        opcoes_filiais = app._filiais_manager.obter_opcoes_combo()
        if opcoes_filiais and len(opcoes_filiais) > 0:
            opcoes_combo = [UIConstants.PLACEHOLDER_COMBO_FILIAL] + opcoes_filiais
        else:
            opcoes_combo = [UIConstants.PLACEHOLDER_COMBO_FILIAL]
    except Exception as e:
        opcoes_combo = [UIConstants.PLACEHOLDER_COMBO_FILIAL]
        print(f"[ERRO] Erro ao carregar filiais no combo: {e}")
        traceback.print_exc()

    app.combo_filial = ctk.CTkComboBox(
        app.frame_cnpj,
        values=opcoes_combo,
        variable=app.filial_selecionada,
        command=app._on_filial_selecionada,
        state="readonly",
        width=UIConstants.WIDTH_COMBO_MES,
        **_combo_kwargs(),
    )
    if opcoes_combo:
        app.filial_selecionada.set(UIConstants.PLACEHOLDER_COMBO_FILIAL)
    app.combo_filial.grid(row=3, column=0, columnspan=2, sticky="ew")

    app.lbl_filial_info = ctk.CTkLabel(
        app.frame_cnpj,
        textvariable=app.nome_filial,
        font=_font(UIConstants.FONT_SIZE_SMALL, "bold"),
        text_color=UIConstants.COLOR_TEXT_SUCCESS,
        anchor="w",
        justify="left",
        wraplength=290,
    )
    app.lbl_filial_info.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 4))

    app.lbl_dica = ctk.CTkLabel(
        app.frame_cnpj,
        text=UIConstants.TEXT_DICA_CNPJ,
        font=_font(UIConstants.FONT_SIZE_TINY),
        text_color=UIConstants.COLOR_TEXT_HINT,
        anchor="w",
        justify="left",
        wraplength=290,
    )
    app.lbl_dica.grid(row=5, column=0, columnspan=2, sticky="w")

    app.period_panel, app.frame_mes_ano = _field_panel(
        app.controls_grid,
        UIConstants.TEXT_STEP_3,
        "Defina o periodo que sera importado no SIPROQUIM para manter o arquivo consistente com o mapa.",
    )
    app.period_panel.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
    app.frame_mes_ano.grid_columnconfigure(0, weight=1)

    ctk.CTkLabel(
        app.frame_mes_ano,
        text="Mes de referencia",
        font=_font(UIConstants.FONT_SIZE_TINY, "bold"),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    ).grid(row=0, column=0, sticky="w", pady=(0, 8))

    app.combo_mes = ctk.CTkComboBox(
        app.frame_mes_ano,
        values=UIConstants.MESES_ABREVIADOS,
        variable=app.mes_selecionado,
        width=UIConstants.WIDTH_COMBO_MES,
        state="readonly",
        **_combo_kwargs(),
    )
    app.combo_mes.grid(row=1, column=0, sticky="ew")

    ctk.CTkLabel(
        app.frame_mes_ano,
        text="Ano de referencia",
        font=_font(UIConstants.FONT_SIZE_TINY, "bold"),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    ).grid(row=2, column=0, sticky="w", pady=(12, 8))

    app.entry_ano = ctk.CTkEntry(
        app.frame_mes_ano,
        textvariable=app.ano_selecionado,
        placeholder_text=UIConstants.PLACEHOLDER_ANO,
        width=UIConstants.WIDTH_COMBO_ANO,
        **_input_kwargs(),
    )
    app.entry_ano.grid(row=3, column=0, sticky="ew")

    app.lbl_dica_mes_ano = ctk.CTkLabel(
        app.frame_mes_ano,
        text=UIConstants.TEXT_DICA_MES_ANO,
        font=_font(UIConstants.FONT_SIZE_TINY),
        text_color=UIConstants.COLOR_TEXT_HINT,
        anchor="w",
    )
    app.lbl_dica_mes_ano.grid(row=4, column=0, sticky="w", pady=(8, 0))

    app.operations_grid = ctk.CTkFrame(app.left_column, fg_color="transparent")
    # Remover grids vazias das originais que estavam no root. A barra de progresso continua em app.controls_card.
    # Integração da Barra de Progresso dentro do Controls Card
    app.frame_status = ctk.CTkFrame(app.controls_card, fg_color="transparent")
    app.frame_status.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 20))
    app.frame_status.grid_columnconfigure(0, weight=1)
    app.frame_status.grid_columnconfigure(1, weight=0)

    app.lbl_progress_context = ctk.CTkLabel(
        app.frame_status,
        text=UIConstants.TEXT_PROGRESS_CONTEXT,
        font=_font(UIConstants.FONT_SIZE_SMALL),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    )
    app.lbl_progress_context.grid(row=0, column=0, sticky="w", pady=(0, 4))

    app.lbl_progress_percent = ctk.CTkLabel(
        app.frame_status,
        text="0%",
        font=_font(UIConstants.FONT_SIZE_SMALL, "bold"),
        text_color=UIConstants.COLOR_PRIMARY,
        anchor="e",
    )
    app.lbl_progress_percent.grid(row=0, column=1, sticky="e", pady=(0, 4))

    app.progress_bar = ctk.CTkProgressBar(
        app.frame_status,
        height=UIConstants.HEIGHT_PROGRESS_BAR,
        progress_color=UIConstants.COLOR_SECONDARY,
        fg_color=UIConstants.COLOR_BG_BADGE_NEUTRAL,
        corner_radius=999,
        border_width=0,
    )
    app.progress_bar.set(0)
    app.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew")

    app.lbl_status = ctk.CTkLabel(
        app.frame_status,
        textvariable=app.status,
        font=_font(UIConstants.FONT_SIZE_SMALL, "bold"),
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        anchor="w",
        justify="left",
    )
    app.lbl_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

    app.lbl_tempo = ctk.CTkLabel(
        app.frame_status,
        text="",
        font=_font(UIConstants.FONT_SIZE_TINY, family=UIConstants.FONT_FAMILY_LOGS),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    )
    app.lbl_tempo.grid(row=3, column=0, columnspan=2, sticky="w")

    app.frame_aprendizado = ctk.CTkFrame(
        app.right_column,
        fg_color=UIConstants.COLOR_BG_FRAME,
        border_width=2,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=UIConstants.CORNER_RADIUS_FRAME,
    )
    app.frame_aprendizado.grid(row=0, column=0, sticky="nsew")
    app.frame_aprendizado.grid_columnconfigure(0, weight=1)

    app.lbl_step4 = ctk.CTkLabel(
        app.frame_aprendizado,
        text=UIConstants.TEXT_STEP_4,
        font=_font(UIConstants.FONT_SIZE_HEADING, "bold"),
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        anchor="w",
    )
    app.lbl_step4.grid(row=0, column=0, sticky="w", padx=22, pady=(20, 6))

    app.lbl_dica_aprendizado = ctk.CTkLabel(
        app.frame_aprendizado,
        text=UIConstants.TEXT_DICA_APRENDIZADO,
        font=_font(UIConstants.FONT_SIZE_SMALL),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
        justify="left",
        wraplength=480, # Mais longo para agrupar em 1 linha
    )
    app.lbl_dica_aprendizado.grid(row=1, column=0, sticky="w", padx=22, pady=(0, 14))

    app.frame_aprendizado_acoes = ctk.CTkFrame(app.frame_aprendizado, fg_color="transparent")
    app.frame_aprendizado_acoes.grid(row=2, column=0, sticky="ew", padx=22)
    app.frame_aprendizado_acoes.grid_columnconfigure(0, weight=1)

    app.btn_aprender_txt = ctk.CTkButton(
        app.frame_aprendizado_acoes,
        text=UIConstants.TEXT_BUTTON_APRENDER_TXT,
        command=app._on_aprender_txt,
        height=UIConstants.HEIGHT_BUTTON_SMALL,
        corner_radius=UIConstants.CORNER_RADIUS_BUTTON_SEC,
        fg_color=UIConstants.COLOR_SECONDARY,
        hover_color=UIConstants.COLOR_SECONDARY_HOVER,
        text_color=UIConstants.COLOR_TEXT_ON_PRIMARY,
        font=_font(UIConstants.FONT_SIZE_SMALL, "bold"),
    )
    app.btn_aprender_txt.grid(row=0, column=0, sticky="w")

    app.btn_abrir_memoria = ctk.CTkButton(
        app.frame_aprendizado_acoes,
        text=UIConstants.TEXT_BUTTON_ABRIR_MEMORIA,
        command=app._abrir_pasta_memoria,
        height=UIConstants.HEIGHT_BUTTON_SMALL,
        corner_radius=UIConstants.CORNER_RADIUS_BUTTON_SEC,
        border_width=2,
        border_color=UIConstants.COLOR_PRIMARY,
        fg_color="transparent",
        hover_color=UIConstants.COLOR_BG_BADGE_NEUTRAL,
        text_color=UIConstants.COLOR_PRIMARY,
        font=_font(UIConstants.FONT_SIZE_SMALL, "bold"),
    )
    app.btn_abrir_memoria.grid(row=1, column=0, sticky="w", pady=(8, 0))

    try:
        resumo_memoria = app._aprendizado_store.resumo_memoria()
        caminho_memoria = resumo_memoria.get("arquivo_db", "")
    except Exception:
        caminho_memoria = ""

    app.frame_memoria_info = ctk.CTkFrame(
        app.frame_aprendizado,
        fg_color=UIConstants.COLOR_BG_SURFACE_ALT,
        border_width=2,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=16,
    )
    app.frame_memoria_info.grid(row=3, column=0, sticky="ew", padx=22, pady=(16, 20))
    app.frame_memoria_info.grid_columnconfigure(0, weight=1)

    app.lbl_memoria_path = ctk.CTkLabel(
        app.frame_memoria_info,
        text=app._formatar_texto_memoria(caminho_memoria),
        font=_font(UIConstants.FONT_SIZE_TINY),
        text_color=UIConstants.COLOR_TEXT_HINT,
        anchor="w",
        justify="left",
        wraplength=480,  # Expandido para evitar quebrar o caminho prematuramente
    )
    app.lbl_memoria_path.grid(row=0, column=0, sticky="ew", padx=14, pady=12)

    if not app._aprendizado_store:
        app.btn_aprender_txt.configure(state="disabled")
        app.btn_abrir_memoria.configure(state="disabled")
        app.lbl_memoria_path.configure(text=app._formatar_texto_memoria(""))

    app.stats_grid_row_1 = ctk.CTkFrame(app.right_column, fg_color="transparent")
    app.stats_grid_row_1.grid(row=1, column=0, sticky="ew", pady=(12, 0))
    app.stats_grid_row_1.grid_columnconfigure(0, weight=1)
    app.stats_grid_row_1.grid_columnconfigure(1, weight=1)

    app.stats_grid_row_2 = ctk.CTkFrame(app.right_column, fg_color="transparent")
    app.stats_grid_row_2.grid(row=2, column=0, sticky="ew", pady=(12, 0))
    app.stats_grid_row_2.grid_columnconfigure(0, weight=1)
    app.stats_grid_row_2.grid_columnconfigure(1, weight=1)

    app.card_registros, app.lbl_metric_registros, app.lbl_metric_registros_det = _metric_card(
        app.stats_grid_row_1, UIConstants.TEXT_METRIC_REGISTROS, UIConstants.COLOR_PRIMARY, "Leitura inicial do PDF"
    )
    app.card_registros.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

    app.card_nfs, app.lbl_metric_nfs, app.lbl_metric_nfs_det = _metric_card(
        app.stats_grid_row_1, UIConstants.TEXT_METRIC_NFS, UIConstants.COLOR_SECONDARY, "Apos deduplicacao"
    )
    app.card_nfs.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    app.card_ajustes, app.lbl_metric_ajustes, app.lbl_metric_ajustes_det = _metric_card(
        app.stats_grid_row_2, UIConstants.TEXT_METRIC_AJUSTES, UIConstants.COLOR_WARNING, "Exigem revisao manual"
    )
    app.card_ajustes.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

    app.card_criticos, app.lbl_metric_criticos, app.lbl_metric_criticos_det = _metric_card(
        app.stats_grid_row_2, UIConstants.TEXT_METRIC_CRITICOS, UIConstants.COLOR_DANGER, "Bloqueios identificados"
    )
    app.card_criticos.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    app.frame_logs_col = ctk.CTkFrame(
        app.container,
        fg_color=UIConstants.COLOR_BG_FRAME,
        border_width=1,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=UIConstants.CORNER_RADIUS_FRAME,
    )
    app.frame_logs_col.grid(row=2, column=0, sticky="ew", pady=(20, 0))
    app.frame_logs_col.grid_columnconfigure(0, weight=1)
    app.frame_logs_col.rowconfigure(2, weight=1)

    app.frame_logs_header = ctk.CTkFrame(app.frame_logs_col, fg_color="transparent")
    app.frame_logs_header.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 10))
    app.frame_logs_header.grid_columnconfigure(0, weight=1)

    texto_logs = ctk.CTkFrame(app.frame_logs_header, fg_color="transparent")
    texto_logs.grid(row=0, column=0, sticky="w")

    app.lbl_logs_title = ctk.CTkLabel(
        texto_logs,
        text=UIConstants.TEXT_LOGS_TITLE,
        font=_font(UIConstants.FONT_SIZE_HEADING, "bold"),
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        anchor="w",
    )
    app.lbl_logs_title.grid(row=0, column=0, sticky="w")

    ctk.CTkLabel(
        texto_logs,
        text=UIConstants.TEXT_LOGS_SUBTITLE,
        font=_font(UIConstants.FONT_SIZE_SMALL),
        text_color=UIConstants.COLOR_TEXT_SECONDARY,
        anchor="w",
    ).grid(row=1, column=0, sticky="w", pady=(4, 0))

    app.frame_font_controls = ctk.CTkFrame(
        app.frame_logs_header,
        fg_color=UIConstants.COLOR_BG_SURFACE_ALT,
        border_width=1,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=18,
    )
    app.frame_font_controls.grid(row=0, column=1, sticky="e")

    app.btn_font_minus = ctk.CTkButton(
        app.frame_font_controls,
        text="A-",
        width=40,
        command=lambda: app._ajustar_fonte_logs(-UIConstants.LOG_FONT_SIZE_STEP),
        **_secondary_button_kwargs(),
    )
    app.btn_font_minus.grid(row=0, column=0, padx=(10, 8), pady=10)

    app.btn_font_plus = ctk.CTkButton(
        app.frame_font_controls,
        text="A+",
        width=40,
        command=lambda: app._ajustar_fonte_logs(UIConstants.LOG_FONT_SIZE_STEP),
        **_secondary_button_kwargs(),
    )
    app.btn_font_plus.grid(row=0, column=1, padx=(0, 8), pady=10)

    app.btn_export_logs = ctk.CTkButton(
        app.frame_font_controls,
        text=UIConstants.TEXT_BUTTON_EXPORTAR_LOG,
        width=86,
        command=app._exportar_logs,
        **_secondary_button_kwargs(),
    )
    app.btn_export_logs.grid(row=0, column=2, padx=(0, 8), pady=10)

    app.btn_logs_fullscreen = ctk.CTkButton(
        app.frame_font_controls,
        text=UIConstants.TEXT_BUTTON_LOGS_FULLSCREEN,
        width=96,
        command=app._toggle_logs_fullscreen,
        **_secondary_button_kwargs(),
    )
    app.btn_logs_fullscreen.grid(row=0, column=3, padx=(0, 10), pady=10)

    app.lbl_logs_legend = ctk.CTkLabel(
        app.frame_logs_col,
        text=UIConstants.TEXT_LOGS_LEGEND,
        font=_font(UIConstants.FONT_SIZE_TINY),
        text_color=UIConstants.COLOR_TEXT_HINT,
        anchor="w",
    )
    app.lbl_logs_legend.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 10))

    app.frame_logs = ctk.CTkFrame(
        app.frame_logs_col,
        height=420,
        fg_color=UIConstants.COLOR_BG_TEXTBOX,
        border_width=1,
        border_color=UIConstants.COLOR_BORDER,
        corner_radius=UIConstants.CORNER_RADIUS_LOGS,
    )
    app.frame_logs.grid(row=2, column=0, sticky="nsew", padx=22, pady=(0, 22))
    app.frame_logs.columnconfigure(0, weight=1)
    app.frame_logs.rowconfigure(0, weight=1)
    app.frame_logs.grid_propagate(False)

    app.textbox_logs = ctk.CTkTextbox(
        app.frame_logs,
        font=_font(UIConstants.LOG_FONT_SIZE_DEFAULT, family=UIConstants.FONT_FAMILY_LOGS),
        text_color=UIConstants.COLOR_TEXT_PRIMARY,
        fg_color=UIConstants.COLOR_BG_TEXTBOX,
        border_width=0,
        corner_radius=16,
        wrap="word",
    )
    app.textbox_logs.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
    app.textbox_logs.configure(state="disabled")

    app.cnpj_mapa.trace_add("write", app._on_cnpj_changed)
    app.ano_selecionado.trace_add("write", app._on_campo_changed)
    app.mes_selecionado.trace_add("write", app._on_campo_changed)
    app.status.trace_add("write", app._on_status_text_changed)

    update_metric_cards(app)
    update_log_summary_cards(app)
    update_progress_card(app, 0.0, UIConstants.TEXT_PROGRESS_CONTEXT)
    update_status_badge(app, app.status.get())


def update_metric_cards(app) -> None:
    """Atualiza cards de estatistica do painel."""
    total_registros = app._total_registros_extraidos or 0
    total_nfs = app._total_nfs_dedup or app._ultima_estatistica.get("total_aprovados", 0) or 0
    ajustes_manuais = app._ultima_estatistica.get("total_ajustes_manuais", 0) or 0
    corrigidos = app._ultima_estatistica.get("total_corrigidos", 0) or 0
    criticos = app._ultima_estatistica.get("total_com_erros_criticos", 0) or 0

    app.lbl_metric_registros.configure(text=str(total_registros))
    app.lbl_metric_registros_det.configure(text="Leitura bruta do PDF")
    app.lbl_metric_nfs.configure(text=str(total_nfs))
    app.lbl_metric_nfs_det.configure(text="Apos deduplicacao de notas")
    app.lbl_metric_ajustes.configure(text=str(ajustes_manuais))
    app.lbl_metric_ajustes_det.configure(text=f"Correcoes automaticas: {corrigidos}")
    app.lbl_metric_criticos.configure(text=str(criticos))
    app.lbl_metric_criticos_det.configure(text="Pendencias que exigem revisao")


def update_log_summary_cards(app) -> None:
    """Renderiza os mini-cards acima do historico."""
    if hasattr(app, "lbl_log_eventos_valor") and app.lbl_log_eventos_valor:
        app.lbl_log_eventos_valor.configure(text=str(app._log_event_count))
    if hasattr(app, "lbl_log_pendencias_valor") and app.lbl_log_pendencias_valor:
        app.lbl_log_pendencias_valor.configure(text=str(app._log_pending_count))
    if hasattr(app, "lbl_log_ultimo_valor") and app.lbl_log_ultimo_valor:
        app.lbl_log_ultimo_valor.configure(text=app._ultimo_log_resumo)


def update_progress_card(app, progresso: float, contexto: str | None = None) -> None:
    """Atualiza o card de progresso com percentual e contexto."""
    progresso_normalizado = max(0.0, min(1.0, float(progresso)))
    if hasattr(app, "progress_bar") and app.progress_bar:
        app.progress_bar.set(progresso_normalizado)
    if hasattr(app, "lbl_progress_percent") and app.lbl_progress_percent:
        app.lbl_progress_percent.configure(text=f"{int(progresso_normalizado * 100):02d}%")
    if contexto is not None and hasattr(app, "lbl_progress_context") and app.lbl_progress_context:
        app.lbl_progress_context.configure(text=contexto)


def update_status_badge(app, texto_status: str) -> None:
    """Atualiza badge e detalhe do status no cabecalho."""
    texto = (texto_status or "").strip()
    texto_upper = texto.upper()

    badge = "Parado"
    fg_color = UIConstants.COLOR_BG_BADGE_NEUTRAL
    text_color = UIConstants.COLOR_PRIMARY
    if any(chave in texto_upper for chave in ["ERRO", "FALHA", "CRITIC", "PENDENCIAS CRITICAS"]):
        badge = "Erro"
        fg_color = UIConstants.COLOR_DANGER_SOFT
        text_color = UIConstants.COLOR_TEXT_DANGER
    elif any(chave in texto_upper for chave in ["SUCESSO", "CONCLUID", "FINALIZADO"]):
        badge = "Sucesso"
        fg_color = UIConstants.COLOR_SUCCESS_SOFT
        text_color = UIConstants.COLOR_SUCCESS
    elif any(chave in texto_upper for chave in ["ABRINDO", "EXTRAINDO", "GERANDO", "PROCESSANDO", "VALIDANDO", "DEDUPLICANDO", "APRENDENDO"]):
        badge = "Executando"
        fg_color = UIConstants.COLOR_BG_BADGE_RUNNING
        text_color = UIConstants.COLOR_SECONDARY

    if hasattr(app, "header_status_badge") and app.header_status_badge:
        app.header_status_badge.configure(
            text=badge,
            fg_color=fg_color,
            text_color=text_color,
        )
    if hasattr(app, "header_status_detail") and app.header_status_detail:
        app.header_status_detail.configure(text=texto or UIConstants.TEXT_HEADER_STATUS_DETAIL)
    if hasattr(app, "header_status_time") and app.header_status_time:
        app.header_status_time.configure(text=f"Atualizado em {datetime.now().strftime('%H:%M:%S')}")
