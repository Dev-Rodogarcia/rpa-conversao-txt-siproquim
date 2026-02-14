"""
Parser simples para arquivos TXT no layout SIPROQUIM (EM/TN/CC).

Objetivo:
- Ler TXT gerado/corrigido no fluxo atual.
- Extrair campos estruturados das linhas TN e CC.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .layout_constants import (
    CC_POS_CTE_DATA,
    CC_POS_CTE_NUMERO,
    CC_POS_DATA_RECEBIMENTO,
    CC_POS_RECEBEDOR,
    CC_TAMANHO_TOTAL,
    CC_TIPO,
    TN_POS_CNPJ_CONTRATANTE,
    TN_POS_CNPJ_DESTINO,
    TN_POS_CNPJ_ORIGEM,
    TN_POS_LOCAL_ENTREGA,
    TN_POS_LOCAL_RETIRADA,
    TN_POS_NF_DATA,
    TN_POS_NF_NUMERO,
    TN_POS_NOME_CONTRATANTE,
    TN_POS_NOME_DESTINO,
    TN_POS_NOME_ORIGEM,
    TN_TAMANHO_TOTAL,
    TN_TIPO,
)


def _slice_posicional(linha: str, pos: tuple[int, int]) -> str:
    """Extrai substring por posicao 1-based inclusiva."""
    inicio, fim = pos
    return linha[inicio - 1:fim]


def _somente_digitos(valor: str) -> str:
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _ler_linhas(caminho_txt: str) -> List[str]:
    """
    Le linhas preservando espacos de preenchimento.

    Tenta UTF-8 primeiro (saida padrao do gerador) e cai para CP1252.
    """
    caminho = Path(caminho_txt)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo TXT nao encontrado: {caminho_txt}")

    erros: List[str] = []
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            with open(caminho, "r", encoding=encoding, newline="") as arquivo:
                return [linha.rstrip("\r\n") for linha in arquivo]
        except UnicodeDecodeError as exc:
            erros.append(f"{encoding}: {exc}")
            continue

    raise ValueError(f"Nao foi possivel ler {caminho_txt}. Tentativas: {' | '.join(erros)}")


def _parse_tn(linha: str, numero_linha: int) -> Dict[str, str]:
    linha_norm = linha if len(linha) >= TN_TAMANHO_TOTAL else linha.ljust(TN_TAMANHO_TOTAL)
    return {
        "tipo": TN_TIPO,
        "linha_numero": str(numero_linha),
        "contratante_cnpj": _somente_digitos(_slice_posicional(linha_norm, TN_POS_CNPJ_CONTRATANTE)),
        "contratante_nome": _slice_posicional(linha_norm, TN_POS_NOME_CONTRATANTE).strip(),
        "nf_numero": _slice_posicional(linha_norm, TN_POS_NF_NUMERO).strip(),
        "nf_data": _slice_posicional(linha_norm, TN_POS_NF_DATA).strip(),
        "emitente_cnpj": _somente_digitos(_slice_posicional(linha_norm, TN_POS_CNPJ_ORIGEM)),
        "emitente_nome": _slice_posicional(linha_norm, TN_POS_NOME_ORIGEM).strip(),
        "destinatario_cnpj": _somente_digitos(_slice_posicional(linha_norm, TN_POS_CNPJ_DESTINO)),
        "destinatario_nome": _slice_posicional(linha_norm, TN_POS_NOME_DESTINO).strip(),
        "local_retirada": _slice_posicional(linha_norm, TN_POS_LOCAL_RETIRADA).strip(),
        "local_entrega": _slice_posicional(linha_norm, TN_POS_LOCAL_ENTREGA).strip(),
    }


def _parse_cc(linha: str, numero_linha: int) -> Dict[str, str]:
    linha_norm = linha if len(linha) >= CC_TAMANHO_TOTAL else linha.ljust(CC_TAMANHO_TOTAL)
    return {
        "tipo": CC_TIPO,
        "linha_numero": str(numero_linha),
        "cte_numero": _slice_posicional(linha_norm, CC_POS_CTE_NUMERO).strip(),
        "cte_data": _slice_posicional(linha_norm, CC_POS_CTE_DATA).strip(),
        "data_recebimento": _slice_posicional(linha_norm, CC_POS_DATA_RECEBIMENTO).strip(),
        "recebedor": _slice_posicional(linha_norm, CC_POS_RECEBEDOR).strip(),
    }


def parse_txt_siproquim(caminho_txt: str) -> Dict[str, object]:
    """
    Faz parse de TXT SIPROQUIM e retorna dados estruturados.

    Retorno:
    {
      "tn": [...],
      "cc": [...],
      "invalidas": [{"linha_numero": int, "motivo": str}]
    }
    """
    linhas = _ler_linhas(caminho_txt)
    tn: List[Dict[str, str]] = []
    cc: List[Dict[str, str]] = []
    invalidas: List[Dict[str, object]] = []

    for idx, linha in enumerate(linhas, start=1):
        if not linha:
            continue
        prefixo = linha[:2].upper()
        if prefixo == TN_TIPO:
            try:
                tn.append(_parse_tn(linha, idx))
            except Exception as exc:
                invalidas.append({"linha_numero": idx, "motivo": f"Falha parse TN: {exc}"})
        elif prefixo == CC_TIPO:
            try:
                cc.append(_parse_cc(linha, idx))
            except Exception as exc:
                invalidas.append({"linha_numero": idx, "motivo": f"Falha parse CC: {exc}"})

    return {"tn": tn, "cc": cc, "invalidas": invalidas}


def parse_primeira_nf(caminho_txt: str) -> Optional[str]:
    """Helper util para verificacao rapida de arquivo."""
    dados = parse_txt_siproquim(caminho_txt)
    registros_tn = dados.get("tn", [])
    if not registros_tn:
        return None
    return str(registros_tn[0].get("nf_numero") or "").strip() or None
