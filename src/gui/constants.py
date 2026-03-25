"""
Constantes da interface grafica.
"""

from src.gerador.layout_constants import MESES_ALFANUMERICOS


def _pair(light: str, dark: str) -> tuple[str, str]:
    return (light, dark)


class UIConstants:
    """Constantes de UI usadas no app."""

    # Window
    WINDOW_TITLE = "Rodogarcia | Painel SIPROQUIM by valentelucass" 
    WINDOW_SIZE = "1440x900"
    WINDOW_RESIZABLE = True
    WINDOW_START_MAXIMIZED = True
    WINDOW_MIN_WIDTH = 1180
    WINDOW_MIN_HEIGHT = 760

    # Visual identity
    COLOR_PRIMARY = _pair("#21478A", "#7AA8F6")
    COLOR_PRIMARY_HOVER = _pair("#1A3970", "#5B93F3")
    COLOR_PRIMARY_PRESSED = _pair("#15315E", "#3A72E4")
    COLOR_SECONDARY = _pair("#2B89D9", "#5EB7FF")
    COLOR_SECONDARY_HOVER = _pair("#2270B3", "#489EE3")
    COLOR_DISABLED = _pair("#C9D6E3", "#33455D")

    COLOR_SUCCESS = _pair("#1F7A63", "#4CC29D")
    COLOR_SUCCESS_SOFT = _pair("#EAEFF4", "#18342D")
    COLOR_DANGER = _pair("#B55045", "#F08B81")
    COLOR_DANGER_SOFT = _pair("#FBEAE8", "#3D2325")
    COLOR_WARNING = _pair("#B7791F", "#F0BE57")
    COLOR_WARNING_SOFT = _pair("#FFF5E4", "#3B2E19")

    COLOR_BG_APP = _pair("#E2E8F0", "#020817")
    COLOR_BG_FRAME = _pair("#FFFFFF", "#0F172A")
    COLOR_BG_FRAME_LOGS = _pair("#FFFFFF", "#0F172A")
    COLOR_BG_TEXTBOX = _pair("#F8FAFC", "#08111F")
    COLOR_BG_SURFACE_ALT = _pair("#F1F5F9", "#122033")
    COLOR_BG_FIELD_PANEL = _pair("#F8FAFC", "#0F172A")
    COLOR_BG_BADGE_NEUTRAL = _pair("#EFF6FF", "#16243A")
    COLOR_BG_BADGE_RUNNING = _pair("#E0F2FE", "#173155")

    COLOR_BORDER = _pair("#CBD5E1", "#22324A")
    COLOR_BORDER_STRONG = _pair("#94A3B8", "#334155")

    COLOR_TEXT_PRIMARY = _pair("#0F172A", "#F8FAFC")
    COLOR_TEXT_SECONDARY = _pair("#64748B", "#C0CFE4")
    COLOR_TEXT_HINT = _pair("#94A3B8", "#7E92AF")
    COLOR_TEXT_SUCCESS = _pair("#1F7A63", "#69D1AF")
    COLOR_TEXT_DANGER = _pair("#B55045", "#F3A29A")
    COLOR_TEXT_ON_PRIMARY = _pair("#FFFFFF", "#09111F")

    # Logs
    COLOR_LOG_ERROR = "#B55045"
    COLOR_LOG_SUCCESS = "#1F7A63"
    COLOR_LOG_INFO = "#21478A"
    COLOR_LOG_DEBUG = "#64748B"
    COLOR_LOG_WARNING = "#B7791F"
    COLOR_LOG_SYSTEM = "#21478A"
    COLOR_LOG_STATUS = "#2B89D9"
    COLOR_LOG_ACTION = "#21478A"
    COLOR_LOG_NF = "#0F172A"

    # Dimensions
    LOG_FONT_SIZE_MIN = 9
    LOG_FONT_SIZE_DEFAULT = 11
    LOG_FONT_SIZE_MAX = 18
    LOG_FONT_SIZE_STEP = 1

    FONT_SIZE_TITLE = 28
    FONT_SIZE_SUBTITLE = 12
    FONT_SIZE_HEADING = 18
    FONT_SIZE_NORMAL = 13
    FONT_SIZE_SMALL = 12
    FONT_SIZE_TINY = 11
    FONT_SIZE_BUTTON = 15
    FONT_SIZE_METRIC = 30
    FONT_SIZE_BADGE = 11

    HEIGHT_ENTRY = 40
    HEIGHT_BUTTON_SMALL = 38
    HEIGHT_BUTTON_LARGE = 46
    HEIGHT_PROGRESS_BAR = 14

    WIDTH_BUTTON_SMALL = 110
    WIDTH_COMBO_MES = 170
    WIDTH_COMBO_ANO = 170

    PADDING_FRAME = 24
    PADDING_MAIN = 20
    PADDING_INTERNAL = 12
    PADDING_SMALL = 6

    CORNER_RADIUS_MAIN = 0
    CORNER_RADIUS_FRAME = 20
    CORNER_RADIUS_LOGS = 20
    CORNER_RADIUS_HEADER = 24
    CORNER_RADIUS_BUTTON = 10
    CORNER_RADIUS_BUTTON_SEC = 10
    CORNER_RADIUS_BADGE = 999

    # Texts
    TEXT_TITLE = "Conversor Operacional SIPROQUIM"
    TEXT_SUBTITLE = "Operacao compacta para leitura de PDFs, validacao estrutural e envio consistente ao SIPROQUIM."
    TEXT_HEADER_KICKER = "PAINEL OPERACIONAL"
    TEXT_HEADER_SELO = "MAPAS E TRANSPORTE NACIONAL"
    TEXT_HEADER_STATUS_TITLE = "Status do robo"
    TEXT_HEADER_STATUS_DETAIL = "Aguardando novo lote para processamento."
    TEXT_THEME_LABEL = "Tema"
    TEXT_THEME_LIGHT = "Claro"
    TEXT_THEME_DARK = "Escuro"

    TEXT_STEP_1 = "Arquivo de origem"
    TEXT_STEP_2 = "Filial e CNPJ do mapa"
    TEXT_STEP_3 = "Periodo de referencia"
    TEXT_STEP_4 = "Memoria de aprendizado"

    PLACEHOLDER_PDF = "Selecione o PDF de fretes para iniciar o processamento"
    PLACEHOLDER_CNPJ = "Digite o CNPJ da filial ou use a busca"
    PLACEHOLDER_ANO = "Ano (ex: 2026)"
    PLACEHOLDER_COMBO_FILIAL = "Selecione uma filial..."

    TEXT_BUTTON_BUSCAR_PDF = "Selecionar PDF"
    TEXT_BUTTON_BUSCAR_FILIAL = "Buscar"
    TEXT_BUTTON_CONVERTER = "Processar arquivo"
    TEXT_BUTTON_PROCESSANDO = "Processando..."
    TEXT_BUTTON_APRENDER_TXT = "Aprender TXT corrigido"
    TEXT_BUTTON_APRENDENDO_TXT = "Aprendendo..."
    TEXT_BUTTON_ABRIR_MEMORIA = "Abrir pasta memoria"
    TEXT_BUTTON_EXPORTAR_LOG = "Exportar"
    TEXT_BUTTON_LOGS_FULLSCREEN = "Tela cheia"

    TEXT_ACTION_TITLE = "Inicializar processo"
    TEXT_ACTION_HINT = "Valida o layout final antes do upload e salva o TXT padronizado na pasta Downloads."

    TEXT_DICA_CNPJ = "Busque a filial pelo CNPJ ou selecione diretamente na lista cadastrada."
    TEXT_DICA_MES_ANO = "Use o periodo do mapa que sera importado no SIPROQUIM."
    TEXT_DICA_APRENDIZADO = (
        "Reimporte um TXT corrigido para reforcar a memoria operacional e reduzir ajustes manuais nos proximos lotes."
    )

    TEXT_LOGS_TITLE = "Historico de execucao"
    TEXT_LOGS_SUBTITLE = "Console operacional do lote em tempo real."
    TEXT_LOGS_LEGEND = (
        "SYSTEM=Processo | STATUS=Etapa | PROGRESSO=Andamento | CHECK=Validacao | "
        "AVISO=Revisao manual | ERRO=Falha | EXPORT=Arquivo"
    )
    TEXT_STATUS_DEFAULT = "Aguardando selecao do arquivo e parametros do mapa."
    TEXT_STATUS_INICIANDO = "Iniciando processamento..."
    TEXT_STATUS_ABRINDO_PDF = "Abrindo arquivo PDF..."
    TEXT_PROGRESS_TITLE = "Progresso do lote"
    TEXT_PROGRESS_CONTEXT = "Preparando ambiente de processamento."

    TEXT_METRIC_REGISTROS = "Registros extraidos"
    TEXT_METRIC_NFS = "NFs unicas"
    TEXT_METRIC_AJUSTES = "Ajustes manuais"
    TEXT_METRIC_CRITICOS = "Erros criticos"

    TEXT_LOG_SUMMARY_EVENTOS = "Eventos"
    TEXT_LOG_SUMMARY_PENDENCIAS = "Pendencias"
    TEXT_LOG_SUMMARY_ULTIMO = "Ultimo evento"

    TEXT_SUCESSO_CONVERSAO = "Conversao concluida com sucesso."
    TEXT_SUCESSO_ARQUIVO_SALVO = "Arquivo salvo em:"
    TEXT_SUCESSO_ABRIR_DOWNLOADS = "Abrir pasta de downloads?"

    TEXT_ERRO_PDF_INVALIDO = "PDF invalido."
    TEXT_ERRO_CNPJ_INVALIDO = "CNPJ deve ter {digitos} digitos."
    TEXT_ERRO_MES_NAO_SELECIONADO = "Selecione o mes de referencia."
    TEXT_ERRO_ANO_INVALIDO = "Ano deve ter 4 digitos (ex: 2026)."
    TEXT_ERRO_ANO_FORA_INTERVALO = "Ano deve estar entre {min} e {max}."
    TEXT_ERRO_ANO_INVALIDO_VALOR = "Ano invalido."
    TEXT_ERRO_MES_INVALIDO = "Mes invalido: {mes}"
    TEXT_ERRO_CONVERSAO = "Erro na conversao."
    TEXT_ERRO_DETALHES = "Falha ao processar:\n{erro}\n\nVerifique os logs abaixo para mais detalhes."

    TEXT_AVISO_CNPJ_DIGITOS = "CNPJ deve ter {digitos} digitos."
    TEXT_AVISO_CNPJ_NAO_ENCONTRADO = "CNPJ nao encontrado no cadastro: {cnpj}"
    TEXT_INFO_CNPJ_ENCONTRADO = "{nome} - CNPJ: {cnpj}"

    # Progress
    PROGRESSO_INICIAL = 0.05
    PROGRESSO_EXTRAIR = 0.70
    PROGRESSO_DEDUPLICAR = 0.75
    PROGRESSO_GERAR = 0.90
    PROGRESSO_COMPLETO = 1.0

    # Log
    INTERVALO_LOG_PAGINAS = 10

    # Month map
    MESES_ABREVIADOS = list(MESES_ALFANUMERICOS.values())
    MES_PADRAO = "DEZ"
    MAPA_MESES = {
        "JAN": 1,
        "FEV": 2,
        "MAR": 3,
        "ABR": 4,
        "MAI": 5,
        "JUN": 6,
        "JUL": 7,
        "AGO": 8,
        "SET": 9,
        "OUT": 10,
        "NOV": 11,
        "DEZ": 12,
    }

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
        "EXPORT": COLOR_LOG_SUCCESS,
        "CRITICO": COLOR_LOG_ERROR,
    }

    THEME_MODE = "Light"
    THEME_COLOR = "blue"
    THEME_OPTIONS = [TEXT_THEME_LIGHT, TEXT_THEME_DARK]
    THEME_OPTION_TO_MODE = {
        TEXT_THEME_LIGHT: "Light",
        TEXT_THEME_DARK: "Dark",
    }

    FILE_TYPES_PDF = [("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
    FILE_TYPES_TXT = [("Arquivos TXT", "*.txt"), ("Todos os arquivos", "*.*")]
    DIALOG_TITLE_PDF = "Selecione o arquivo PDF"
    DIALOG_TITLE_TXT = "Selecione o TXT corrigido"
    DIALOG_TITLE_SUCESSO = "Sucesso"
    DIALOG_TITLE_ERRO = "Erro na Conversao"
    DIALOG_TITLE_AVISO = "Aviso"

    FORMATO_NOME_ARQUIVO = "M{ano}{mes}{cnpj}.txt"

    FONT_FAMILY_TITLE = "Manrope"
    FONT_FAMILY_TEXT = "Manrope"
    FONT_FAMILY_LOGS = "Consolas"
