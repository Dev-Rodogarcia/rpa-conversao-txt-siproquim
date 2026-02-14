"""
Módulo responsável pela extração de campos específicos de textos.
Contém funções utilitárias para extrair CNPJ, nomes, datas, etc.
"""

import itertools
import re
from typing import Optional

# Importa constantes compartilhadas
try:
    from ..gerador.layout_constants import CNPJ_TAMANHO, CNPJ_VAZIO
    from ..gerador.validators import validar_cnpj, validar_cpf
except (ImportError, ValueError):
    # Fallback se importação circular - calcula dinamicamente
    CNPJ_TAMANHO = 14
    CNPJ_VAZIO = "0" * CNPJ_TAMANHO

    def validar_cnpj(_: str) -> bool:
        return False

    def validar_cpf(_: str) -> bool:
        return False


def limpar_cnpj_cpf(texto: str) -> str:
    """
    Remove pontuação de CNPJ/CPF.
    
    Args:
        texto: Texto contendo CNPJ/CPF
    
    Returns:
        CNPJ/CPF apenas com números
    """
    if not texto:
        return ""
    return re.sub(r'[^\d]', '', str(texto))


_MAPA_OCR_DIGITOS = str.maketrans({
    "O": "0",
    "Q": "0",
    "D": "0",
    "I": "1",
    "L": "1",
    "|": "1",
    "!": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "G": "6",
    "T": "7",
})


def _subsequencias(valor: str, tamanho: int, limite: int) -> list[str]:
    """Gera subsequencias em ordem, com limite para evitar explosao combinatoria."""
    if len(valor) < tamanho:
        return []
    if len(valor) == tamanho:
        return [valor]

    resultado = []
    for idxs in itertools.combinations(range(len(valor)), tamanho):
        resultado.append(''.join(valor[i] for i in idxs))
        if len(resultado) >= limite:
            break
    return resultado


def _extrair_cnpj_ocr_ruidoso(texto: str) -> Optional[str]:
    """
    Tenta recuperar CNPJ em texto com OCR ruidoso.

    Regra de seguranca: so retorna quando houver exatamente um candidato valido.
    """
    if not texto:
        return None

    texto_norm = str(texto).upper().translate(_MAPA_OCR_DIGITOS)

    # Mantem delimitadores visuais entre "palavras" para evitar colar CNPJ com telefone.
    texto_filtrado = ''.join(
        ch if (ch.isdigit() or ch in './-') else ' '
        for ch in texto_norm
    )
    texto_filtrado = re.sub(r'\s+', ' ', texto_filtrado).strip()
    if not texto_filtrado:
        return None

    candidatos_validos = set()
    padrao_token = re.compile(r'^(\d{2,8})\.(\d{3,8})\.(\d{3,8})/(\d{4,8})-(\d{2,8})$')

    tokens = texto_filtrado.split(' ')
    for idx, token in enumerate(tokens):
        candidatos_token = [token]
        # OCR comum: primeiro bloco separado, ex. "201 .512.682/0001-91".
        if token.startswith('.') and idx > 0 and tokens[idx - 1].isdigit():
            candidatos_token.append(tokens[idx - 1] + token)

        for token_candidato in candidatos_token:
            if token_candidato.count('.') < 2 or '/' not in token_candidato or '-' not in token_candidato:
                continue

            # Normaliza espacos ao redor de separadores.
            token_candidato = re.sub(r'\s*([./-])\s*', r'\1', token_candidato).strip(".,;:")
            match_token = padrao_token.match(token_candidato)
            if not match_token:
                continue

            grupo1, grupo2, grupo3, grupo4, grupo5 = match_token.groups()
            if len(grupo1) < 2 or len(grupo2) < 3 or len(grupo3) < 3 or len(grupo4) < 4 or len(grupo5) < 2:
                continue

            partes1 = _subsequencias(grupo1, 2, limite=28)
            partes2 = _subsequencias(grupo2, 3, limite=56)
            partes3 = _subsequencias(grupo3, 3, limite=56)
            partes4 = _subsequencias(grupo4, 4, limite=70)
            partes5 = _subsequencias(grupo5, 2, limite=28)

            tentativas = 0
            for p1 in partes1:
                for p2 in partes2:
                    for p3 in partes3:
                        for p4 in partes4:
                            for p5 in partes5:
                                tentativas += 1
                                candidato = f"{p1}{p2}{p3}{p4}{p5}"
                                if validar_cnpj(candidato):
                                    candidatos_validos.add(candidato)
                                if tentativas >= 45000:
                                    break
                            if tentativas >= 45000:
                                break
                        if tentativas >= 45000:
                            break
                    if tentativas >= 45000:
                        break
                if tentativas >= 45000:
                    break
            if tentativas >= 45000:
                break

    if len(candidatos_validos) == 1:
        return next(iter(candidatos_validos))
    return None


