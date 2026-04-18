"""
Constantes de layout para geração de arquivos TXT no formato SIPROQUIM.
Centraliza todas as definições de posições, tamanhos e valores fixos para evitar duplicação e erros.
"""

# ============================================================================
# SEÇÃO EM (Identificação da Empresa/Mapa) - Layout 3.1.1
# ============================================================================

# Tamanho total da linha EM
EM_TAMANHO_TOTAL = 31

# Posições dos campos na linha EM
EM_POS_TIPO = (1, 2)              # Pos 1-2: Tipo "EM"
EM_POS_CNPJ = (3, 16)             # Pos 3-16: CNPJ (14 chars)
EM_POS_MES = (17, 19)             # Pos 17-19: Mês (3 chars alfanumérico: JAN, FEV, etc.)
EM_POS_ANO = (20, 23)             # Pos 20-23: Ano (4 chars)
EM_POS_COM_NACIONAL = (24, 24)    # Pos 24: Comercialização Nacional (1 char)
EM_POS_COM_INTERNACIONAL = (25, 25)  # Pos 25: Comercialização Internacional (1 char)
EM_POS_PRODUCAO = (26, 26)        # Pos 26: Produção (1 char)
EM_POS_TRANSFORMACAO = (27, 27)   # Pos 27: Transformação (1 char)
EM_POS_CONSUMO = (28, 28)         # Pos 28: Consumo (1 char)
EM_POS_FABRICACAO = (29, 29)      # Pos 29: Fabricação (1 char)
EM_POS_TRANSPORTE = (30, 30)      # Pos 30: Transporte (1 char)
EM_POS_ARMAZENAMENTO = (31, 31)  # Pos 31: Armazenamento (1 char)

# Tamanhos dos campos EM
EM_TAM_TIPO = 2
EM_TAM_CNPJ = 14
EM_TAM_MES = 3
EM_TAM_ANO = 4
EM_TAM_FLAGS = 8  # Total de flags (pos 24-31)

# Valores fixos
EM_TIPO = "EM"

# Mapeamento de mês numérico para alfanumérico
MESES_ALFANUMERICOS = {
    1: "JAN",
    2: "FEV",
    3: "MAR",
    4: "ABR",
    5: "MAI",
    6: "JUN",
    7: "JUL",
    8: "AGO",
    9: "SET",
    10: "OUT",
    11: "NOV",
    12: "DEZ"
}

# Flags padrão para Transporte Nacional (apenas Transporte = 1)
EM_FLAGS_TRANSPORTE_NACIONAL = {
    'comercializacao_nacional': '0',
    'comercializacao_internacional': '0',
    'producao': '0',
    'transformacao': '0',
    'consumo': '0',
    'fabricacao': '0',
    'transporte': '1',  # Sempre 1 para este projeto
    'armazenamento': '0'
}


# ============================================================================
# SEÇÃO TN (Transporte Nacional) - Layout 3.1.9
# ============================================================================

# Tamanho total da linha TN
TN_TAMANHO_TOTAL = 276

# Posições dos campos na linha TN
TN_POS_TIPO = (1, 2)                  # Pos 1-2: Tipo "TN"
TN_POS_CNPJ_CONTRATANTE = (3, 16)     # Pos 3-16: CNPJ Contratante (14 chars)
TN_POS_NOME_CONTRATANTE = (17, 86)    # Pos 17-86: Nome Contratante (70 chars)
TN_POS_NF_NUMERO = (87, 96)           # Pos 87-96: Número NF (10 chars)
TN_POS_NF_DATA = (97, 106)            # Pos 97-106: Data NF (10 chars)
TN_POS_CNPJ_ORIGEM = (107, 120)       # Pos 107-120: CNPJ Origem (14 chars)
TN_POS_NOME_ORIGEM = (121, 190)       # Pos 121-190: Nome Origem (70 chars)
TN_POS_CNPJ_DESTINO = (191, 204)      # Pos 191-204: CNPJ Destino (14 chars)
TN_POS_NOME_DESTINO = (205, 274)      # Pos 205-274: Nome Destino (70 chars)
TN_POS_LOCAL_RETIRADA = (275, 275)    # Pos 275: Local Retirada (1 char)
TN_POS_LOCAL_ENTREGA = (276, 276)     # Pos 276: Local Entrega (1 char)

