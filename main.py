"""
Script principal para conversão de PDF para TXT no formato SIPROQUIM/Rodogarcia.
Orquestra a extração de dados do PDF e a geração do arquivo TXT.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional
from src.extrator import ExtratorPDF
from src.processador import SiproquimProcessor, ProcessadorValidacaoIntegrada
from src.gerador import GeradorTXT
from src.gerador.validators import validar_cnpj, validar_cpf


class ProcessamentoInterrompido(RuntimeError):
    """Sinaliza uma interrupcao cooperativa solicitada pela interface."""


def _normalizar_documento(valor: object) -> str:
    """Retorna apenas digitos de um CPF/CNPJ."""
    return ''.join(filter(str.isdigit, str(valor or '')))


def _documento_valido(documento: object, aceitar_cpf: bool = True) -> bool:
    """Valida CPF/CNPJ conforme o campo de destino do layout."""
    doc = _normalizar_documento(documento)
    if len(doc) == 14:
        return validar_cnpj(doc)
    if aceitar_cpf and len(doc) == 11:
        return validar_cpf(doc)
    return False


def _coletar_pendencias_documentos(nfs: list[dict]) -> list[dict]:
    """Coleta documentos ausentes que precisam de decisao humana antes do TXT."""
    pendencias = []
    campos = [
        ("emitente_cnpj", "Origem/Emitente", False),
        ("contratante_cnpj", "Contratante", True),
        ("destinatario_cnpj", "Destino/Destinatario", True),
    ]

    for nf in nfs:
        nf_num = str(nf.get("nf_numero") or "N/A").strip()
        for chave, label, aceita_cpf in campos:
            if _normalizar_documento(nf.get(chave)):
                continue
            exterior = bool(chave == "destinatario_cnpj" and nf.get("destinatario_exterior"))
            if exterior:
                # Destino exterior nao tem CPF/CNPJ brasileiro no TN; o gerador tratara como TI/PI.
                continue
            pendencias.append({
                "nf": nf_num,
                "campo": chave,
                "campo_label": label,
                "nome": nf.get(chave.replace("_cnpj", "_nome")) or "",
                "aceita_cpf": aceita_cpf,
                "exterior": exterior,
                "pode_autorizar_vazio": False,
            })

    return pendencias


def _aplicar_resolucao_documentos(
    nfs: list[dict],
    pendencias: list[dict],
    resolucao: Optional[dict],
) -> set[str]:
    """Aplica documentos digitados e retorna NFs autorizadas com destino vazio."""
    if not pendencias:
        return set()
    if not resolucao or resolucao.get("cancelado"):
        raise ProcessamentoInterrompido("Geracao cancelada: documentos obrigatorios nao informados.")

    pendencias_por_chave = {
        (str(p["nf"]), p["campo"]): p
        for p in pendencias
    }
    nfs_por_numero = {
        str(nf.get("nf_numero") or "N/A").strip(): nf
        for nf in nfs
    }

    autorizadas = set()
    for item in resolucao.get("autorizadas", []):
        nf_num = str(item.get("nf") or "").strip()
        campo = item.get("campo")
        pendencia = pendencias_por_chave.get((nf_num, campo))
        if not pendencia or not pendencia.get("pode_autorizar_vazio"):
            raise ValueError(f"Autorizacao invalida para NF {nf_num} ({campo}).")
        autorizadas.add(nf_num)

    for item in resolucao.get("documentos", []):
        nf_num = str(item.get("nf") or "").strip()
        campo = item.get("campo")
        documento = _normalizar_documento(item.get("documento"))
        pendencia = pendencias_por_chave.get((nf_num, campo))
        if not pendencia:
            raise ValueError(f"Documento informado para pendencia inexistente: NF {nf_num} ({campo}).")
        if not _documento_valido(documento, aceitar_cpf=bool(pendencia.get("aceita_cpf"))):
            esperado = "CPF ou CNPJ valido" if pendencia.get("aceita_cpf") else "CNPJ valido"
            raise ValueError(f"NF {nf_num}: {pendencia.get('campo_label')} exige {esperado}.")
        nfs_por_numero[nf_num][campo] = documento

    faltantes = []
    for pendencia in pendencias:
        nf_num = str(pendencia["nf"])
        campo = pendencia["campo"]
        if nf_num in autorizadas and pendencia.get("pode_autorizar_vazio"):
            continue
        nf = nfs_por_numero.get(nf_num, {})
        if not _normalizar_documento(nf.get(campo)):
            faltantes.append(f"NF {nf_num} ({pendencia.get('campo_label')})")
    if faltantes:
        raise ProcessamentoInterrompido(
            "Geracao cancelada: documento obrigatorio nao informado para "
            + ", ".join(faltantes)
        )

    return autorizadas


def extrair_mes_ano_do_pdf(caminho_pdf: str) -> tuple:
    """
    Extrai mês e ano da data de modificação do arquivo PDF.
    Alternativamente, pode ser extraído de dentro do PDF.
    
    Args:
        caminho_pdf: Caminho do arquivo PDF
    
    Returns:
        Tupla (mes, ano)
    """
    # Por padrão, usa a data de modificação do arquivo
    timestamp = os.path.getmtime(caminho_pdf)
    data_modificacao = datetime.fromtimestamp(timestamp)
    
    # Se o mês for 1-6, assume que é do ano anterior (ex: 06/01/2026 -> Mês 12/Ano 2025)
    mes = data_modificacao.month
    ano = data_modificacao.year
    
    if mes <= 6:
        ano = ano - 1
        mes = 12
    
    return mes, ano


def processar_pdf(caminho_pdf: str, cnpj_rodogarcia: str, 
                  caminho_saida: Optional[str] = None,
                  callback_progresso=None,
                  mes: Optional[int] = None,
                  ano: Optional[int] = None,
                  callback_cancelamento: Optional[Callable[[], bool]] = None,
                  callback_resolver_pendencias: Optional[Callable[[list[dict]], dict]] = None) -> str:
    """
    Processa um arquivo PDF e gera o arquivo TXT correspondente.
    
    Args:
        caminho_pdf: Caminho do arquivo PDF de entrada
        cnpj_rodogarcia: CNPJ da Rodogarcia
        caminho_saida: Caminho do arquivo TXT de saída (opcional)
        callback_progresso: Função opcional chamada durante processamento.
                           Recebe (etapa, detalhes) como parâmetros.
                           Etapas: 'abrir', 'extrair', 'deduplicar', 'gerar', 'finalizar'
    
    Returns:
        Caminho do arquivo TXT gerado
    """
    def _verificar_cancelamento() -> None:
        if callback_cancelamento and callback_cancelamento():
            raise ProcessamentoInterrompido("Execucao interrompida pelo usuario.")

    # Validação de entrada
    if not os.path.exists(caminho_pdf):
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {caminho_pdf}")
    
    # Define caminho de saída se não fornecido
    if not caminho_saida:
        caminho_base = Path(caminho_pdf).stem
        caminho_saida = f"{caminho_base}_siproquim.txt"
    
    if callback_progresso:
        callback_progresso('abrir', {'arquivo': Path(caminho_pdf).name})
    _verificar_cancelamento()
    
    print(f"Processando PDF: {caminho_pdf}")

    # Função wrapper para converter logs do processador em callback_progresso
    def log_wrapper(mensagem: str):
        """Converte logs do processador para callback_progresso (GUI) ou print (CLI)."""
        if callback_progresso:
            # Extrai o tipo do log da mensagem formatada [TIPO] mensagem
            tipo = 'INFO'
            msg_limpa = mensagem
            if mensagem.startswith('[') and ']' in mensagem:
                tipo = mensagem[1:mensagem.index(']')].strip()
                msg_limpa = mensagem[mensagem.index(']') + 1:].strip()
            
            # Envia para o GUI usando a etapa 'processar_log'
            callback_progresso('processar_log', {
                'tipo': tipo,
                'mensagem': msg_limpa
            })
        else:
            # Fallback para CLI
            print(mensagem)

    def event_wrapper(evento: str, detalhes: dict):
        if callback_progresso:
            callback_progresso(evento, detalhes)

    # Usa processador com validação integrada robusta (inclui validação de estrutura do PDF)
    processador = ProcessadorValidacaoIntegrada(
        callback_log=log_wrapper,
        callback_event=event_wrapper
    )
    _verificar_cancelamento()
    
    # Extrai dados do PDF
    extrator = ExtratorPDF(caminho_pdf)
    try:
        extrator.abrir_pdf()
        _verificar_cancelamento()

        # Valida estrutura do PDF antes da extração (detecta mudança de layout)
        primeira_pagina = extrator.pdf.pages[0] if extrator.pdf and extrator.pdf.pages else None
        texto_pagina = primeira_pagina.extract_text() if primeira_pagina else ""
        processador.validar_estrutura_pdf(texto_pagina or "")
        _verificar_cancelamento()
        
        # Define callback para progresso de páginas
        def callback_pagina(pagina_atual, total_paginas):
            _verificar_cancelamento()
            if callback_progresso:
                callback_progresso('extrair', {
                    'pagina_atual': pagina_atual,
                    'total_paginas': total_paginas
                })

        todos_dados = extrator.extrair_todos_dados(
            callback_progresso=callback_pagina,
            callback_cancelamento=callback_cancelamento,
        )
        print(f"Total de registros extraídos: {len(todos_dados)}")
        _verificar_cancelamento()
        
        
        # Deduplica por número de NF
        nfs_deduplicadas = extrator.deduplicar_por_nf(todos_dados)
        
        if callback_progresso:
            callback_progresso('deduplicar', {
                'total_registros': len(todos_dados),
                'total_nfs': len(nfs_deduplicadas)
            })
        print(f"Total de NFs únicas após deduplicação: {len(nfs_deduplicadas)}")
        _verificar_cancelamento()
        
    finally:
        extrator.fechar_pdf()
    
    # CAMADA DE PROCESSAMENTO ROBUSTA: Validação completa com checksum/integridade
    # Estratégia: Validação Preventiva + Auto-correção + Delegação (NENHUM registro é removido)
    # NOVO: Valida TODOS os campos (NF, CTe, CNPJs, Datas) ANTES de gerar TXT
    if callback_progresso:
        callback_progresso('processar', {'total_registros': len(nfs_deduplicadas)})
    _verificar_cancelamento()
    
    
    # Processa com VALIDAÇÃO ROBUSTA: Checksum + Formato + Integridade
    # 1. Valida TODOS os campos (NF, CTe, CNPJs, Datas)
    # 2. Corrige automaticamente usando base de conhecimento
    # 3. Mantém TODOS os registros no arquivo
    # 4. Avisos aparecem no log para correção manual quando necessário
    nfs_validas = processador.filtrar_dados_validos(
        nfs_deduplicadas,
        callback_cancelamento=callback_cancelamento,
    )
    _verificar_cancelamento()
    
    # Estatísticas para callback (com informações de validação)
    stats = processador.obter_estatisticas()
    if callback_progresso:
        callback_progresso('processar', {
            'total_rejeitados': stats['total_rejeitados'],  # Sempre 0 na estratégia híbrida
            'total_corrigidos': stats['total_corrigidos'],
            'total_aprovados': len(nfs_validas),
            'total_com_erros': stats.get('total_com_erros', 0),
            'total_com_erros_criticos': stats.get('total_com_erros_criticos', 0),
            'total_ajustes_manuais': stats.get('total_ajustes_manuais', 0),
        })

    pendencias_documentos = _coletar_pendencias_documentos(nfs_validas)
    documentos_destino_vazios_autorizados: set[str] = set()
    if pendencias_documentos:
        if callback_resolver_pendencias is None:
            descricoes = ", ".join(
                f"NF {p['nf']} ({p['campo_label']})"
                for p in pendencias_documentos[:5]
            )
            if len(pendencias_documentos) > 5:
                descricoes += f", ... +{len(pendencias_documentos) - 5}"
            raise ValueError(
                "Documento obrigatorio ausente no PDF. "
                f"Pendencias: {descricoes}."
            )

        resolucao = callback_resolver_pendencias(pendencias_documentos)
        documentos_destino_vazios_autorizados = _aplicar_resolucao_documentos(
            nfs_validas,
            pendencias_documentos,
            resolucao,
        )
        for nf_autorizada in sorted(documentos_destino_vazios_autorizados):
            if callback_progresso:
                callback_progresso('ajuste_manual', {
                    'nf': nf_autorizada,
                    'tipo': 'ACAO_NECESSARIA',
                    'mensagem': (
                        "Documento Destino ausente autorizado manualmente "
                        "para caso de exterior."
                    )
                })
                callback_progresso('processar_log', {
                    'tipo': 'ACAO_NECESSARIA',
                    'mensagem': (
                        f"NF {nf_autorizada}: Documento Destino ausente autorizado "
                        "manualmente e sera gerado em branco no TXT."
                    )
                })
    
    # Extrai mês e ano (usa valores fornecidos ou extrai do PDF)
    if mes is None or ano is None:
        mes, ano = extrair_mes_ano_do_pdf(caminho_pdf)
    print(f"Período de referência: {mes:02d}/{ano}")
    
    if callback_progresso:
        callback_progresso('gerar', {
            'total_nfs': len(nfs_validas),
            'mes': mes,
            'ano': ano
        })
    _verificar_cancelamento()
    
    # Gera arquivo TXT (agora só recebe dados que o SIPROQUIM aceita)
    gerador = GeradorTXT(
        cnpj_rodogarcia,
        documentos_destino_vazios_autorizados=documentos_destino_vazios_autorizados,
    )
    caminho_gerado = gerador.gerar_arquivo(
        nfs_validas,
        mes,
        ano,
        caminho_saida,
        callback_progresso=callback_progresso,
        callback_cancelamento=callback_cancelamento,
    )
    _verificar_cancelamento()
    
    print(f"Arquivo TXT gerado com sucesso: {caminho_gerado}")
    return caminho_gerado


def main():
    """Função principal do script."""
    if len(sys.argv) < 3:
        print("Uso: python main.py <caminho_pdf> <cnpj_rodogarcia> [caminho_saida]")
        print("\nExemplo:")
        print("  python main.py documento.pdf 12345678000190 saida.txt")
        sys.exit(1)
    
    caminho_pdf = sys.argv[1]
    cnpj_rodogarcia = sys.argv[2]
    caminho_saida = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        caminho_gerado = processar_pdf(caminho_pdf, cnpj_rodogarcia, caminho_saida)
        print(f"\n[OK] Conversao concluida com sucesso!")
        print(f"  Arquivo: {caminho_gerado}")
    except Exception as e:
        print(f"\n[ERRO] Erro ao processar arquivo: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
