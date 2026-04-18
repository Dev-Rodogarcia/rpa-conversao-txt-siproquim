"""
Módulo responsável pelo parsing de tabelas extraídas do PDF.
Processa tabelas e extrai dados estruturados.
"""

import re
from typing import Dict, List, Optional
from .campo_extractor import (
    extrair_cnpj_do_texto,
    extrair_nome_do_texto,
    extrair_numero_cte,
    extrair_data_cte,
    extrair_data_entrega,
    extrair_recebedor
)

# Importa constantes compartilhadas
try:
    from ..gerador.layout_constants import (
        RECEBEDOR_NAO_INFORMADO, TN_LOCAL_PROPRIO
    )
except (ImportError, ValueError):
    # Fallback se importação circular
    RECEBEDOR_NAO_INFORMADO = "NAO INFORMADO"
    TN_LOCAL_PROPRIO = "P"


class TabelaParser:
    """Classe responsável por processar tabelas do PDF."""
    
    def __init__(self):
        """Inicializa o parser de tabelas."""
        pass
    
    def encontrar_cabecalho(self, tabela: List[List]) -> Optional[int]:
        """
        Encontra o índice da linha que contém o cabeçalho "QUANTIDADE".
        
        Args:
            tabela: Tabela extraída pelo pdfplumber
        
        Returns:
            Índice da linha do cabeçalho ou None
        """
        for i, linha in enumerate(tabela):
            if linha and any(celula and 'QUANTIDADE' in str(celula).upper() for celula in linha):
                return i
        return None
    
    def extrair_dados_compartilhados(self, tabela: List[List]) -> Dict:
        """
        Extrai dados compartilhados da tabela (Emitente, Destinatário, Contratante, CTe).
        Estes dados são os mesmos para todos os produtos da tabela.
        
        Args:
            tabela: Tabela extraída pelo pdfplumber
        
        Returns:
            Dicionário com dados compartilhados
        """
        dados = {
            'emitente_texto': None,
            'destinatario_texto': None,
            'contratante_texto': None,
            'cte_texto': None
        }
        
        for linha in tabela:
            if not linha:
                continue
            
            for celula in linha:
                if not celula:
                    continue
                
                texto = str(celula)
                
                if 'EMITENTE' in texto.upper() and not dados['emitente_texto']:
                    dados['emitente_texto'] = texto
                
                if ('DESTINATÁRIO' in texto.upper() or 'DESTINATARIO' in texto.upper()) and not dados['destinatario_texto']:
                    dados['destinatario_texto'] = texto
                
                if ('CONTRANTE' in texto.upper() or 'CONTRATANTE' in texto.upper()) and not dados['contratante_texto']:
                    dados['contratante_texto'] = texto
                
                if ('CT-E' in texto.upper() or 'CTE' in texto.upper() or 'Nº CT' in texto.upper()) and not dados['cte_texto']:
                    dados['cte_texto'] = texto
        
        return dados
    
    def processar_dados_compartilhados(self, dados_compartilhados: Dict) -> Dict:
        """
        Processa os dados compartilhados extraindo CNPJs, nomes, etc.
        
        Args:
            dados_compartilhados: Dicionário com textos brutos
        
        Returns:
            Dicionário com dados processados
        """
        resultado = {}
        
        # Processa emitente
        if dados_compartilhados['emitente_texto']:
            resultado['emitente_cnpj'] = extrair_cnpj_do_texto(dados_compartilhados['emitente_texto'])
            resultado['emitente_nome'] = extrair_nome_do_texto(dados_compartilhados['emitente_texto'])
        
        # Processa destinatário
        if dados_compartilhados['destinatario_texto']:
            resultado['destinatario_texto'] = dados_compartilhados['destinatario_texto']
            resultado['destinatario_exterior'] = bool(
                re.search(
                    r'EXTERIOR\s*-\s*EX|99999-999',
                    dados_compartilhados['destinatario_texto'],
                    re.IGNORECASE,
                )
            )
            resultado['destinatario_cnpj'] = extrair_cnpj_do_texto(dados_compartilhados['destinatario_texto'])
            resultado['destinatario_nome'] = extrair_nome_do_texto(dados_compartilhados['destinatario_texto'])
        
        # Processa contratante
        if dados_compartilhados['contratante_texto']:
            resultado['contratante_cnpj'] = extrair_cnpj_do_texto(dados_compartilhados['contratante_texto'])
            resultado['contratante_nome'] = extrair_nome_do_texto(dados_compartilhados['contratante_texto'])
        
        # Se não tem contratante, usa o emitente
        if not resultado.get('contratante_cnpj'):
            resultado['contratante_cnpj'] = resultado.get('emitente_cnpj')
            resultado['contratante_nome'] = resultado.get('emitente_nome')
        
        # Processa CTe
        if dados_compartilhados['cte_texto']:
            resultado['cte_numero'] = extrair_numero_cte(dados_compartilhados['cte_texto'])
            resultado['cte_data'] = extrair_data_cte(dados_compartilhados['cte_texto'])
            resultado['data_entrega'] = extrair_data_entrega(dados_compartilhados['cte_texto'])
            resultado['recebedor'] = extrair_recebedor(dados_compartilhados['cte_texto'])
        
        # FALLBACK CRÍTICO: Se não encontrou recebedor, usa destinatário (quem recebe a carga)
        # Campo "Responsável pelo Recebimento" é OBRIGATÓRIO no SIPROQUIM
        if not resultado.get('recebedor'):
            resultado['recebedor'] = resultado.get('destinatario_nome')
        
        # Se ainda não tiver, tenta contratante
        if not resultado.get('recebedor'):
            resultado['recebedor'] = resultado.get('contratante_nome')
        
        # Último fallback: emitente
        if not resultado.get('recebedor'):
            resultado['recebedor'] = resultado.get('emitente_nome')
        
        # Último recurso: valor padrão
        if not resultado.get('recebedor'):
            resultado['recebedor'] = RECEBEDOR_NAO_INFORMADO
        
        return resultado
    
    def extrair_nf_da_linha(self, linha: List) -> Dict[str, Optional[str]]:
        """
        Extrai número e data da NF de uma linha de produto.
        
        A estrutura da tabela é:
        - Coluna 0: QUANTIDADE\n2.0
        - Coluna 1: UNIDADE\nPC
        - Coluna 2: DATA NF\n29/12/2025
        - Coluna 3: NF\n11288
        
        Args:
            linha: Linha da tabela contendo dados do produto
        
        Returns:
            Dicionário com nf_numero e nf_data
        """
        nf_numero = None
        nf_data = None
        
        # Estratégia 1: Busca por posição (mais confiável)
        # Se a linha tem pelo menos 4 colunas, tenta pegar das colunas específicas
        if len(linha) >= 4:
            # Coluna 3 (índice 3) = NF
            if linha[3]:
                texto_nf = str(linha[3])
                # Se tem "\n", pega a parte após o "\n"
                if '\n' in texto_nf:
                    partes = texto_nf.split('\n')
                    for parte in partes:
                        parte = parte.strip()
                        # Se a parte é só um número de 4-6 dígitos, é a NF
                        if parte.isdigit() and 4 <= len(parte) <= 6:
                            nf_numero = parte
                            break
                        # Ou procura padrão "NF" seguido de número
                        match_nf = re.search(r'NF\s*:?\s*(\d{4,6})', parte, re.IGNORECASE)
                        if match_nf:
                            nf_numero = match_nf.group(1)
                            break
                else:
                    # Se não tem "\n", pode ser só o número
                    texto_nf = texto_nf.strip()
                    if texto_nf.isdigit() and 4 <= len(texto_nf) <= 6:
                        nf_numero = texto_nf
            
            # Coluna 2 (índice 2) = DATA NF
            if linha[2] and not nf_data:
                texto_data = str(linha[2])
                # Se tem "\n", pega a parte após o "\n"
                if '\n' in texto_data:
                    partes = texto_data.split('\n')
                    for parte in partes:
                        match_data = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', parte)
                        if match_data:
                            nf_data = match_data.group(1)
                            break
                else:
                    # Se não tem "\n", procura data diretamente
                    match_data = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', texto_data)
                    if match_data:
                        nf_data = match_data.group(1)
        
        # Estratégia 2: Busca genérica em todas as células (fallback)
        if not nf_numero or not nf_data:
            for celula in linha:
                if not celula:
                    continue
                
                texto = str(celula)
                
                # Busca NF
                if not nf_numero:
                    # Se a célula contém "NF\n" seguido de número
                    if 'NF' in texto.upper() and '\n' in texto:
                        partes = texto.split('\n')
                        for parte in partes:
                            parte = parte.strip()
                            # Procura número após "NF"
                            if 'NF' in parte.upper():
                                match_nf = re.search(r'NF\s*:?\s*(\d{4,6})', parte, re.IGNORECASE)
                                if match_nf:
                                    nf_numero = match_nf.group(1)
                                    break
                            # Ou se a parte é só um número grande, pode ser a NF
                            elif parte.isdigit() and 4 <= len(parte) <= 6:
                                nf_numero = parte
                                break
                    # Procura padrão "NF" seguido de número
                    else:
                        match_nf_label = re.search(r'NF\s*:?\s*(\d{4,6})', texto, re.IGNORECASE)
                        if match_nf_label:
                            nf_numero = match_nf_label.group(1)
                        # Ou número isolado de 4-6 dígitos que não seja ano
                        elif re.match(r'^\d{4,6}$', texto.strip()):
                            num = texto.strip()
                            # Não é ano (não começa com 20) ou tem mais de 4 dígitos
                            if not (num.startswith('20') and len(num) == 4):
                                nf_numero = num
                
                # Busca Data
                if not nf_data:
                    # Se a célula contém "DATA NF\n" seguido de data
                    if 'DATA' in texto.upper() and 'NF' in texto.upper() and '\n' in texto:
                        partes = texto.split('\n')
                        for parte in partes:
                            match_data = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', parte)
                            if match_data:
                                nf_data = match_data.group(1)
                                break
                    # Busca genérica de data
                    else:
                        match_data = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', texto)
                        if match_data:
                            nf_data = match_data.group(1)
        
        return {'nf_numero': nf_numero, 'nf_data': nf_data}
    
    def e_linha_de_produto(self, linha: List) -> bool:
        """
        Verifica se uma linha é uma linha de produto (tem data e número).
        
        Args:
            linha: Linha da tabela
        
        Returns:
            True se for linha de produto, False caso contrário
        """
        if not linha:
            return False
        
        linha_texto = ' '.join([str(c) for c in linha if c])
        tem_data = bool(re.search(r'\d{1,2}/\d{1,2}/\d{4}', linha_texto))
        tem_numero = bool(re.search(r'\d{4,6}', linha_texto))
        
        return tem_data and tem_numero
    
    def processar_tabela(self, tabela: List[List]) -> List[Dict]:
        """
        Processa uma tabela completa e extrai todos os registros.
        
        Args:
            tabela: Tabela extraída pelo pdfplumber
        
        Returns:
            Lista de dicionários, cada um representando uma NF com seus dados
        """
        dados = []
        
        # Encontra cabeçalho
        idx_cabecalho = self.encontrar_cabecalho(tabela)
        if idx_cabecalho is None:
            return []
        
        # Extrai dados compartilhados
        dados_compartilhados = self.extrair_dados_compartilhados(tabela)
        dados_processados = self.processar_dados_compartilhados(dados_compartilhados)
        
        # Processa cada linha de produto
        # IMPORTANTE: A linha do cabeçalho (idx_cabecalho) também contém os dados do primeiro produto!
        # Estrutura: Linha 2 = "QUANTIDADE\n2.0 | UNIDADE\nPC | DATA NF\n29/12/2025 | NF\n11288"
        for i in range(idx_cabecalho, len(tabela)):
            linha = tabela[i]
            if not linha:
                continue
            
            # Se for a linha do cabeçalho, verifica se tem dados de produto (tem números e datas)
            # Se for linha seguinte, verifica se é linha de produto
            if i == idx_cabecalho:
                # Linha do cabeçalho: verifica se tem dados além do cabeçalho
                tem_dados_produto = any(
                    celula and ('\n' in str(celula) and re.search(r'\d{1,2}/\d{1,2}/\d{4}', str(celula)))
                    for celula in linha
                )
                if not tem_dados_produto:
                    continue
            else:
                # Linha seguinte: verifica se é linha de produto
                if not self.e_linha_de_produto(linha):
                    continue
            
            # Extrai NF desta linha
            nf_dados = self.extrair_nf_da_linha(linha)
            
            # Só cria registro se tiver NF
            if nf_dados['nf_numero']:
                registro = {
                    'nf_numero': nf_dados['nf_numero'],
                    'nf_data': nf_dados['nf_data'],
                    'emitente_cnpj': dados_processados.get('emitente_cnpj'),
                    'emitente_nome': dados_processados.get('emitente_nome'),
                    'destinatario_cnpj': dados_processados.get('destinatario_cnpj'),
                    'destinatario_nome': dados_processados.get('destinatario_nome'),
                    'destinatario_texto': dados_processados.get('destinatario_texto'),
                    'destinatario_exterior': dados_processados.get('destinatario_exterior', False),
                    'contratante_cnpj': dados_processados.get('contratante_cnpj'),
                    'contratante_nome': dados_processados.get('contratante_nome'),
                    'cte_numero': dados_processados.get('cte_numero'),
                    'cte_data': dados_processados.get('cte_data'),
                    'data_entrega': dados_processados.get('data_entrega'),
                    'recebedor': dados_processados.get('recebedor'),
                    'local_retirada': TN_LOCAL_PROPRIO,
                    'local_entrega': TN_LOCAL_PROPRIO
                }
                
                # FALLBACK CRÍTICO: Garante que recebedor nunca fique vazio (campo obrigatório)
                if not registro.get('recebedor'):
                    registro['recebedor'] = registro.get('destinatario_nome') or registro.get('contratante_nome') or registro.get('emitente_nome')
                dados.append(registro)
        
        return dados
