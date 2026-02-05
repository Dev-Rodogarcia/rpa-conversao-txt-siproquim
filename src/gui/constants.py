"""
Constantes para a interface gráfica.
Centraliza cores, tamanhos, textos e valores configuráveis.
"""

from src.gerador.layout_constants import MESES_ALFANUMERICOS


class UIConstants:
    """Constantes da interface gráfica."""
    
    # ============================================================================
    # CONFIGURAÇÕES DA JANELA
    # ============================================================================
    WINDOW_TITLE = "SIPROQUIM Converter V2 by valentelucass"
    WINDOW_SIZE = "1250x750"
    WINDOW_RESIZABLE = True
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 650
    
    # ============================================================================
    # CORES
    # ============================================================================
    # Cores principais
    COLOR_PRIMARY = "#2CC985"  # Verde vibrante
    COLOR_PRIMARY_HOVER = "#25A96F"  # Verde hover
    COLOR_SECONDARY = "#3B8ED0"  # Azul
    COLOR_SECONDARY_HOVER = "#36719F"  # Azul hover
    COLOR_DISABLED = "gray30"  # Cinza inativo
    
    # Cores de logs
    COLOR_LOG_ERROR = "#FF6B6B"  # Vermelho
    COLOR_LOG_SUCCESS = "#51CF66"  # Verde
    COLOR_LOG_INFO = "#E5E7EB"  # Branco suave
    COLOR_LOG_DEBUG = "#A78BFA"  # Roxo
    COLOR_LOG_WARNING = "#FFD43B"  # Amarelo
    COLOR_LOG_SYSTEM = "#60A5FA"  # Azul
    COLOR_LOG_STATUS = "#22D3EE"  # Ciano
    COLOR_LOG_ACTION = "#A3E635"  # Verde lima
    COLOR_LOG_NF = "#FFFFFF"  # Branco
    
    # Cores de texto
    COLOR_TEXT_PRIMARY = ("gray10", "gray90")
    COLOR_TEXT_SECONDARY = "gray60"
    COLOR_TEXT_HINT = "gray50"
    COLOR_TEXT_SUCCESS = "#2CC985"
    
    # Cores de background
    COLOR_BG_FRAME = ("gray90", "gray15")
    COLOR_BG_FRAME_LOGS = ("gray85", "gray20")
    COLOR_BG_TEXTBOX = ("gray95", "gray10")
    
    # ============================================================================
    # TAMANHOS E DIMENSÕES
    # ============================================================================
    # Tamanhos de fonte
    FONT_SIZE_TITLE = 26
    FONT_SIZE_SUBTITLE = 13
    FONT_SIZE_HEADING = 14
    FONT_SIZE_NORMAL = 12
    FONT_SIZE_SMALL = 11
    FONT_SIZE_TINY = 10
    FONT_SIZE_BUTTON = 15
    
    # Fontes de log (ajustáveis pela UI)
    LOG_FONT_SIZE_DEFAULT = 10
    LOG_FONT_SIZE_MIN = 8
    LOG_FONT_SIZE_MAX = 16
    LOG_FONT_SIZE_STEP = 1
    
    # Alturas de componentes
    HEIGHT_ENTRY = 35
    HEIGHT_BUTTON_SMALL = 35
    HEIGHT_BUTTON_LARGE = 50
    HEIGHT_TEXTBOX_LOGS = 150
    HEIGHT_PROGRESS_BAR = 10
    
    # Larguras
    WIDTH_BUTTON_SMALL = 100
    WIDTH_COMBO_MES = 150
    WIDTH_COMBO_ANO = 150
    
    # Padding e espaçamentos
    PADDING_FRAME = 30
    PADDING_MAIN = 20
    PADDING_INTERNAL = 10
    PADDING_SMALL = 5
    
    # Corner radius
    CORNER_RADIUS_MAIN = 15
    CORNER_RADIUS_FRAME = 10
    CORNER_RADIUS_LOGS = 8
    
    # ============================================================================
    # TEXTOS E MENSAGENS
    # ============================================================================
    # Título e subtítulo
    TEXT_TITLE = "Conversor SIPROQUIM - Rodogarcia"
    TEXT_SUBTITLE = "Transforme seus PDFs de frete no padrão da Polícia Federal"
    
    # Labels de etapas
    TEXT_STEP_1 = "1. Selecione o arquivo PDF"
    TEXT_STEP_2 = "2. Filial / CNPJ do Mapa"
    TEXT_STEP_3 = "3. Período de Referência (Mês/Ano)"
    
    # Placeholders
    PLACEHOLDER_PDF = "Nenhum arquivo selecionado..."
    PLACEHOLDER_CNPJ = "Digite o CNPJ (14 dígitos) ou busque pela filial"
    PLACEHOLDER_ANO = "Ano (ex: 2025)"
    PLACEHOLDER_COMBO_FILIAL = "Selecione uma filial..."
    
    # Botões
    TEXT_BUTTON_BUSCAR_PDF = "Buscar PDF"
    TEXT_BUTTON_BUSCAR_FILIAL = "Buscar"
    TEXT_BUTTON_CONVERTER = "CONVERTER AGORA"
    TEXT_BUTTON_PROCESSANDO = "PROCESSANDO..."
    
    # Dicas
    TEXT_DICA_CNPJ = "ℹ️ Digite o CNPJ e clique em 'Buscar' ou selecione uma filial na lista acima."
    TEXT_DICA_MES_ANO = "ℹ️ Período de referência do arquivo conforme SIPROQUIM (ex: DEZ/2025)."
    
    # Títulos de seções
    TEXT_LOGS_TITLE = "📋 Logs de Processamento"
    TEXT_LOGS_LEGEND = "SYSTEM=Processo | CONFIG=Configuracao | STATUS=Etapa | PROGRESSO=Andamento | RELATORIO=Resumo final | CHECK=Indicadores | AVISO=Revisao manual | ERRO=Falha | EXPORT=Arquivo"
    TEXT_STATUS_DEFAULT = "Aguardando ação do usuário..."
    TEXT_STATUS_INICIANDO = "Iniciando processamento..."
    TEXT_STATUS_ABRINDO_PDF = "Abrindo arquivo PDF..."
    
    # Mensagens de sucesso
    TEXT_SUCESSO_CONVERSAO = "✅ Conversão concluída com sucesso!"
    TEXT_SUCESSO_ARQUIVO_SALVO = "Arquivo salvo em:"
    TEXT_SUCESSO_ABRIR_DOWNLOADS = "Abrir pasta de downloads?"
    
    # Mensagens de erro
    TEXT_ERRO_PDF_INVALIDO = "PDF inválido."
    TEXT_ERRO_CNPJ_INVALIDO = "CNPJ deve ter {digitos} dígitos."
    TEXT_ERRO_MES_NAO_SELECIONADO = "Selecione o mês de referência."
    TEXT_ERRO_ANO_INVALIDO = "Ano deve ter 4 dígitos (ex: 2025)."
    TEXT_ERRO_ANO_FORA_INTERVALO = "Ano deve estar entre {min} e {max}."
    TEXT_ERRO_ANO_INVALIDO_VALOR = "Ano inválido."
    TEXT_ERRO_MES_INVALIDO = "Mês inválido: {mes}"
    TEXT_ERRO_CONVERSAO = "Erro na conversão."
    TEXT_ERRO_DETALHES = "Falha ao processar:\n{erro}\n\nVerifique os logs abaixo para mais detalhes."
    
    # Mensagens de aviso
    TEXT_AVISO_CNPJ_DIGITOS = "CNPJ deve ter {digitos} dígitos."
    TEXT_AVISO_CNPJ_NAO_ENCONTRADO = "⚠ CNPJ não encontrado no cadastro: {cnpj}"
    TEXT_INFO_CNPJ_ENCONTRADO = "✓ {nome} - CNPJ: {cnpj}"
    
    # ============================================================================
    # VALORES DE PROGRESSO
    # ============================================================================
    PROGRESSO_INICIAL = 0.05  # 5% inicial
    PROGRESSO_EXTRAIR = 0.70  # 70% para extração
    PROGRESSO_DEDUPLICAR = 0.75  # 75% para deduplicação
    PROGRESSO_GERAR = 0.90  # 90% para geração
    PROGRESSO_COMPLETO = 1.0  # 100% completo
    
    # ============================================================================
    # CONFIGURAÇÕES DE LOG
    # ============================================================================
    INTERVALO_LOG_PAGINAS = 10  # Log a cada N páginas
    
    # ============================================================================
    # MESES E MAPEAMENTOS
    # ============================================================================
    MESES_ABREVIADOS = list(MESES_ALFANUMERICOS.values())
    MES_PADRAO = "DEZ"  # Dezembro
    
    # Mapeamento de meses abreviados para números
    MAPA_MESES = {
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12
    }
    
    # ============================================================================
    # TIPOS DE LOG
    # ============================================================================
    LOG_TIPOS = {
        "ERRO": COLOR_LOG_ERROR,
        "SUCESSO": COLOR_LOG_SUCCESS,
        "INFO": COLOR_LOG_INFO,
        "DEBUG": COLOR_LOG_DEBUG,
        "AVISO": COLOR_LOG_WARNING,
        "ALERTA": COLOR_LOG_WARNING,
        "ATENCAO": COLOR_LOG_WARNING,
        "ACAO_NECESSARIA": COLOR_LOG_WARNING,
        "VALIDACAO": COLOR_LOG_INFO,
        "SYSTEM": COLOR_LOG_SYSTEM,
        "CONFIG": COLOR_LOG_SYSTEM,
        "STATUS": COLOR_LOG_STATUS,
        "PROGRESSO": COLOR_LOG_STATUS,
        "RELATORIO": COLOR_LOG_SYSTEM,
        "CHECK": COLOR_LOG_SUCCESS,
        "EXPORT": COLOR_LOG_SUCCESS
    }
    
    # ============================================================================
    # CONFIGURAÇÕES DE TEMA
    # ============================================================================
    THEME_MODE = "Dark"  # "System", "Dark", "Light"
    THEME_COLOR = "blue"  # "blue", "green", "dark-blue"
    
    # ============================================================================
    # CONFIGURAÇÕES DE ARQUIVO
    # ============================================================================
    FILE_TYPES_PDF = [("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
    DIALOG_TITLE_PDF = "Selecione o arquivo PDF"
    DIALOG_TITLE_SUCESSO = "Sucesso"
    DIALOG_TITLE_ERRO = "Erro na Conversão"
    DIALOG_TITLE_AVISO = "Aviso"
    
    # ============================================================================
    # FORMATAÇÃO DE NOMES DE ARQUIVO
    # ============================================================================
    FORMATO_NOME_ARQUIVO = "M{ano}{mes}{cnpj}.txt"
    
    # ============================================================================
    # FONTES
    # ============================================================================
    FONT_FAMILY_TITLE = "Roboto"
    FONT_FAMILY_LOGS = "Consolas"