def extrair_cnpj_do_texto(texto: str) -> Optional[str]:
    """
    Extrai CNPJ/CPF de um texto usando múltiplas estratégias (robustez).
    
    Estratégias (em ordem de prioridade):
    1. Busca padrão formatado: "CNPJ/CPF: XX.XXX.XXX/XXXX-XX" ou "CNPJ/CPF: XXX.XXX.XXX-XX" (CPF)
    2. Busca padrão formatado solto: "XX.XXX.XXX/XXXX-XX" (CNPJ) ou "XXX.XXX.XXX-XX" (CPF)
    3. Busca sequência de 11 dígitos (CPF) ou 14 dígitos (CNPJ) com validação para evitar pegar telefone
    
    Args:
        texto: Texto que pode conter CNPJ/CPF
    
    Returns:
        CNPJ/CPF limpo (apenas números) ou None
    """
    if not texto:
        return None
    
    # Estratégia 1: Busca padrão "CNPJ/CPF: XX.XXX.XXX/XXXX-XX" ou "CNPJ/CPF: XXX.XXX.XXX-XX"
    # CRÍTICO: Para na primeira ocorrência e não continua para pegar telefone
    # Busca CPF formatado primeiro (11 dígitos: XXX.XXX.XXX-XX)
    match_cpf = re.search(r'CNPJ/CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})(?:\s|$|[^\d])', texto, re.IGNORECASE)
    if match_cpf:
        cpf_limpo = limpar_cnpj_cpf(match_cpf.group(1))
        if len(cpf_limpo) == 11 and validar_cpf(cpf_limpo):
            return cpf_limpo
    
    # Busca CNPJ formatado (14 dígitos: XX.XXX.XXX/XXXX-XX)
    match_cnpj = re.search(r'CNPJ/CPF:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})(?:\s|$|[^\d])', texto, re.IGNORECASE)
    if match_cnpj:
        cnpj_limpo = limpar_cnpj_cpf(match_cnpj.group(1))
        if len(cnpj_limpo) == CNPJ_TAMANHO:  # Valida tamanho
            return cnpj_limpo
    
    # Busca padrão mais genérico mas ainda limitado (para na primeira ocorrência válida)
    match = re.search(r'CNPJ/CPF:\s*([\d./-]+?)(?:\s|$|[^\d./-])', texto, re.IGNORECASE)
    if match:
        cnpj_limpo = limpar_cnpj_cpf(match.group(1))
        # Aceita CPF (11 dígitos) ou CNPJ (14 dígitos)
        if len(cnpj_limpo) == 11:
            if validar_cpf(cnpj_limpo):
                return cnpj_limpo
        elif len(cnpj_limpo) == CNPJ_TAMANHO:
            return cnpj_limpo
    
    # Estratégia 2: Busca padrão formatado solto "XX.XXX.XXX/XXXX-XX" (CNPJ) ou "XXX.XXX.XXX-XX" (CPF)
    # Aceita variações: com/sem pontos, com/sem barra, com/sem hífen
    padroes_formatados = [
        r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}',  # 92.660.406/0076-36 (CNPJ)
        r'\d{2}\.\d{3}\.\d{3}/\d{4}',         # 92.660.406/0076 (CNPJ sem dígito verificador)
        r'\d{3}\.\d{3}\.\d{3}-\d{2}',         # 413.030.828-96 (CPF)
        r'\d{2}\.\d{3}\.\d{3}\.\d{4}-\d{2}', # Formato alternativo CNPJ
    ]
    
    for padrao in padroes_formatados:
        match = re.search(padrao, texto)
        if match:
            cnpj_limpo = limpar_cnpj_cpf(match.group(0))
            if len(cnpj_limpo) == 11:
                if validar_cpf(cnpj_limpo):
                    return cnpj_limpo
            elif len(cnpj_limpo) == CNPJ_TAMANHO:
                return cnpj_limpo
    
    # Estratégia 3: Busca sequências de dígitos, mas com validação para evitar pegar CPF + telefone
    # Primeiro tenta encontrar CPF (11 dígitos) formatado ou não
    # Divide o texto por linhas para evitar pegar CPF de uma linha + telefone de outra
    linhas = texto.split('\n')
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        
        # Busca CPF formatado na linha (XXX.XXX.XXX-XX)
        match_cpf_linha = re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', linha)
        if match_cpf_linha:
            cpf_limpo = limpar_cnpj_cpf(match_cpf_linha.group(1))
            if len(cpf_limpo) == 11 and validar_cpf(cpf_limpo):
                return cpf_limpo
        
        # Busca CNPJ formatado na linha (XX.XXX.XXX/XXXX-XX)
        match_cnpj_linha = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', linha)
        if match_cnpj_linha:
            cnpj_limpo = limpar_cnpj_cpf(match_cnpj_linha.group(1))
            if len(cnpj_limpo) == CNPJ_TAMANHO:
                return cnpj_limpo
        
        # Busca CPF não formatado (11 dígitos) mas para antes de telefone
        # Procura por padrão que pare antes de sequências longas de dígitos (telefone)
        match_cpf_raw = re.search(r'(?:CNPJ/CPF|CPF)[:\s]*(\d{11})(?:\s|$|[^\d]|FONE|TELEFONE)', linha, re.IGNORECASE)
        if match_cpf_raw:
            cpf_limpo = match_cpf_raw.group(1)
            if len(cpf_limpo) == 11 and validar_cpf(cpf_limpo):
                return cpf_limpo
        
        # Busca CNPJ não formatado (14 dígitos) mas para antes de telefone
        match_cnpj_raw = re.search(r'(?:CNPJ/CPF|CNPJ)[:\s]*(\d{14})(?:\s|$|[^\d]|FONE|TELEFONE)', linha, re.IGNORECASE)
        if match_cnpj_raw:
            cnpj_limpo = match_cnpj_raw.group(1)
            if len(cnpj_limpo) == CNPJ_TAMANHO:
                return cnpj_limpo
    
    # Estratégia 4: Busca sequências de dígitos no texto completo, mas com cuidado
    # Remove pontuação primeiro para facilitar busca
    texto_sem_pontuacao = re.sub(r'[^\d\s]', ' ', texto)
    
    # Busca CPF primeiro (11 dígitos) - mais comum que CNPJ
    # Só aceita quando houver contexto de documento e não de telefone.
    tem_contexto_doc = bool(re.search(r'(CNPJ/CPF|CNPJ|CPF)', texto, re.IGNORECASE))
    tem_contexto_fone = bool(re.search(r'(FONE|TELEFONE)', texto, re.IGNORECASE))
    match_cpf = re.search(r'(?:^|\s)(\d{11})(?:\s|$)', texto_sem_pontuacao)
    if match_cpf:
        cpf_candidato = match_cpf.group(1)
        if tem_contexto_doc and not tem_contexto_fone and validar_cpf(cpf_candidato):
            return cpf_candidato
    
    # Busca CNPJ (14 dígitos) - prioriza candidatos válidos por checksum
    candidatos_cnpj = re.findall(r'(?:^|\s)(\d{14})(?:\s|$)', texto_sem_pontuacao)
    cnpjs_filtrados = []
    for candidato in candidatos_cnpj:
        # Validação básica: não pode ser tudo zeros ou começar com 00
        if (candidato != CNPJ_VAZIO and
            not candidato.startswith('00') and
            not (len(candidato) == 14 and candidato[:11] != "0" * 11 and
                 candidato[11:14].startswith(('14', '15', '16', '17', '18', '19')))):
            cnpjs_filtrados.append(candidato)
    for candidato in cnpjs_filtrados:
        if validar_cnpj(candidato):
            return candidato
    if cnpjs_filtrados:
        return cnpjs_filtrados[0]
    
    # Estratégia 5: Busca sequências de CNPJ_TAMANHO dígitos próximas a palavras-chave
    # Para casos extremos onde o CNPJ está quebrado
    contexto_cnpj = re.search(rf'(?:CNPJ|EMITENTE|DESTINAT[ÁA]RIO|CONTRANTE).*?(\d{{{CNPJ_TAMANHO}}})(?:\s|$|[^\d]|FONE|TELEFONE)', 
                              texto, re.IGNORECASE | re.DOTALL)
    if contexto_cnpj:
        cnpj_candidato = limpar_cnpj_cpf(contexto_cnpj.group(1))
        if len(cnpj_candidato) == CNPJ_TAMANHO:
            # Validação básica: não pode ser tudo zeros ou começar com 000 (provavelmente CPF)
            if cnpj_candidato != CNPJ_VAZIO and not cnpj_candidato.startswith('000'):
                return cnpj_candidato

    # Estratégia 6: OCR ruidoso (só retorna quando há candidato único válido).
    cnpj_ocr = _extrair_cnpj_ocr_ruidoso(texto)
    if cnpj_ocr:
        return cnpj_ocr

    return None


