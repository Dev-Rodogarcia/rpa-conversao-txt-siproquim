"""
Script principal para conversão de PDF para TXT no formato SIPROQUIM/Rodogarcia.
Orquestra a extração de dados do PDF e a geração do arquivo TXT.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from src.extrator import ExtratorPDF
from src.processador import SiproquimProcessor, ProcessadorValidacaoIntegrada
from src.gerador import GeradorTXT


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
                  ano: Optional[int] = None) -> str:
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
    # Validação de entrada
    if not os.path.exists(caminho_pdf):
        raise FileNotFoundError(f"Arquivo PDF não encontrado: {caminho_pdf}")
    
    # Define caminho de saída se não fornecido
    if not caminho_saida:
        caminho_base = Path(caminho_pdf).stem
        caminho_saida = f"{caminho_base}_siproquim.txt"
    
    if callback_progresso:
        callback_progresso('abrir', {'arquivo': Path(caminho_pdf).name})
    
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
    
    # Extrai dados do PDF
    extrator = ExtratorPDF(caminho_pdf)
    try:
        extrator.abrir_pdf()

        # Valida estrutura do PDF antes da extração (detecta mudança de layout)
        primeira_pagina = extrator.pdf.pages[0] if extrator.pdf and extrator.pdf.pages else None
        texto_pagina = primeira_pagina.extract_text() if primeira_pagina else ""
        processador.validar_estrutura_pdf(texto_pagina or "")
        
        # Define callback para progresso de páginas
        def callback_pagina(pagina_atual, total_paginas):
            if callback_progresso:
                callback_progresso('extrair', {
                    'pagina_atual': pagina_atual,
                    'total_paginas': total_paginas
                })
        
        todos_dados = extrator.extrair_todos_dados(callback_progresso=callback_pagina)
        print(f"Total de registros extraídos: {len(todos_dados)}")
        
        
        # Deduplica por número de NF
        nfs_deduplicadas = extrator.deduplicar_por_nf(todos_dados)
        
        if callback_progresso:
            callback_progresso('deduplicar', {
                'total_registros': len(todos_dados),
                'total_nfs': len(nfs_deduplicadas)
            })
        print(f"Total de NFs únicas após deduplicação: {len(nfs_deduplicadas)}")
        
    finally:
        extrator.fechar_pdf()
    
    # CAMADA DE PROCESSAMENTO ROBUSTA: Validação completa com checksum/integridade
    # Estratégia: Validação Preventiva + Auto-correção + Delegação (NENHUM registro é removido)
    # NOVO: Valida TODOS os campos (NF, CTe, CNPJs, Datas) ANTES de gerar TXT
    if callback_progresso:
        callback_progresso('processar', {'total_registros': len(nfs_deduplicadas)})
    
    
    # Processa com VALIDAÇÃO ROBUSTA: Checksum + Formato + Integridade
    # 1. Valida TODOS os campos (NF, CTe, CNPJs, Datas)
    # 2. Corrige automaticamente usando base de conhecimento
    # 3. Mantém TODOS os registros no arquivo
    # 4. Avisos aparecem no log para correção manual quando necessário
    nfs_validas = processador.filtrar_dados_validos(nfs_deduplicadas)
    
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
    
    # Gera arquivo TXT (agora só recebe dados que o SIPROQUIM aceita)
    gerador = GeradorTXT(cnpj_rodogarcia)
    caminho_gerado = gerador.gerar_arquivo(nfs_validas, mes, ano, caminho_saida, callback_progresso=callback_progresso)
    
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
