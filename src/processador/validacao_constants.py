"""
Constantes para validação de campos extraídos do PDF.
Define limites, formatos e padrões esperados para cada campo crítico.
"""

import re
from typing import Pattern

# ============================================================================
# CONSTANTES DE TAMANHO
# ============================================================================

# NF (Nota Fiscal)
NF_NUMERO_MIN_DIGITOS = 4
NF_NUMERO_MAX_DIGITOS = 6

# CTe (Conhecimento de Transporte)
CTE_NUMERO_MIN_DIGITOS = 1
CTE_NUMERO_MAX_DIGITOS = 9

# CNPJs/CPFs
CNPJ_TAMANHO = 14
CPF_TAMANHO = 11

# Nomes/Razões Sociais
NOME_MIN_CARACTERES = 3
NOME_MAX_CARACTERES = 70

# Recebedor
RECEBEDOR_MIN_CARACTERES = 3
RECEBEDOR_MAX_CARACTERES = 70

# ============================================================================
# PADRÕES REGEX
# ============================================================================

# Padrão de data brasileiro: dd/mm/aaaa (aceita 1 ou 2 dígitos para dia/mês)
PATTERN_DATA_BR: Pattern = re.compile(r'^\d{1,2}/\d{1,2}/\d{4}$')

# Padrão de NF: 4 a 6 dígitos numéricos
PATTERN_NF_NUMERO: Pattern = re.compile(rf'^\d{{{NF_NUMERO_MIN_DIGITOS},{NF_NUMERO_MAX_DIGITOS}}}$')

# Padrão de CTe: 1 a 9 dígitos numéricos
PATTERN_CTE_NUMERO: Pattern = re.compile(rf'^\d{{{CTE_NUMERO_MIN_DIGITOS},{CTE_NUMERO_MAX_DIGITOS}}}$')

# Padrão de CNPJ: exatamente 14 dígitos
PATTERN_CNPJ: Pattern = re.compile(rf'^\d{{{CNPJ_TAMANHO}}}$')

# Padrão de CPF: exatamente 11 dígitos
PATTERN_CPF: Pattern = re.compile(rf'^\d{{{CPF_TAMANHO}}}$')

# ============================================================================
# LABELS OBRIGATÓRIOS NO PDF (Para detecção de mudança de layout)
# ============================================================================

LABELS_OBRIGATORIOS_PDF = {
    'EMITENTE': r'EMITENTE',
    'DESTINATARIO': r'DESTINAT[ÁA]RIO',
    'CONTRATANTE': r'CONTRA[NT]E|CONTRANTE',
    'CTE': r'CT-?E|N[º°]\s*CT',
    'CNPJ_CPF': r'CNPJ[/\s]?CPF|CPF[/\s]?CNPJ|DOCUMENTO',
}

# ============================================================================
# MENSAGENS DE ERRO PADRONIZADAS
# ============================================================================

class MensagensErro:
    """Mensagens de erro padronizadas para validação."""
    
    # Erros de estrutura do PDF
    PDF_LAYOUT_MUDOU = "ERRO CRÍTICO: PDF não contém labels esperados: {labels_faltando}. Possível mudança de layout pela PF. Verifique o formato do PDF."
    
    # Erros de NF
    NF_NUMERO_VAZIO = "NF número está VAZIO"
    NF_NUMERO_INVALIDO = "NF número inválido: '{valor}' (esperado: {min}-{max} dígitos numéricos)"
    NF_DATA_VAZIA = "NF data está VAZIA"
    NF_DATA_FORMATO_INVALIDO = "NF data formato inválido: '{valor}' (esperado: dd/mm/aaaa)"
    NF_DATA_INVALIDA = "NF data inválida: '{valor}' (data não existe no calendário)"
    
    # Erros de CTe
    CTE_NUMERO_VAZIO = "CTe número está VAZIO"
    CTE_NUMERO_INVALIDO = "CTe número inválido: '{valor}' (esperado: {min}-{max} dígitos numéricos)"
    CTE_DATA_VAZIA = "CTe data está VAZIA"
    CTE_DATA_FORMATO_INVALIDO = "CTe data formato inválido: '{valor}' (esperado: dd/mm/aaaa)"
    CTE_DATA_INVALIDA = "CTe data inválida: '{valor}' (data não existe no calendário)"
    
    # Erros de CNPJ/CPF
    CNPJ_VAZIO = "{campo} está VAZIO"
    CNPJ_TAMANHO_INVALIDO = "{campo} tamanho inválido: {tamanho} dígitos (esperado: 11 para CPF ou 14 para CNPJ)"
    CPF_MODULO11_FALHOU = "{campo} CPF inválido: {valor} (não passa na validação Módulo 11)"
    CNPJ_MODULO11_FALHOU = "{campo} CNPJ inválido: {valor} (não passa na validação Módulo 11)"
    
    # Erros de Nome
    NOME_VAZIO = "{campo} está VAZIO"
    NOME_MUITO_CURTO = "{campo} muito curto: '{valor}' (mínimo: {min_chars} caracteres)"
    
    # Erros de Recebedor
    RECEBEDOR_VAZIO = "Recebedor está VAZIO (campo obrigatório no SIPROQUIM)"
    RECEBEDOR_MUITO_CURTO = "Recebedor muito curto: '{valor}' (mínimo: {min_chars} caracteres)"

# ============================================================================
# CONFIGURAÇÃO DE VALIDAÇÃO
# ============================================================================

class ConfigValidacao:
    """Configurações para controlar o comportamento da validação."""
    
    # Se True, validação lança exceção no primeiro erro (fail-fast)
    # Se False, coleta todos os erros e retorna lista completa
    FAIL_FAST = False
    
    # Se True, valida estrutura do PDF antes de extrair dados
    VALIDAR_ESTRUTURA_PDF = True
    
    # Se True, valida formato de datas (dd/mm/aaaa existe no calendário)
    VALIDAR_DATA_CALENDARIO = True
    
    # Se True, remove registros com erros críticos
    # Se False, apenas registra erros mas mantém registro (modo atual)
    REMOVER_REGISTROS_INVALIDOS = False
