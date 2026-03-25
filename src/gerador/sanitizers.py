"""
Módulo com funções de sanitização de dados.
Contém funções para limpar e formatar textos, números, etc.
"""

import re
import unidecode
from typing import Optional

from .validators import validar_cpf, validar_cnpj


def sanitizar_texto(texto: Optional[str], tamanho: int) -> str:
    """
    Remove acentos, converte para maiúscula e ajusta ao tamanho especificado.
    CRÍTICO: "Achata" o texto removendo TODAS as quebras de linha e espaços múltiplos.
    
    Esta função garante que nenhum campo contenha \n, \r, \t ou múltiplos espaços,
    evitando que o layout posicional seja quebrado.
    
    Args:
        texto: Texto a ser sanitizado (pode ser None)
        tamanho: Tamanho final do campo (preenche com espaços à direita)
    
    Returns:
        String sanitizada com tamanho fixo exato, SEM quebras de linha
    """
    if not texto:
        return " " * tamanho
    
    # 1. Converte para string primeiro (garante que é string)
    texto = str(texto)
    
    # 2. CRÍTICO: Remove quebras de linha ANTES de processar
    # Substitui explicitamente \n, \r, \t por espaço
    texto = texto.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # 3. Remove acentos e converte para maiúscula
    texto = unidecode.unidecode(texto).upper()
    
    # 4. O PULO DO GATO: Substitui QUALQUER sequência de espaços em branco
    # (múltiplos espaços) por um único espaço simples.
    # Isso "achata" o texto em uma linha só, eliminando quebras fantasma.
    texto_achatado = re.sub(r'\s+', ' ', texto)
    
    # 5. Remove espaços nas pontas
    texto_achatado = texto_achatado.strip()
    
    # 6. CRÍTICO: Corta PRIMEIRO, depois preenche (evita estouro)
    # Garantia final: remove qualquer caractere não imprimível que possa quebrar
    texto_final = ''.join(c for c in texto_achatado if c.isprintable() or c == ' ')
    texto_final = re.sub(r'\s+', ' ', texto_final).strip()
    
    return texto_final[:tamanho].ljust(tamanho)


def _identificar_tipo_documento(valor: str) -> str:
    """
    Identifica se um valor numérico é CPF ou CNPJ baseado apenas no tamanho.
    
    CRÍTICO: Não confunde CPF com CNPJ. Baseado apenas no tamanho:
    - 11 dígitos = CPF
    - 14 dígitos = CNPJ
    - Outros = DESCONHECIDO
    
    Args:
        valor: String numérica limpa (apenas dígitos)
    
    Returns:
        'CPF', 'CNPJ' ou 'DESCONHECIDO'
    """
    if len(valor) == 11:
        return 'CPF'
    elif len(valor) == 14:
        return 'CNPJ'
    else:
        return 'DESCONHECIDO'


def sanitizar_numerico(valor: Optional[str], tamanho: int) -> str:
    """
    Remove tudo que não for número e ajusta ao tamanho especificado.
    
    IMPORTANTE:
    - esta função é genérica para campos puramente numéricos
    - não deve ser usada para os campos mistos CPF/CNPJ do layout TN/LR/LE do SIPROQUIM,
      porque `zfill` em CPF cria um pseudo-CNPJ inválido
    
    Args:
        valor: Valor numérico a ser sanitizado (pode ser None)
        tamanho: Tamanho final do campo
    
    Returns:
        String numérica com tamanho fixo
    """
    if not valor:
        return "0" * tamanho
    
    nums = ''.join(filter(str.isdigit, str(valor)))
    
    # Identifica o tipo do documento (CPF ou CNPJ)
    tipo_doc = _identificar_tipo_documento(nums)
    
    # Se já tem o tamanho exato, retorna como está
    if len(nums) == tamanho:
        return nums
    
    # CRÍTICO: Se é CPF (11 dígitos) e precisa caber em campo de CNPJ (14 dígitos)
    # Preenche com zeros à esquerda (conforme manual técnico: campos numéricos preenchem à esquerda)
    # NOTA: O resultado NÃO será um CNPJ válido, mas é o formato exigido pelo layout.
    # A validação do CPF original deve ser feita ANTES desta formatação.
    if tipo_doc == 'CPF' and tamanho == 14:
        return nums.zfill(tamanho)
    
    # Se é CNPJ (14 dígitos) mas tamanho diferente, preenche à esquerda
    if tipo_doc == 'CNPJ':
        return nums.zfill(tamanho)
    
    # Outros casos: preenche com zeros à esquerda (padrão para campos numéricos)
    return nums.zfill(tamanho)


def sanitizar_documento(valor: Optional[str], tamanho: int, aceitar_cpf: bool = True) -> str:
    """
    Formata CPF/CNPJ para o layout posicional do SIPROQUIM.

    Regra prática observada no manual:
    - CNPJ válido permanece com 14 dígitos
    - CPF válido ocupa o campo de 14 posições com padding em branco à esquerda
      para não virar um pseudo-CNPJ inválido via `zfill`

    Args:
        valor: Documento bruto
        tamanho: Tamanho do campo no layout
        aceitar_cpf: Se True, aceita CPF válido além de CNPJ válido

    Returns:
        Documento pronto para o campo posicional

    Raises:
        ValueError: Quando o documento não é um CPF/CNPJ válido compatível
    """
    if tamanho < 14:
        raise ValueError(f"Campo de documento inválido: tamanho {tamanho} é menor que 14.")

    nums = ''.join(filter(str.isdigit, str(valor or '')))
    if not nums:
        return " " * tamanho

    if len(nums) == 14 and validar_cnpj(nums):
        return nums

    if aceitar_cpf and len(nums) == 11 and validar_cpf(nums):
        return nums.rjust(tamanho)

    raise ValueError(
        f"Documento inválido para o layout SIPROQUIM: '{valor}' -> '{nums}'."
    )


def sanitizar_alfanumerico(valor: Optional[str], tamanho: int) -> str:
    """
    Remove zeros à esquerda e ajusta ao tamanho (para campos alfanuméricos como NF).
    
    Args:
        valor: Valor alfanumérico a ser sanitizado
        tamanho: Tamanho final do campo
    
    Returns:
        String alfanumérica com tamanho fixo
    """
    if not valor:
        return " " * tamanho
    # Remove zeros à esquerda mas mantém o valor
    valor_str = str(valor).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').lstrip('0')
    if not valor_str:
        valor_str = "0"

    # Normaliza para ASCII e remove tudo que não for letra/número.
    valor_ascii = unidecode.unidecode(valor_str).upper()
    valor_limpo = re.sub(r'[^A-Z0-9]', '', valor_ascii)
    return valor_limpo[:tamanho].ljust(tamanho)
