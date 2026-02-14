"""
Constantes da interface grafica.
"""

from src.gerador.layout_constants import MESES_ALFANUMERICOS


class UIConstants:
    """Constantes de UI usadas no app."""

    # Window
    WINDOW_TITLE = "SIPROQUIM Converter V3 by valentelucass"
    WINDOW_SIZE = "1250x750"
    WINDOW_RESIZABLE = True
    WINDOW_START_MAXIMIZED = True
    WINDOW_MIN_WIDTH = 1000
    WINDOW_MIN_HEIGHT = 650

    # Colors
    COLOR_PRIMARY = "#2CC985"
    COLOR_PRIMARY_HOVER = "#25A96F"
    COLOR_SECONDARY = "#3B8ED0"
    COLOR_SECONDARY_HOVER = "#36719F"
    COLOR_DISABLED = "gray30"

    COLOR_LOG_ERROR = "#FF6B6B"
    COLOR_LOG_SUCCESS = "#51CF66"
    COLOR_LOG_INFO = "#FFFFFF"
    COLOR_LOG_DEBUG = "#A78BFA"
    COLOR_LOG_WARNING = "#FFD43B"
    COLOR_LOG_SYSTEM = "#60A5FA"
    COLOR_LOG_STATUS = "#22D3EE"
    COLOR_LOG_ACTION = "#A3E635"
    COLOR_LOG_NF = "#FFFFFF"

    COLOR_TEXT_PRIMARY = ("gray10", "gray90")
    COLOR_TEXT_SECONDARY = "gray60"
    COLOR_TEXT_HINT = "gray50"
    COLOR_TEXT_SUCCESS = "#2CC985"

    COLOR_BG_FRAME = ("gray90", "gray15")
    COLOR_BG_FRAME_LOGS = ("gray85", "gray20")
    COLOR_BG_TEXTBOX = ("gray95", "gray10")

    # Dimensions
    LOG_FONT_SIZE_MIN = 9
    LOG_FONT_SIZE_DEFAULT = 11
    LOG_FONT_SIZE_MAX = 18
    LOG_FONT_SIZE_STEP = 1

    FONT_SIZE_TITLE = 26
    FONT_SIZE_SUBTITLE = 13
    FONT_SIZE_HEADING = 14
    FONT_SIZE_NORMAL = 12
    FONT_SIZE_SMALL = 11
    FONT_SIZE_TINY = 10
    FONT_SIZE_BUTTON = 15

    HEIGHT_ENTRY = 35
    HEIGHT_BUTTON_SMALL = 35
    HEIGHT_BUTTON_LARGE = 50
    HEIGHT_TEXTBOX_LOGS = 150
    HEIGHT_PROGRESS_BAR = 10

    WIDTH_BUTTON_SMALL = 100
    WIDTH_COMBO_MES = 150
    WIDTH_COMBO_ANO = 150

    PADDING_FRAME = 30
    PADDING_MAIN = 20
    PADDING_INTERNAL = 10
    PADDING_SMALL = 5

    CORNER_RADIUS_MAIN = 15
    CORNER_RADIUS_FRAME = 10
    CORNER_RADIUS_LOGS = 8

    # Texts
    TEXT_TITLE = "Conversor SIPROQUIM - Rodogarcia"
    TEXT_SUBTITLE = "Transforme seus PDFs de frete no padrao da Policia Federal"

    TEXT_STEP_1 = "1. Selecione o arquivo PDF"
    TEXT_STEP_2 = "2. Filial / CNPJ do Mapa"
    TEXT_STEP_3 = "3. Periodo de Referencia (Mes/Ano)"
    TEXT_STEP_4 = "4. Aprendizado (opcional)"

    PLACEHOLDER_PDF = "Nenhum arquivo selecionado..."
    PLACEHOLDER_CNPJ = "Digite o CNPJ (14 digitos) ou busque pela filial"
    PLACEHOLDER_ANO = "Ano (ex: 2025)"
    PLACEHOLDER_COMBO_FILIAL = "Selecione uma filial..."

    TEXT_BUTTON_BUSCAR_PDF = "Buscar PDF"
    TEXT_BUTTON_BUSCAR_FILIAL = "Buscar"
    TEXT_BUTTON_CONVERTER = "CONVERTER AGORA"
    TEXT_BUTTON_PROCESSANDO = "PROCESSANDO..."
    TEXT_BUTTON_APRENDER_TXT = "Aprender TXT corrigido"
    TEXT_BUTTON_APRENDENDO_TXT = "APRENDENDO..."
    TEXT_BUTTON_ABRIR_MEMORIA = "Abrir pasta memoria"

    TEXT_DICA_CNPJ = "Digite o CNPJ e clique em 'Buscar' ou selecione uma filial."
    TEXT_DICA_MES_ANO = "Periodo de referencia conforme SIPROQUIM (ex: DEZ/2025)."
    TEXT_DICA_APRENDIZADO = (
        "Opcional: reimporte um TXT corrigido para o sistema aprender e reutilizar nos proximos lotes."
    )

    TEXT_LOGS_TITLE = "Logs de Processamento"
    TEXT_LOGS_LEGEND = (
        "SYSTEM=Processo | CONFIG=Configuracao | STATUS=Etapa | PROGRESSO=Andamento | "
        "RELATORIO=Resumo final | CHECK=Indicadores | AVISO=Revisao manual | ERRO=Falha | EXPORT=Arquivo"
    )
    TEXT_STATUS_DEFAULT = "Aguardando acao do usuario..."
    TEXT_STATUS_INICIANDO = "Iniciando processamento..."
    TEXT_STATUS_ABRINDO_PDF = "Abrindo arquivo PDF..."

    TEXT_SUCESSO_CONVERSAO = "Conversao concluida com sucesso!"
    TEXT_SUCESSO_ARQUIVO_SALVO = "Arquivo salvo em:"
    TEXT_SUCESSO_ABRIR_DOWNLOADS = "Abrir pasta de downloads?"

    TEXT_ERRO_PDF_INVALIDO = "PDF invalido."
    TEXT_ERRO_CNPJ_INVALIDO = "CNPJ deve ter {digitos} digitos."
    TEXT_ERRO_MES_NAO_SELECIONADO = "Selecione o mes de referencia."
    TEXT_ERRO_ANO_INVALIDO = "Ano deve ter 4 digitos (ex: 2025)."
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
    }

    THEME_MODE = "Dark"
    THEME_COLOR = "blue"

    FILE_TYPES_PDF = [("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
    FILE_TYPES_TXT = [("Arquivos TXT", "*.txt"), ("Todos os arquivos", "*.*")]
    DIALOG_TITLE_PDF = "Selecione o arquivo PDF"
    DIALOG_TITLE_TXT = "Selecione o TXT corrigido"
    DIALOG_TITLE_SUCESSO = "Sucesso"
    DIALOG_TITLE_ERRO = "Erro na Conversao"
    DIALOG_TITLE_AVISO = "Aviso"

    FORMATO_NOME_ARQUIVO = "M{ano}{mes}{cnpj}.txt"

    FONT_FAMILY_TITLE = "Roboto"
    FONT_FAMILY_LOGS = "Consolas"