def extrair_nome_do_texto(texto: str) -> Optional[str]:
    """
    Extrai APENAS a Razão Social, descartando endereços, CNPJs e outras informações.
    CRÍTICO: Pega apenas a primeira linha válida após o rótulo, ignorando o resto.
    
    Estratégia:
    1. Divide o texto por linhas
    2. Pega a primeira linha que não contém CNPJ, endereço, telefone, etc.
    3. Remove qualquer "lixo" que possa ter vindo junto (CNPJ parcial, códigos)
    
    Args:
        texto: Texto que pode conter nome/razão social
    
    Returns:
        Apenas a razão social limpa (sem endereço, CNPJ, etc.) ou None
    """
    if not texto:
        return None

    def linha_e_metadado(linha: str) -> bool:
        linha_upper = linha.upper().strip()
        if not linha_upper:
            return True

        # Campos técnicos/documentais.
        if re.search(r'\b(CNPJ/CPF|CNPJ|CPF|FONE|TELEFONE|CEP|CT-?E|RECEBEDOR)\b', linha_upper):
            return True
        if re.search(r'^\s*N[º°]?\s*CT', linha_upper):
            return True
        if re.search(r'^\s*DATA\b', linha_upper):
            return True

        # Campos de endereço: usa fronteira de palavra para evitar falsos positivos
        # em nomes como "PROMOTORA DE VENDAS" / "CIDADE IMPERIAL".
        if re.search(r'^\s*(END|ENDERECO|LOGRADOURO|RUA|AV\.?|AVENIDA|ROD\.?|RODOVIA|BAIRRO|CIDADE|UF)\b', linha_upper):
            return True

        # Datas isoladas / linhas numéricas.
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', linha_upper):
            return True
        if re.match(r'^\d+$', linha_upper):
            return True

        return False

    linhas = str(texto).split('\n')
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue

        # Remove rótulos do início da linha, preservando o conteúdo real.
        linha = re.sub(
            r'^\s*(EMITENTE|DESTINAT[ÁA]RIO|CONTRANTE|CONTRATANTE)\s*:?\s*',
            '',
            linha,
            flags=re.IGNORECASE
        ).strip()
        if not linha or linha_e_metadado(linha):
            continue

        nome_limpo = linha
        # Corta o trecho quando começa conteúdo técnico.
        nome_limpo = re.split(r'\b(?:CNPJ/CPF|CNPJ|CPF|FONE|TELEFONE|CEP)\b', nome_limpo, flags=re.IGNORECASE)[0]
        # Remove sufixos comuns de tabela/cidade após pipe.
        nome_limpo = re.sub(r'\s*\|\s*.*$', '', nome_limpo)
        # Remove códigos numéricos no final (ex.: 0076-36, 0042-97).
        nome_limpo = re.sub(r'\s+\d{4}-\d{2}.*$', '', nome_limpo)
        # Remove número puro residual no fim.
        nome_limpo = re.sub(r'\s+\d+$', '', nome_limpo)
        nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip(" -|")

        if nome_limpo and len(nome_limpo) >= 3 and not re.match(r'^[\d\s\.\-/]+$', nome_limpo):
            return nome_limpo

    return None


