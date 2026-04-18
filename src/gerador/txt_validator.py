"""
Validador estrutural para arquivos TXT no layout SIPROQUIM.

Foco atual:
- secoes EM, TN e CC
- subsecoes LR e LE quando TN usa armazenagem terceirizada

Objetivo:
- detectar localmente linhas truncadas/curtas antes do upload no SIPROQUIM
- reproduzir mensagens proximas do erro oficial quando possivel
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from .layout_constants import (
    CC_MODAIS_VALIDOS,
    CC_TAMANHO_MINIMO,
    CC_TIPO,
    EM_TAMANHO_TOTAL,
    EM_TIPO,
    LA_TAMANHO_TOTAL,
    LA_TIPO,
    LE_TAMANHO_TOTAL,
    LE_TIPO,
    LR_TAMANHO_TOTAL,
    LR_TIPO,
    PI_POS_ENDERECO,
    PI_POS_NOME_EMPRESA,
    PI_POS_PAIS_ID,
    PI_TAMANHO_TOTAL,
    PI_TIPO,
    TI_CONTRATANTES_VALIDOS,
    TI_LOCAIS_ARMAZENAMENTO_VALIDOS,
    TI_OPERACOES_VALIDAS,
    TI_POS_CNPJ_EMPRESA,
    TI_POS_CONTRATANTE,
    TI_POS_LOCAL_ARMAZENAMENTO,
    TI_POS_NF_NUMERO,
    TI_POS_NOME_EMPRESA,
    TI_POS_OPERACAO,
    TI_TAMANHO_TOTAL,
    TI_TIPO,
    TN_POS_CNPJ_CONTRATANTE,
    TN_POS_CNPJ_DESTINO,
    TN_POS_CNPJ_ORIGEM,
    TN_POS_NF_NUMERO,
    TN_TAMANHO_TOTAL,
    TN_TIPO,
)
from .validators import validar_cnpj, validar_cpf


@dataclass(frozen=True)
class ErroLayoutTXT:
    linha_numero: int
    tipo: str
    mensagem: str

    def formatar(self) -> str:
        prefixo = f"Linha {self.linha_numero}"
        if self.tipo:
            prefixo += f" ({self.tipo})"
        return f"{prefixo}: {self.mensagem}"


@dataclass(frozen=True)
class ResultadoValidacaoTXT:
    caminho: Path
    total_linhas: int
    erros: Sequence[ErroLayoutTXT]

    @property
    def valido(self) -> bool:
        return not self.erros


@dataclass(frozen=True)
class _RegistroLinha:
    numero: int
    tipo: str
    conteudo: str


def _ler_bytes(caminho_txt: str | Path) -> bytes:
    caminho = Path(caminho_txt)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo TXT nao encontrado: {caminho}")
    return caminho.read_bytes()


def _ler_linhas(caminho_txt: str | Path) -> tuple[Path, List[str], List[ErroLayoutTXT]]:
    caminho = Path(caminho_txt)
    erros: List[ErroLayoutTXT] = []
    conteudo_bruto = _ler_bytes(caminho)

    if conteudo_bruto.startswith(b"\xef\xbb\xbf"):
        erros.append(
            ErroLayoutTXT(
                linha_numero=1,
                tipo=EM_TIPO,
                mensagem="arquivo possui BOM UTF-8; isso desloca o layout posicional da primeira linha.",
            )
        )

    try:
        texto = conteudo_bruto.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Arquivo nao esta em UTF-8 valido: {exc}") from exc

    return caminho, texto.splitlines(), erros


def _tem_minusculo_ascii(linha: str) -> bool:
    return any("a" <= ch <= "z" for ch in linha)


def _caracteres_nao_ascii(linha: str) -> list[str]:
    return sorted({ch for ch in linha if ord(ch) > 127})


def _caracteres_controle(linha: str) -> list[str]:
    return [ch for ch in linha if not ch.isprintable()]


def _validar_modal_cc(modal: str) -> str | None:
    if not modal:
        return "modal de transporte vazio; minimo esperado: RO."
    if len(modal) % 2 != 0:
        return f"modal de transporte com tamanho invalido ({len(modal)}). Use codigos concatenados de 2 caracteres."
    blocos = [modal[idx:idx + 2] for idx in range(0, len(modal), 2)]
    invalidos = [bloco for bloco in blocos if bloco not in CC_MODAIS_VALIDOS]
    if invalidos:
        return f"modal de transporte invalido: {', '.join(invalidos)}. Valores aceitos: {', '.join(sorted(CC_MODAIS_VALIDOS))}."
    return None


def _mensagem_tn_curta(comprimento: int) -> str:
    return (
        f"linha curta com {comprimento} caracteres. "
        "O campo 'Nome Contratante' ocupa as posicoes 17-86; "
        f"o erro oficial costuma aparecer como 'begin 16, end 86, length {comprimento}'."
    )


def _slice_posicional(linha: str, pos: tuple[int, int]) -> str:
    inicio, fim = pos
    return linha[inicio - 1:fim]


def _validar_documento_tn_campo(raw: str, campo: str, aceita_cpf: bool) -> str | None:
    if any(ch not in " 0123456789" for ch in raw):
        return f"{campo} contem caracteres invalidos; use apenas digitos e espacos de padding."

    documento = raw.strip()
    if not documento:
        return f"{campo} vazio."

    digitos = "".join(ch for ch in documento if ch.isdigit())
    if len(digitos) == 14:
        if validar_cnpj(digitos):
            return None
        if validar_cpf(digitos[-11:]):
            return (
                f"{campo} contem CPF preenchido com zeros a esquerda ({digitos}); "
                "o SIPROQUIM interpreta esse valor como CNPJ invalido."
            )
        return f"{campo} invalido: {digitos}."

    if len(digitos) == 11 and aceita_cpf:
        if validar_cpf(digitos):
            return None
        return f"{campo} invalido: {digitos}."

    doc_esperado = "CPF valido (11 digitos) ou CNPJ valido (14 digitos)" if aceita_cpf else "CNPJ valido (14 digitos)"
    return f"{campo} deve conter {doc_esperado} apos remover espacos."


def _validar_linha_ti(numero_linha: int, linha: str) -> list[ErroLayoutTXT]:
    erros: List[ErroLayoutTXT] = []
    if len(linha) != TI_TAMANHO_TOTAL:
        erros.append(
            ErroLayoutTXT(numero_linha, TI_TIPO, f"tamanho invalido: {len(linha)} caracteres (esperado {TI_TAMANHO_TOTAL}).")
        )
        return erros

    operacao = _slice_posicional(linha, TI_POS_OPERACAO)
    contratante = _slice_posicional(linha, TI_POS_CONTRATANTE)
    local_armazenamento = _slice_posicional(linha, TI_POS_LOCAL_ARMAZENAMENTO)

    if operacao not in TI_OPERACOES_VALIDAS:
        erros.append(ErroLayoutTXT(numero_linha, TI_TIPO, f"Operacao invalida: '{operacao}'. Use E ou I."))
    if contratante not in TI_CONTRATANTES_VALIDOS:
        erros.append(ErroLayoutTXT(numero_linha, TI_TIPO, f"Contratante invalido: '{contratante}'. Use O ou D."))
    if not _slice_posicional(linha, TI_POS_NF_NUMERO).strip():
        erros.append(ErroLayoutTXT(numero_linha, TI_TIPO, "Numero NF vazio."))
    if not _slice_posicional(linha, TI_POS_NOME_EMPRESA).strip():
        erros.append(ErroLayoutTXT(numero_linha, TI_TIPO, "Nome da Empresa vazio."))

    erro_doc = _validar_documento_tn_campo(
        _slice_posicional(linha, TI_POS_CNPJ_EMPRESA),
        "CPF/CNPJ Empresa",
        aceita_cpf=True,
    )
    if erro_doc:
        erros.append(ErroLayoutTXT(numero_linha, TI_TIPO, erro_doc))

    if local_armazenamento not in TI_LOCAIS_ARMAZENAMENTO_VALIDOS:
        erros.append(ErroLayoutTXT(numero_linha, TI_TIPO, f"Local de Armazenamento invalido: '{local_armazenamento}'. Use apenas P ou A."))

    return erros


def _validar_linha_pi(numero_linha: int, linha: str) -> list[ErroLayoutTXT]:
    erros: List[ErroLayoutTXT] = []
    if len(linha) != PI_TAMANHO_TOTAL:
        erros.append(
            ErroLayoutTXT(numero_linha, PI_TIPO, f"tamanho invalido: {len(linha)} caracteres (esperado {PI_TAMANHO_TOTAL}).")
        )
        return erros

    nome = _slice_posicional(linha, PI_POS_NOME_EMPRESA).strip()
    pais_id = _slice_posicional(linha, PI_POS_PAIS_ID)
    endereco = _slice_posicional(linha, PI_POS_ENDERECO).strip()

    if not nome:
        erros.append(ErroLayoutTXT(numero_linha, PI_TIPO, "Nome Empresa vazio."))
    if not pais_id.isdigit() or pais_id == "000":
        erros.append(ErroLayoutTXT(numero_linha, PI_TIPO, "Id do pais invalido; use 3 digitos da tabela oficial."))
    if not endereco:
        erros.append(ErroLayoutTXT(numero_linha, PI_TIPO, "Endereco completo vazio."))

    return erros


def _validar_linha_la(numero_linha: int, linha: str) -> list[ErroLayoutTXT]:
    erros: List[ErroLayoutTXT] = []
    if len(linha) != LA_TAMANHO_TOTAL:
        erros.append(
            ErroLayoutTXT(numero_linha, LA_TIPO, f"tamanho invalido: {len(linha)} caracteres (esperado {LA_TAMANHO_TOTAL}).")
        )
        return erros

    erro_doc = _validar_documento_tn_campo(linha[2:16], "CPF/CNPJ Empresa", aceita_cpf=True)
    if erro_doc:
        erros.append(ErroLayoutTXT(numero_linha, LA_TIPO, erro_doc))
    if not linha[16:86].strip():
        erros.append(ErroLayoutTXT(numero_linha, LA_TIPO, "Nome Empresa vazio."))

    return erros


def _validar_linha_basica(
    numero_linha: int,
    linha: str,
    documentos_destino_vazios_autorizados: set[str] | None = None,
) -> tuple[_RegistroLinha, list[ErroLayoutTXT]]:
    tipo = linha[:2].upper() if len(linha) >= 2 else ""
    erros: List[ErroLayoutTXT] = []

    if not linha:
        erros.append(ErroLayoutTXT(numero_linha, "", "linha em branco; cada registro deve ocupar exatamente uma linha."))
        return _RegistroLinha(numero_linha, "", linha), erros

    controles = _caracteres_controle(linha)
    if controles:
        erros.append(
            ErroLayoutTXT(
                numero_linha,
                tipo,
                "linha contem caracteres de controle nao imprimiveis.",
            )
        )

    if _tem_minusculo_ascii(linha):
        erros.append(ErroLayoutTXT(numero_linha, tipo, "linha contem letras minusculas; o manual exige dados alfanumericos em MAIUSCULO."))

    nao_ascii = _caracteres_nao_ascii(linha)
    if nao_ascii:
        erros.append(
            ErroLayoutTXT(
                numero_linha,
                tipo,
                "linha contem caracteres nao ASCII/acentuados proibidos pelo manual.",
            )
        )

    if tipo == EM_TIPO:
        if len(linha) != EM_TAMANHO_TOTAL:
            erros.append(
                ErroLayoutTXT(numero_linha, tipo, f"tamanho invalido: {len(linha)} caracteres (esperado {EM_TAMANHO_TOTAL}).")
            )
    elif tipo == TN_TIPO:
        if len(linha) < 86:
            erros.append(ErroLayoutTXT(numero_linha, tipo, _mensagem_tn_curta(len(linha))))
        elif len(linha) != TN_TAMANHO_TOTAL:
            erros.append(
                ErroLayoutTXT(numero_linha, tipo, f"tamanho invalido: {len(linha)} caracteres (esperado {TN_TAMANHO_TOTAL}).")
            )
        if len(linha) >= TN_TAMANHO_TOTAL:
            for posicao, campo, aceita_cpf in (
                (TN_POS_CNPJ_CONTRATANTE, "CPF/CNPJ Contratante", True),
                (TN_POS_CNPJ_ORIGEM, "CPF/CNPJ Origem Carga", False),
                (TN_POS_CNPJ_DESTINO, "CPF/CNPJ Destino Carga", True),
            ):
                erro_doc = _validar_documento_tn_campo(
                    _slice_posicional(linha, posicao),
                    campo,
                    aceita_cpf=aceita_cpf,
                )
                if erro_doc:
                    erros.append(ErroLayoutTXT(numero_linha, tipo, erro_doc))

            local_retirada = linha[274]
            local_entrega = linha[275]
            if local_retirada not in {"P", "A"}:
                erros.append(ErroLayoutTXT(numero_linha, tipo, f"Local de Retirada invalido: '{local_retirada}'. Use apenas P ou A."))
            if local_entrega not in {"P", "A"}:
                erros.append(ErroLayoutTXT(numero_linha, tipo, f"Local de Entrega invalido: '{local_entrega}'. Use apenas P ou A."))
    elif tipo == CC_TIPO:
        if len(linha) < CC_TAMANHO_MINIMO:
            erros.append(
                ErroLayoutTXT(numero_linha, tipo, f"tamanho invalido: {len(linha)} caracteres (minimo esperado {CC_TAMANHO_MINIMO}).")
            )
        else:
            modal = linha[101:].strip()
            erro_modal = _validar_modal_cc(modal)
            if erro_modal:
                erros.append(ErroLayoutTXT(numero_linha, tipo, erro_modal))
    elif tipo == LR_TIPO:
        if len(linha) != LR_TAMANHO_TOTAL:
            erros.append(
                ErroLayoutTXT(numero_linha, tipo, f"tamanho invalido: {len(linha)} caracteres (esperado {LR_TAMANHO_TOTAL}).")
            )
    elif tipo == LA_TIPO:
        erros.extend(_validar_linha_la(numero_linha, linha))
    elif tipo == LE_TIPO:
        if len(linha) != LE_TAMANHO_TOTAL:
            erros.append(
                ErroLayoutTXT(numero_linha, tipo, f"tamanho invalido: {len(linha)} caracteres (esperado {LE_TAMANHO_TOTAL}).")
            )
    elif tipo == TI_TIPO:
        erros.extend(_validar_linha_ti(numero_linha, linha))
    elif tipo == PI_TIPO:
        erros.extend(_validar_linha_pi(numero_linha, linha))
    else:
        erros.append(ErroLayoutTXT(numero_linha, tipo, f"tipo de linha desconhecido: '{tipo or linha[:10]}'."))

    return _RegistroLinha(numero_linha, tipo, linha), erros


def _validar_dependencias_registros(registros: Sequence[_RegistroLinha]) -> list[ErroLayoutTXT]:
    erros: List[ErroLayoutTXT] = []

    if not registros:
        erros.append(ErroLayoutTXT(1, "", "arquivo sem registros."))
        return erros

    if registros[0].tipo != EM_TIPO:
        erros.append(ErroLayoutTXT(registros[0].numero, registros[0].tipo, "primeira linha deve ser EM."))

    total_em = sum(1 for registro in registros if registro.tipo == EM_TIPO)
    if total_em != 1:
        erros.append(ErroLayoutTXT(1, EM_TIPO, f"arquivo deve conter exatamente 1 linha EM, encontrado: {total_em}."))

    tipos_topo = {TN_TIPO, TI_TIPO, EM_TIPO}

    for idx, registro in enumerate(registros):
        if registro.tipo != TN_TIPO or len(registro.conteudo) < TN_TAMANHO_TOTAL:
            continue

        local_retirada = registro.conteudo[274]
        local_entrega = registro.conteudo[275]

        subsecoes = []
        cursor = idx + 1
        while cursor < len(registros) and registros[cursor].tipo not in tipos_topo:
            subsecoes.append(registros[cursor].tipo)
            cursor += 1

        if local_retirada == "A" and LR_TIPO not in subsecoes:
            erros.append(
                ErroLayoutTXT(
                    registro.numero,
                    registro.tipo,
                    "Local de Retirada = 'A' exige uma subsecao LR antes do proximo TN.",
                )
            )
        if local_entrega == "A" and LE_TIPO not in subsecoes:
            erros.append(
                ErroLayoutTXT(
                    registro.numero,
                    registro.tipo,
                    "Local de Entrega = 'A' exige uma subsecao LE antes do proximo TN.",
                )
            )

    for idx, registro in enumerate(registros):
        if registro.tipo != TI_TIPO or len(registro.conteudo) < TI_TAMANHO_TOTAL:
            continue

        local_armazenamento = registro.conteudo[108]
        subsecoes = []
        cursor = idx + 1
        while cursor < len(registros) and registros[cursor].tipo not in tipos_topo:
            subsecoes.append(registros[cursor].tipo)
            cursor += 1

        if PI_TIPO not in subsecoes:
            erros.append(
                ErroLayoutTXT(
                    registro.numero,
                    registro.tipo,
                    "Transporte Internacional exige uma subsecao PI antes do proximo registro principal.",
                )
            )
        if local_armazenamento == "A" and LA_TIPO not in subsecoes:
            erros.append(
                ErroLayoutTXT(
                    registro.numero,
                    registro.tipo,
                    "Local de Armazenamento = 'A' exige uma subsecao LA antes do proximo registro principal.",
                )
            )

    for idx, registro in enumerate(registros):
        if registro.tipo not in {PI_TIPO, LA_TIPO}:
            continue
        anterior_principal = None
        cursor = idx - 1
        while cursor >= 0:
            if registros[cursor].tipo in tipos_topo:
                anterior_principal = registros[cursor].tipo
                break
            cursor -= 1
        if anterior_principal != TI_TIPO:
            erros.append(
                ErroLayoutTXT(
                    registro.numero,
                    registro.tipo,
                    f"subsecao {registro.tipo} deve estar vinculada a uma linha TI anterior.",
                )
            )

    return erros


def validar_txt_siproquim_arquivo(
    caminho_txt: str | Path,
    documentos_destino_vazios_autorizados: set[str] | None = None,
) -> ResultadoValidacaoTXT:
    caminho, linhas, erros_iniciais = _ler_linhas(caminho_txt)
    erros: List[ErroLayoutTXT] = list(erros_iniciais)
    registros: List[_RegistroLinha] = []
    autorizados = {str(nf).strip() for nf in (documentos_destino_vazios_autorizados or set()) if str(nf).strip()}

    for numero_linha, linha in enumerate(linhas, start=1):
        registro, erros_linha = _validar_linha_basica(
            numero_linha,
            linha,
            documentos_destino_vazios_autorizados=autorizados,
        )
        registros.append(registro)
        erros.extend(erros_linha)

    erros.extend(_validar_dependencias_registros(registros))
    return ResultadoValidacaoTXT(caminho=caminho, total_linhas=len(linhas), erros=tuple(erros))


def garantir_txt_valido(
    caminho_txt: str | Path,
    documentos_destino_vazios_autorizados: set[str] | None = None,
) -> ResultadoValidacaoTXT:
    resultado = validar_txt_siproquim_arquivo(
        caminho_txt,
        documentos_destino_vazios_autorizados=documentos_destino_vazios_autorizados,
    )
    if resultado.valido:
        return resultado

    mensagens = "\n".join(f"- {erro.formatar()}" for erro in resultado.erros[:20])
    if len(resultado.erros) > 20:
        mensagens += f"\n- ... {len(resultado.erros) - 20} erro(s) adicional(is)"
    raise ValueError(
        "TXT gerado invalido segundo o layout SIPROQUIM:\n"
        f"{mensagens}"
    )


def _cli(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida um TXT posicional do SIPROQUIM.")
    parser.add_argument("arquivo", help="Caminho do arquivo TXT a validar")
    args = parser.parse_args(list(argv) if argv is not None else None)

    resultado = validar_txt_siproquim_arquivo(args.arquivo)
    if resultado.valido:
        print(f"OK: {resultado.caminho} | {resultado.total_linhas} linha(s) validada(s).")
        return 0

    print(f"ERRO: {resultado.caminho} | {len(resultado.erros)} problema(s) encontrado(s).")
    for erro in resultado.erros:
        print(f"- {erro.formatar()}")
    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