# Tamanhos dos campos TN
TN_TAM_TIPO = 2
TN_TAM_CNPJ = 14
TN_TAM_NOME = 70
TN_TAM_NF_NUMERO = 10
TN_TAM_NF_DATA = 10
TN_TAM_LOCAL = 1

# Valores fixos
TN_TIPO = "TN"
TN_LOCAL_PROPRIO = "P"


# ============================================================================
# SEÇÃO CC (Conhecimento de Carga) - Layout 3.1.9.1
# ============================================================================

# Tamanho total da linha CC
CC_TAMANHO_TOTAL = 103
CC_TAMANHO_MINIMO = CC_TAMANHO_TOTAL

# Posições dos campos na linha CC
CC_POS_TIPO = (1, 2)                  # Pos 1-2: Tipo "CC"
CC_POS_CTE_NUMERO = (3, 11)           # Pos 3-11: Número CTe (9 chars)
CC_POS_CTE_DATA = (12, 21)            # Pos 12-21: Data CTe (10 chars)
CC_POS_DATA_RECEBIMENTO = (22, 31)    # Pos 22-31: Data Recebimento (10 chars)
CC_POS_RECEBEDOR = (32, 101)          # Pos 32-101: Responsável Recebimento (70 chars)
CC_POS_MODAL = (102, 103)             # Pos 102-103: Modal (2 chars)

# Tamanhos dos campos CC
CC_TAM_TIPO = 2
CC_TAM_CTE_NUMERO = 9
CC_TAM_DATA = 10
CC_TAM_RECEBEDOR = 70
CC_TAM_MODAL = 2

# Valores fixos
CC_TIPO = "CC"
CC_MODAL_RODOVIARIO = "RO"
CC_MODAIS_VALIDOS = {"RO", "AQ", "FE", "AE"}


# ============================================================================
# SECAO TI (Transporte Internacional) - Layout 3.1.10
# ============================================================================

# Tamanho total da linha TI
TI_TAMANHO_TOTAL = 109

# Posicoes dos campos na linha TI
TI_POS_TIPO = (1, 2)                    # Pos 1-2: Tipo "TI"
TI_POS_OPERACAO = (3, 3)                # Pos 3: (E)xportacao ou (I)mportacao
TI_POS_CONTRATANTE = (4, 4)             # Pos 4: (O)rigem ou (D)estino da carga
TI_POS_NF_NUMERO = (5, 14)              # Pos 5-14: Numero NF (10 chars)
TI_POS_NF_DATA = (15, 24)               # Pos 15-24: Data NF (10 chars)
TI_POS_CNPJ_EMPRESA = (25, 38)          # Pos 25-38: CPF/CNPJ Empresa (14 chars)
TI_POS_NOME_EMPRESA = (39, 108)         # Pos 39-108: Nome Empresa (70 chars)
TI_POS_LOCAL_ARMAZENAMENTO = (109, 109) # Pos 109: P ou A

# Tamanhos dos campos TI
TI_TAM_TIPO = 2
TI_TAM_OPERACAO = 1
TI_TAM_CONTRATANTE = 1
TI_TAM_NF_NUMERO = 10
TI_TAM_NF_DATA = 10
TI_TAM_CNPJ = 14
TI_TAM_NOME = 70
TI_TAM_LOCAL = 1

# Valores fixos/permitidos TI
TI_TIPO = "TI"
TI_OPERACOES_VALIDAS = {"E", "I"}
TI_CONTRATANTES_VALIDOS = {"O", "D"}
TI_LOCAIS_ARMAZENAMENTO_VALIDOS = {"P", "A"}
TI_OPERACAO_EXPORTACAO = "E"
TI_OPERACAO_IMPORTACAO = "I"
TI_CONTRATANTE_ORIGEM = "O"
TI_CONTRATANTE_DESTINO = "D"
TI_LOCAL_PROPRIO = "P"
TI_LOCAL_ARMAZENAGEM_TERCEIRIZADA = "A"


# ============================================================================
# SUBSECAO LA (Armazenamento do Transporte Internacional) - Layout 3.1.10.1
# ============================================================================

LA_TAMANHO_TOTAL = 86
LA_TIPO = "LA"


# ============================================================================
# SUBSECAO PI (Pessoa Internacional) - Layout 3.1.10.2
# ============================================================================