def extrair_numero_cte(texto: str) -> Optional[str]:
    """
    Extrai número do CTe de um texto.
    
    Args:
        texto: Texto que pode conter número do CTe
    
    Returns:
        Número do CTe ou None
    """
    if not texto:
        return None
    
    match = re.search(r'N[º°]?\s*CT-?E\s*:?\s*(\d+)', texto, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extrair_data_cte(texto: str) -> Optional[str]:
    """
    Extrai data do CTe de um texto.
    
    Args:
        texto: Texto que pode conter data do CTe
    
    Returns:
        Data no formato dd/mm/aaaa ou None
    """
    if not texto:
        return None
    
    match = re.search(r'DATA\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', texto, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extrair_data_entrega(texto: str) -> Optional[str]:
    """
    Extrai data de entrega de um texto.
    
    Args:
        texto: Texto que pode conter data de entrega
    
    Returns:
        Data no formato dd/mm/aaaa ou None
    """
    if not texto:
        return None
    
    # Procura padrão "DATA ENTREGA: dd/mm/aaaa"
    match = re.search(r'DATA\s*ENTREGA\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', texto, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Tenta buscar data com hora (ex: "05/01/2026 18:26")
    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\s+\d{1,2}:\d{2}', texto)
    if match:
        return match.group(1)
    
    return None


def extrair_recebedor(texto: str) -> Optional[str]:
    """
    Extrai nome do recebedor de um texto.
    Busca em múltiplos padrões para encontrar o recebedor.
    
    Args:
        texto: Texto que pode conter nome do recebedor
    
    Returns:
        Nome do recebedor limpo ou None
    """
    if not texto:
        return None
    
    # Padrão 1: "RECEBEDOR: Nome" ou "RECEBEDOR Nome"
    match = re.search(r'RECEBEDOR\s*:?\s*([^\n]+?)(?:\s*DATA\s*ENTREGA|$)', texto, re.IGNORECASE)
    if match:
        recebedor = match.group(1).strip()
        # Remove "DATA ENTREGA:" se aparecer
        recebedor = re.sub(r'\s*DATA\s*ENTREGA\s*:?\s*.*$', '', recebedor, flags=re.IGNORECASE)
        recebedor = recebedor.strip()
        
        if recebedor and recebedor.upper() not in ['', 'NONE', 'NULL', 'DATA ENTREGA:']:
            return recebedor
    
    # Padrão 2: Busca por "RESPONSAVEL" ou "RESPONSÁVEL" (variações)
    match = re.search(r'RESPONS[ÁA]VEL\s*(?:PELO\s*)?(?:RECEBIMENTO|RECEBEDOR)?\s*:?\s*([^\n]+)', texto, re.IGNORECASE)
    if match:
        recebedor = match.group(1).strip()
        if recebedor and recebedor.upper() not in ['', 'NONE', 'NULL']:
            return recebedor
    
    # Padrão 3: Busca por "RECEBIDO POR" ou "RECEBIDO EM"
    match = re.search(r'RECEBIDO\s*(?:POR|EM)\s*:?\s*([^\n]+)', texto, re.IGNORECASE)
    if match:
        recebedor = match.group(1).strip()
        if recebedor and recebedor.upper() not in ['', 'NONE', 'NULL']:
            return recebedor
    
    return None
