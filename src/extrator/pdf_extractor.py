"""
Módulo principal de extração de dados de PDFs.
Classe principal que orquestra a extração usando os outros módulos.
"""

import pdfplumber
import re
from typing import Dict, List, Optional
from collections import defaultdict

from .tabela_parser import TabelaParser
from .campo_extractor import (
    extrair_cnpj_do_texto,
    extrair_nome_do_texto,
    extrair_numero_cte
)

# Importa constantes compartilhadas
try:
    from ..gerador.layout_constants import (
        CNPJ_TAMANHO, CNPJ_VAZIO, RECEBEDOR_NAO_INFORMADO,
        TN_LOCAL_PROPRIO
    )
    from ..gerador.validators import validar_cpf
except (ImportError, ValueError):
    # Fallback se importação circular - calcula dinamicamente
    CNPJ_TAMANHO = 14
    CNPJ_VAZIO = "0" * CNPJ_TAMANHO
    RECEBEDOR_NAO_INFORMADO = "NAO INFORMADO"
    TN_LOCAL_PROPRIO = "P"

    def validar_cpf(_: str) -> bool:
        return False


class ExtratorPDF:
    """Classe principal responsável pela extração de dados do PDF."""
    
    def __init__(self, caminho_pdf: str):
        """
        Inicializa o extrator com o caminho do PDF.
        
        Args:
            caminho_pdf: Caminho para o arquivo PDF
        """
        self.caminho_pdf = caminho_pdf
        self.pdf = None
        self.tabela_parser = TabelaParser()
    
    def abrir_pdf(self):
        """Abre o arquivo PDF."""
        self.pdf = pdfplumber.open(self.caminho_pdf)
    
    def fechar_pdf(self):
        """Fecha o arquivo PDF."""
        if self.pdf:
            self.pdf.close()
    
    def extrair_dados_pagina(self, pagina) -> List[Dict]:
        """
        Extrai dados de uma página do PDF usando tabelas.
        Estratégia híbrida: tabelas primeiro, fallback para texto com padrões.
        
        Args:
            pagina: Página do pdfplumber
        
        Returns:
            Lista de dicionários, cada um representando uma NF com seus dados
        """
        dados = []
        
        # Estratégia 1: Tenta extrair tabelas primeiro (mais estruturado)
        tabelas = pagina.extract_tables()
        
        if tabelas:
            for tabela in tabelas:
                dados_tabela = self.tabela_parser.processar_tabela(tabela)
                dados.extend(dados_tabela)
        
        # Estratégia 2: Se não encontrou dados nas tabelas, usa padrões globais no texto
        # Isso torna o script resiliente a PDFs com layout diferente
        if not dados:
            texto = pagina.extract_text(layout=True)  # layout=True ajuda a manter estrutura espacial
            if texto:
                dados_texto = self._extrair_dados_por_padroes(texto)
                dados.extend(dados_texto)
        
        return dados
    
    def _extrair_dados_por_padroes(self, texto: str) -> List[Dict]:
        """
        Extrai dados usando padrões regex globais (estratégia à prova de balas).
        Não depende de posições fixas, busca padrões em todo o texto.
        
        Args:
            texto: Texto completo da página
        
        Returns:
            Lista de registros extraídos
        """
        dados = []
        
        # Divide o texto em blocos lógicos usando "NCM:" ou "EMITENTE" como delimitadores
        # Cada bloco representa uma operação (NF + CTe)
        blocos = re.split(r'(?=NCM:|EMITENTE)', texto)
        
        for bloco in blocos:
            if not bloco.strip():
                continue
            
            # Busca número do CTe como âncora (é único por transação)
            match_cte = re.search(r'N[º°]?\s*CT-?E\s*:?\s*(\d+)', bloco, re.IGNORECASE)
            if not match_cte:
                continue  # Se não tem CTe, não é um bloco válido
            
            cte_numero = match_cte.group(1)
            
            # Extrai dados do bloco usando padrões
            registro = self._extrair_dados_do_contexto(bloco, cte_numero)
            if registro:
                dados.append(registro)
        
        return dados
    
    def _extrair_dados_do_contexto(self, contexto: str, cte_numero: str) -> Optional[Dict]:
        """
        Extrai dados de um contexto de texto usando padrões robustos.
        Não depende de posições fixas, busca padrões em todo o contexto.
        
        Args:
            contexto: Texto do contexto (pode ser bloco inteiro ou trecho)
            cte_numero: Número do CTe já identificado
        
        Returns:
            Dicionário com dados extraídos ou None
        """
        registro = {'cte_numero': cte_numero}
        
        # Extrai NF (busca padrões flexíveis)
        match_nf = re.search(r'(?:NF|NE|NOTA\s*FISCAL)\s*:?\s*(\d{4,6})', contexto, re.IGNORECASE)
        if match_nf:
            registro['nf_numero'] = match_nf.group(1)
        
        # Extrai data NF (busca todas as datas e pega a primeira, geralmente é da NF)
        datas_encontradas = re.findall(r'(\d{1,2}/\d{1,2}/\d{4})', contexto)
        if datas_encontradas:
            # A primeira data geralmente é da NF
            registro['nf_data'] = datas_encontradas[0]
            # A última data geralmente é do CTe
            if len(datas_encontradas) > 1:
                registro['cte_data'] = datas_encontradas[-1]
            else:
                registro['cte_data'] = datas_encontradas[0]
        
        # Extrai data CTe (se não encontrou acima, busca padrão específico)
        if not registro.get('cte_data'):
            match_data_cte = re.search(r'DATA\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', contexto, re.IGNORECASE)
            if match_data_cte:
                registro['cte_data'] = match_data_cte.group(1)
        
        # Extrai todos os CNPJs/CPFs do bloco (estratégia robusta)
        # Busca todos os CNPJs formatados primeiro (XX.XXX.XXX/XXXX-XX)
        cnpjs_formatados = re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', contexto)
        
        # Busca CPFs formatados também (XXX.XXX.XXX-XX)
        cpfs_formatados = re.findall(r'\d{3}\.\d{3}\.\d{3}-\d{2}', contexto)
        # Mantém CPFs como 11 dígitos - o sanitizer tratará a formatação conforme necessário
        for cpf in cpfs_formatados:
            cpf_limpo = self._limpar_cnpj_cpf(cpf)
            if len(cpf_limpo) == 11 and validar_cpf(cpf_limpo):
                cnpjs_formatados.append(cpf_limpo)
        
        # Se não encontrou formatados suficientes, busca sequências de dígitos
        # Mas com cuidado para não pegar CPF + telefone
        if len(cnpjs_formatados) < 3:
            # Divide por linhas para evitar pegar CPF de uma linha + telefone de outra
            linhas = contexto.split('\n')
            for linha in linhas:
                # Busca CPF formatado na linha
                match_cpf = re.search(r'(\d{3}\.\d{3}\.\d{3}-\d{2})', linha)
                if match_cpf:
                    cpf_limpo = self._limpar_cnpj_cpf(match_cpf.group(1))
                    if len(cpf_limpo) == 11 and validar_cpf(cpf_limpo):
                        if cpf_limpo not in cnpjs_formatados:
                            cnpjs_formatados.append(cpf_limpo)
                
                # Busca CNPJ formatado na linha
                match_cnpj = re.search(r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', linha)
                if match_cnpj:
                    cnpj_limpo = self._limpar_cnpj_cpf(match_cnpj.group(1))
                    if len(cnpj_limpo) == CNPJ_TAMANHO and cnpj_limpo not in cnpjs_formatados:
                        cnpjs_formatados.append(cnpj_limpo)
                
                # Busca CPF não formatado mas para antes de telefone
                match_cpf_raw = re.search(r'(?:CNPJ/CPF|CPF)[:\s]*(\d{11})(?:\s|$|[^\d]|FONE|TELEFONE)', linha, re.IGNORECASE)
                if match_cpf_raw:
                    cpf_limpo = match_cpf_raw.group(1)
                    if len(cpf_limpo) == 11 and validar_cpf(cpf_limpo):
                        if cpf_limpo not in cnpjs_formatados:
                            cnpjs_formatados.append(cpf_limpo)
                
                # Busca CNPJ não formatado mas para antes de telefone
                match_cnpj_raw = re.search(r'(?:CNPJ/CPF|CNPJ)[:\s]*(\d{14})(?:\s|$|[^\d]|FONE|TELEFONE)', linha, re.IGNORECASE)
                if match_cnpj_raw:
                    cnpj_limpo = match_cnpj_raw.group(1)
                    if len(cnpj_limpo) == CNPJ_TAMANHO and cnpj_limpo not in cnpjs_formatados:
                        cnpjs_formatados.append(cnpj_limpo)
                
                if len(cnpjs_formatados) >= 3:
                    break
            
            # Último fallback: busca sequências de dígitos no texto completo
            if len(cnpjs_formatados) < 3:
                texto_sem_pontuacao = re.sub(r'[^\d\s]', ' ', contexto)
                # Busca CPF primeiro (11 dígitos)
                tem_contexto_doc = bool(re.search(r'(CNPJ/CPF|CNPJ|CPF)', contexto, re.IGNORECASE))
                tem_contexto_fone = bool(re.search(r'(FONE|TELEFONE)', contexto, re.IGNORECASE))
                cpfs_raw = re.findall(rf'(?:^|\s)(\d{{11}})(?:\s|$)', texto_sem_pontuacao)
                if tem_contexto_doc and not tem_contexto_fone:
                    for cpf in cpfs_raw:
                        if validar_cpf(cpf) and cpf not in cnpjs_formatados:
                            cnpjs_formatados.append(cpf)
                
                # Busca CNPJ (14 dígitos) mas verifica se não é CPF + telefone
                cnpjs_raw = re.findall(rf'(?:^|\s)(\d{{{CNPJ_TAMANHO}}})(?:\s|$)', texto_sem_pontuacao)
                for cnpj in cnpjs_raw:
                    # Validação: não pode ser tudo zeros ou começar com 00
                    # Verifica se não é CPF (11 dígitos) + telefone (3 dígitos)
                    if (cnpj != CNPJ_VAZIO and 
                        not cnpj.startswith('00') and
                        not (len(cnpj) == 14 and cnpj[:11] != "0" * 11 and 
                             cnpj[11:14].startswith(('14', '15', '16', '17', '18', '19')))):
                        if cnpj not in cnpjs_formatados:
                            cnpjs_formatados.append(cnpj)
                
                cnpjs_formatados = cnpjs_formatados[:3]  # Pega até 3 CNPJs/CPFs
        
        # Associa CNPJs aos campos (ordem: Emitente, Contratante, Destinatário)
        if len(cnpjs_formatados) >= 1:
            registro['emitente_cnpj'] = self._limpar_cnpj_cpf(cnpjs_formatados[0])
        if len(cnpjs_formatados) >= 2:
            registro['contratante_cnpj'] = self._limpar_cnpj_cpf(cnpjs_formatados[1])
        elif registro.get('emitente_cnpj'):
            registro['contratante_cnpj'] = registro['emitente_cnpj']  # Fallback
        if len(cnpjs_formatados) >= 3:
            registro['destinatario_cnpj'] = self._limpar_cnpj_cpf(cnpjs_formatados[2])
        
        # Extrai nomes usando padrões flexíveis
        # Busca texto após labels, até encontrar CNPJ ou próxima seção
        def extrair_nome_apos_label(label, texto_bloco):
            # Padrão: LABEL seguido de texto até CNPJ ou quebra
            pattern = rf'{label}[^\n]*?\n(.*?)(?=CNPJ/CPF|{label}|DESTINAT|CONTRANTE|$)'
            match = re.search(pattern, texto_bloco, re.IGNORECASE | re.DOTALL)
            if match:
                nome = match.group(1).strip()
                # Remove linhas com CNPJ, telefone, endereço, etc.
                linhas_limpas = []
                for linha in nome.split('\n'):
                    linha = linha.strip()
                    if (linha and 
                        'CNPJ' not in linha.upper() and 
                        'CPF' not in linha.upper() and
                        'FONE' not in linha.upper() and
                        'END' not in linha.upper() and
                        'CEP' not in linha.upper() and
                        not re.match(r'^\d', linha)):  # Não começa com número
                        linhas_limpas.append(linha)
                if linhas_limpas:
                    return ' '.join(linhas_limpas)
            return None
        
        registro['emitente_nome'] = extrair_nome_apos_label('EMITENTE', contexto)
        registro['destinatario_nome'] = extrair_nome_apos_label('DESTINAT[ÁA]RIO', contexto)
        registro['contratante_nome'] = extrair_nome_apos_label('CONTRANTE', contexto)
        
        # Fallbacks
        if not registro.get('contratante_cnpj') or registro.get('contratante_cnpj') == CNPJ_VAZIO:
            registro['contratante_cnpj'] = registro.get('emitente_cnpj', CNPJ_VAZIO)
        if not registro.get('contratante_nome'):
            registro['contratante_nome'] = registro.get('emitente_nome')
        
        # FALLBACK CRÍTICO: Se não encontrou recebedor, usa destinatário (campo obrigatório)
        # O recebedor geralmente é quem recebe a carga, ou seja, o destinatário
        if not registro.get('recebedor'):
            registro['recebedor'] = registro.get('destinatario_nome')
        if not registro.get('recebedor'):
            registro['recebedor'] = registro.get('contratante_nome')
        if not registro.get('recebedor'):
            registro['recebedor'] = registro.get('emitente_nome')
        if not registro.get('recebedor'):
            registro['recebedor'] = RECEBEDOR_NAO_INFORMADO
        
        registro['local_retirada'] = TN_LOCAL_PROPRIO
        registro['local_entrega'] = TN_LOCAL_PROPRIO
        
        return registro if registro.get('nf_numero') or registro.get('cte_numero') else None
    
    def _limpar_cnpj_cpf(self, texto: str) -> str:
        """
        Remove pontuação de CNPJ/CPF.
        Retorna o valor limpo sem preencher - o sanitizer tratará a formatação conforme necessário.
        """
        if not texto:
            return CNPJ_VAZIO
        nums = ''.join(filter(str.isdigit, str(texto)))
        # Retorna como está - o sanitizer tratará a formatação conforme necessário
        # Se já tem 14 dígitos (CNPJ), retorna como está
        if len(nums) == CNPJ_TAMANHO:
            return nums
        # Se tem 11 dígitos (CPF), retorna como está
        if len(nums) == 11:
            return nums
        # Para outros tamanhos, preenche com zeros (casos especiais)
        return nums.zfill(CNPJ_TAMANHO)[:CNPJ_TAMANHO]
    
    def extrair_todos_dados(self, callback_progresso=None) -> List[Dict]:
        """
        Extrai todos os dados de todas as páginas do PDF.
        
        Args:
            callback_progresso: Função opcional chamada a cada página processada.
                               Recebe (pagina_atual, total_paginas) como parâmetros.
        
        Returns:
            Lista de dicionários com todos os registros encontrados
        """
        if not self.pdf:
            self.abrir_pdf()
        
        todos_dados = []
        total_paginas = len(self.pdf.pages)
        
        for idx, pagina in enumerate(self.pdf.pages, 1):
            dados_pagina = self.extrair_dados_pagina(pagina)
            todos_dados.extend(dados_pagina)
            
            # Chama callback de progresso se fornecido
            if callback_progresso:
                callback_progresso(idx, total_paginas)
        
        return todos_dados
    
    def deduplicar_por_nf(self, todos_dados: List[Dict]) -> List[Dict]:
        """
        Deduplica registros por número de NF.
        Se uma NF aparece múltiplas vezes, mantém apenas uma ocorrência.
        
        Args:
            todos_dados: Lista de todos os registros extraídos
        
        Returns:
            Lista deduplicada (uma entrada por NF)
        """
        # Agrupa por número de NF
        nfs_agrupadas = defaultdict(list)
        
        for registro in todos_dados:
            nf_num = registro.get('nf_numero')
            if nf_num:
                nfs_agrupadas[nf_num].append(registro)
            else:
                # Se não tem NF, agrupa por CTe
                cte_num = registro.get('cte_numero')
                if cte_num:
                    nfs_agrupadas[f"CTE_{cte_num}"].append(registro)
        
        # Para cada NF, mantém o primeiro registro encontrado
        nfs_deduplicadas = []
        
        for nf_num, registros in nfs_agrupadas.items():
            # Usa o primeiro registro como base
            registro_final = registros[0].copy()
            
            # Se houver múltiplos registros, mescla informações faltantes
            if len(registros) > 1:
                for reg in registros[1:]:
                    for key, value in reg.items():
                        if not registro_final.get(key) and value:
                            registro_final[key] = value
            
            # FALLBACK FINAL: Garante que recebedor nunca fique vazio (campo obrigatório)
            if not registro_final.get('recebedor'):
                registro_final['recebedor'] = (
                    registro_final.get('destinatario_nome') or 
                    registro_final.get('contratante_nome') or 
                    registro_final.get('emitente_nome') or
                    RECEBEDOR_NAO_INFORMADO
                )
            
            nfs_deduplicadas.append(registro_final)
        
        return nfs_deduplicadas