PI_TAMANHO_TOTAL = 145

PI_POS_TIPO = (1, 2)              # Pos 1-2: Tipo "PI"
PI_POS_NOME_EMPRESA = (3, 72)     # Pos 3-72: Nome Empresa (70 chars)
PI_POS_PAIS_ID = (73, 75)         # Pos 73-75: Id do pais (3 chars)
PI_POS_ENDERECO = (76, 145)       # Pos 76-145: Endereco completo (70 chars)

PI_TAM_TIPO = 2
PI_TAM_NOME = 70
PI_TAM_PAIS_ID = 3
PI_TAM_ENDERECO = 70

PI_TIPO = "PI"


# ============================================================================
# SUBSECOES LR/LE (Transporte Nacional com armazenagem terceirizada)
# ============================================================================

# Tamanho total das linhas LR e LE
LR_TAMANHO_TOTAL = 86
LE_TAMANHO_TOTAL = 86

# Valores fixos
LR_TIPO = "LR"
LE_TIPO = "LE"


# ============================================================================
# CONSTANTES DE VALIDAÇÃO
# ============================================================================

# Validação de mês
MES_MINIMO = 1
MES_MAXIMO = 12

# Validação de ano
ANO_MINIMO = 2000
ANO_MAXIMO = 2100

# ============================================================================
# CONSTANTES COMPARTILHADAS
# ============================================================================

# Tamanho padrão de CNPJ (14 dígitos)
CNPJ_TAMANHO = 14

# Tamanho padrão de CPF (11 dígitos)
CPF_TAMANHO = 11

# Valor padrão para CNPJ vazio
CNPJ_VAZIO = "0" * CNPJ_TAMANHO

# Valor padrão para recebedor não informado
RECEBEDOR_NAO_INFORMADO = "NAO INFORMADO"

# ============================================================================
# FUNÇÕES HELPER
# ============================================================================

def mes_numero_para_alfanumerico(mes: int) -> str:
    """
    Converte mês numérico (1-12) para formato alfanumérico (JAN, FEV, etc.).
    
    Args:
        mes: Número do mês (1-12)
    
    Returns:
        String com o mês em formato alfanumérico (JAN, FEV, MAR, etc.)
    
    Raises:
        ValueError: Se o mês estiver fora do intervalo 1-12
    """
    if not (1 <= mes <= 12):
        raise ValueError(f"Mês deve estar entre 1 e 12, recebido: {mes}")
    return MESES_ALFANUMERICOS[mes]


def gerar_flags_em(transporte: bool = True, **kwargs) -> str:
    """
    Gera string de flags para a seção EM.
    
    Ordem dos flags (pos 24-31):
    - Pos 24: Comercialização Nacional
    - Pos 25: Comercialização Internacional
    - Pos 26: Produção
    - Pos 27: Transformação
    - Pos 28: Consumo
    - Pos 29: Fabricação
    - Pos 30: Transporte
    - Pos 31: Armazenamento
    
    Args:
        transporte: Se True, flag de transporte será '1' (padrão)
        **kwargs: Outros flags opcionais (comercializacao_nacional, producao, etc.)
    
    Returns:
        String com 8 caracteres representando os flags (pos 24-31)
        Padrão para Transporte Nacional: "00000010" (apenas Transporte = 1 na posição 30)
    """
    flags = EM_FLAGS_TRANSPORTE_NACIONAL.copy()
    
    # Atualiza flags com valores fornecidos
    for key, value in kwargs.items():
        if key in flags:
            flags[key] = '1' if value else '0'
    
    # Garante que transporte seja sempre 1 para este projeto
    if transporte:
        flags['transporte'] = '1'
    
    # Retorna string na ordem correta conforme manual: CN, CI, P, T, C, F, TR, AR
    # Padrão: 00000010 (apenas Transporte na posição 30 = 7º caractere, índice 6)
    return (
        flags['comercializacao_nacional'] +      # Pos 24
        flags['comercializacao_internacional'] +  # Pos 25
        flags['producao'] +                       # Pos 26
        flags['transformacao'] +                  # Pos 27
        flags['consumo'] +                        # Pos 28
        flags['fabricacao'] +                     # Pos 29
        flags['transporte'] +                     # Pos 30 (sempre 1 para este projeto)
        flags['armazenamento']                    # Pos 31
    )
