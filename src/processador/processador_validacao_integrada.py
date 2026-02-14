"""
Processador com validação integrada e robusta.
Substitui o SiproquimProcessor com validação preventiva completa.
"""

from collections import Counter, defaultdict
import re
from typing import List, Dict, Optional, Callable
import unicodedata
from .validador_campos import ValidadorCampos, ErroValidacao
from .validador_estrutura_pdf import ValidadorEstruturaPDF
from .validacao_constants import ConfigValidacao
from .base_conhecimento import BaseConhecimentoNomes
from ..gerador.validators import validar_cpf, validar_cnpj


class ProcessadorValidacaoIntegrada:
    """
    Processador HÍBRIDO com validação robusta integrada.
    
    Estratégia:
    1. Valida estrutura do PDF (detecta mudança de layout)
    2. Valida cada campo extraído (checksum, formato, integridade)
    3. Tenta corrigir automaticamente usando base de conhecimento
    4. Mantém TODOS os registros no arquivo (modo atual)
    5. Avisa no log exatamente onde estão os problemas
    
    Diferencial:
    - Detecta problemas ANTES de gerar o TXT
    - Usa validadores especializados com checksum
    - Fail-fast opcional (configurável)
    - Relatórios detalhados de erros
    """
    
    def __init__(self, 
                 callback_log: Optional[Callable[[str], None]] = None,
                 callback_event: Optional[Callable[[str, Dict], None]] = None,
                 validar_estrutura_pdf: bool = ConfigValidacao.VALIDAR_ESTRUTURA_PDF,
                 fail_fast: bool = ConfigValidacao.FAIL_FAST):
        """
        Args:
            callback_log: Função para imprimir logs na interface gráfica
            validar_estrutura_pdf: Se True, valida estrutura do PDF antes de processar
            fail_fast: Se True, para no primeiro erro crítico
        """
        self.log = callback_log
        self.callback_event = callback_event
        self.validar_estrutura_pdf_flag = validar_estrutura_pdf
        self.fail_fast = fail_fast
        
        # Validadores especializados
        self.validador_estrutura = ValidadorEstruturaPDF()
        self.validador_campos = ValidadorCampos(fail_fast=fail_fast)
        
        # Estatísticas
        self.registros_corrigidos_count = 0
        self.registros_com_erros_count = 0
        self.registros_com_erros_criticos_count = 0
        self.total_erros_encontrados = 0
        self.ajustes_manuais_count = 0
        
        # Cache de erros por NF
        self.erros_por_nf: Dict[str, List[ErroValidacao]] = {}
        self._indice_docs_por_nome: Dict[str, Dict[str, Counter]] = {}
    
    def _log_gui(self, tipo: str, mensagem: str):
        """Envia mensagem para o log da tela preta ou GUI."""
        msg_formatada = f"[{tipo}] {mensagem}"
        if self.log:
            self.log(msg_formatada)
        else:
            print(msg_formatada)

    @staticmethod
    def _normalizar_texto(valor: object) -> str:
        """Normaliza campos textuais para evitar tratar 'None' como nome valido."""
        if valor is None:
            return ""
        texto = str(valor).strip()
        if texto.upper() in {"NONE", "NULL", "N/A", "NA", "NAN"}:
            return ""
        return texto

    @staticmethod
    def _normalizar_documento(valor: object) -> str:
        """Extrai apenas digitos de um campo de documento."""
        texto = ProcessadorValidacaoIntegrada._normalizar_texto(valor)
        return ''.join(filter(str.isdigit, texto))

    @staticmethod
    def _normalizar_nome_chave(valor: object) -> str:
        """Normaliza nome para comparacoes robustas por chave."""
        texto = ProcessadorValidacaoIntegrada._normalizar_texto(valor)
        if not texto:
            return ""
        texto = unicodedata.normalize("NFD", texto.upper())
        texto = ''.join(ch for ch in texto if unicodedata.category(ch) != "Mn")
        texto = re.sub(r"[^A-Z0-9]+", " ", texto)
        return re.sub(r"\s+", " ", texto).strip()

    def _construir_indice_documentos(self, registros: List[Dict]) -> None:
        """Monta indice nome -> CNPJ valido observado no proprio lote."""
        indices: Dict[str, Dict[str, Counter]] = {
            "emitente_cnpj": defaultdict(Counter),
            "contratante_cnpj": defaultdict(Counter),
            "destinatario_cnpj": defaultdict(Counter),
        }

        campos = [
            ("emitente_cnpj", "emitente_nome"),
            ("contratante_cnpj", "contratante_nome"),
            ("destinatario_cnpj", "destinatario_nome"),
        ]

        for registro in registros:
            for chave_doc, chave_nome in campos:
                doc = self._normalizar_documento(registro.get(chave_doc, ""))
                nome = self._normalizar_nome_chave(registro.get(chave_nome, ""))
                if len(doc) == 14 and doc != ("0" * 14) and len(nome) >= 8:
                    indices[chave_doc][nome][doc] += 1

        self._indice_docs_por_nome = indices

    def _buscar_documento_por_nome(self, chave_doc: str, nome: str) -> Optional[str]:
        """
        Busca CNPJ por nome com prioridade:
        1) match exato no lote
        2) match aproximado unico no lote
        3) base de conhecimento (com contexto de campo)
        """
        nome_chave = self._normalizar_nome_chave(nome)
        if len(nome_chave) < 8:
            return None

        indice = self._indice_docs_por_nome.get(chave_doc, {})
        docs_exatos = indice.get(nome_chave)
        if docs_exatos and len(docs_exatos) == 1:
            return next(iter(docs_exatos.keys()))

        candidatos = set()
        if len(nome_chave) >= 12:
            for nome_idx, docs in indice.items():
                menor, maior = (nome_chave, nome_idx) if len(nome_chave) <= len(nome_idx) else (nome_idx, nome_chave)
                if menor in maior:
                    candidatos.update(docs.keys())
                    if len(candidatos) > 1:
                        break
        if len(candidatos) == 1:
            return next(iter(candidatos))

        campo_aprendizado = {
            "emitente_cnpj": "emitente",
            "contratante_cnpj": "contratante",
            "destinatario_cnpj": "destinatario",
        }.get(chave_doc)

        return BaseConhecimentoNomes.buscar_cnpj_por_nome(
            nome_chave,
            campo=campo_aprendizado
        )

    def _emitir_ajuste(self, nf_num: str, tipo: str, mensagem: str):
        """Emite evento estruturado de ajuste manual para a GUI."""
        if self.callback_event:
            self.callback_event('ajuste_manual', {
                'nf': nf_num,
                'tipo': tipo,
                'mensagem': mensagem
            })
    
    def validar_estrutura_pdf(self, texto_pagina: str) -> bool:
        """
        Valida estrutura do PDF antes de processar.
        
        Args:
            texto_pagina: Texto de uma página do PDF
        
        Returns:
            True se estrutura válida, False caso contrário
        
        Raises:
            ValueError: Se PDF mudou de layout
        """
        if not self.validar_estrutura_pdf_flag:
            return True
        
        try:
            self.validador_estrutura.validar_estrutura(texto_pagina)
            self._log_gui("INFO", "Estrutura do PDF validada com sucesso")
            return True
        except ValueError as e:
            self._log_gui("CRITICO", str(e))
            self._log_gui("CRITICO", self.validador_estrutura.obter_relatorio())
            raise
    
    def filtrar_dados_validos(self, nfs_extraidas: List[Dict]) -> List[Dict]:
        """
        Processa as NFs com validação robusta:
        1. Valida cada campo (checksum, formato, integridade)
        2. Corrige o que pode usando base de conhecimento
        3. Audita o que não pode corrigir
        4. Retorna TUDO (nada é removido, apenas validado e auditado)
        
        Args:
            nfs_extraidas: Lista de dicionários com dados brutos extraídos do PDF
        
        Returns:
            Lista com TODOS os registros (validados e auditados)
        """
        nfs_finais: List[Dict] = []
        self.registros_corrigidos_count = 0
        self.registros_com_erros_count = 0
        self.registros_com_erros_criticos_count = 0
        self.total_erros_encontrados = 0
        self.erros_por_nf = {}
        self.ajustes_manuais_count = 0
        
        self._log_gui("INFO", f"Processando {len(nfs_extraidas)} registros com VALIDAÇÃO ROBUSTA...")
        self._log_gui("INFO", "Sistema de Validação: CHECKSUM + FORMATO + INTEGRIDADE")
        
        self._construir_indice_documentos(nfs_extraidas)

        for idx, nf in enumerate(nfs_extraidas, 1):
            nf_num = nf.get('nf_numero', f'REG_{idx}')
            
            # ETAPA 1: VALIDAÇÃO COMPLETA (Checksum, Formato, Integridade)
            erros = self.validador_campos.validar_registro_completo(nf)
            
            if erros:
                # Registra erros encontrados
                self.erros_por_nf[nf_num] = erros
                self.registros_com_erros_count += 1
                self.total_erros_encontrados += len(erros)
                
                # Conta erros críticos
                erros_criticos = [e for e in erros if e.severidade == 'CRITICO']
                if erros_criticos:
                    self.registros_com_erros_criticos_count += 1
                
                # Gera log detalhado
                self._log_gui("VALIDACAO", f"NF {nf_num}: {len(erros)} erro(s) de validacao encontrado(s)")
                for erro in erros:
                    self._log_gui(erro.severidade, f"  -> {erro.mensagem}")
            
            # ETAPA 2: TENTA CORRIGIR DADOS (Auto-correção)
            corrigiu = self._tentar_corrigir_dados(nf)
            if corrigiu:
                self.registros_corrigidos_count += 1
            
            # ETAPA 3: AUDITA PARA O HUMANO (Aponta erros que não conseguiu resolver)
            self._auditar_para_humano(nf)
            
            # ETAPA 4: MANTÉM O REGISTRO (Não deleta nada)
            nfs_finais.append(nf)
        
        # Relatório final
        self._gerar_relatorio_final(len(nfs_extraidas))
        
        return nfs_finais
    
    def _tentar_corrigir_dados(self, nf: Dict) -> bool:
        """
        Tenta preencher documentos e nomes usando índice interno e base de conhecimento.
        
        Args:
            nf: Registro a corrigir
        
        Returns:
            True se corrigiu algo, False caso contrário
        """
        corrigiu = False
        campos = [
            ('destinatario_cnpj', 'destinatario_nome', 'Destinatário'),
            ('contratante_cnpj', 'contratante_nome', 'Contratante'),
            ('emitente_cnpj', 'emitente_nome', 'Emitente')
        ]

        for chave_cnpj, chave_nome, tipo_pessoa in campos:
            cnpj = self._normalizar_documento(nf.get(chave_cnpj, ''))
            nome = self._normalizar_texto(nf.get(chave_nome, ''))

            # Se o documento estiver ausente, tenta inferir pelo nome.
            if (not cnpj or cnpj == ("0" * 14)) and len(nome) >= 8:
                doc_inferido = self._buscar_documento_por_nome(chave_cnpj, nome)
                if doc_inferido:
                    nf[chave_cnpj] = doc_inferido
                    cnpj = doc_inferido
                    corrigiu = True
                    nf_num = nf.get('nf_numero', 'N/A')
                    self._log_gui(
                        "SUCESSO",
                        f"NF {nf_num}: Documento inferido por nome ({tipo_pessoa}) -> {doc_inferido}"
                    )

            # Se tem CNPJ válido mas está sem nome
            if len(cnpj) == 14 and len(nome) < 2:
                nome_base = BaseConhecimentoNomes.buscar_nome_por_cnpj(cnpj)
                if nome_base:
                    nf[chave_nome] = nome_base
                    corrigiu = True
                    nf_num = nf.get('nf_numero', 'N/A')
                    self._log_gui("SUCESSO", 
                                  f"NF {nf_num}: Auto-correcao aplicada para CNPJ {cnpj} "
                                  f"({tipo_pessoa}) -> {nome_base}")
        
        return corrigiu
    
    def _auditar_para_humano(self, nf: Dict) -> None:
        """
        Verifica problemas que o robô não conseguiu resolver e avisa o humano.
        NÃO remove o registro. Aponta EXATAMENTE onde está o problema.
        """
        nf_num = nf.get('nf_numero', 'N/A')
        
        def registrar_ajuste():
            self.ajustes_manuais_count += 1
        
        # --- VERIFICAÇÃO 1: CPF NO LUGAR DE CNPJ (Caso Leonardo/Thalita) ---
        for chave, tipo_pessoa in [('contratante_cnpj', 'Contratante'), 
                                    ('destinatario_cnpj', 'Destinatário')]:
            doc = self._normalizar_documento(nf.get(chave, ''))
            
            if len(doc) == 11 and validar_cpf(doc):
                registrar_ajuste()
                self._emitir_ajuste(nf_num, "ACAO_NECESSARIA",
                                    f"{tipo_pessoa} é CPF ({doc}) ao invés de CNPJ.")
                self._log_gui("ACAO_NECESSARIA", 
                              f"NF {nf_num}: {tipo_pessoa} e CPF ({doc}) ao inves de CNPJ.")
                self._log_gui("ACAO_NECESSARIA", 
                              f"   -> O registro foi mantido no TXT. Abra o arquivo gerado, "
                              f"procure por '{doc}' (ou NF {nf_num}) e substitua por um CNPJ valido.")
        
        # --- VERIFICAÇÃO 2: NOME AINDA VAZIO (Após tentativa de auto-correção) ---
        campos_verificar = [
            ('destinatario_cnpj', 'destinatario_nome', 'Destinatário'),
            ('contratante_cnpj', 'contratante_nome', 'Contratante'),
            ('emitente_cnpj', 'emitente_nome', 'Emitente')
        ]
        
        for chave_cnpj, chave_nome, tipo_pessoa in campos_verificar:
            nome = self._normalizar_texto(nf.get(chave_nome, ''))
            cnpj = self._normalizar_documento(nf.get(chave_cnpj, ''))
            
            if cnpj and (not nome or len(nome) < 2):
                registrar_ajuste()
                self._emitir_ajuste(nf_num, "ATENCAO",
                                    f"CNPJ {cnpj} ({tipo_pessoa}) está sem nome.")
                self._log_gui("ATENCAO", 
                              f"NF {nf_num}: CNPJ {cnpj} ({tipo_pessoa}) esta SEM NOME "
                              f"(nao encontrado na base de conhecimento).")
                self._log_gui("ATENCAO", 
                              f"   -> O registro foi mantido no TXT. Abra o arquivo gerado, "
                              f"procure por '{cnpj}' (ou NF {nf_num}) e preencha o nome manualmente.")
        
        # --- VERIFICAÇÃO 3: CNPJ EMITENTE INVÁLIDO ---
        cnpj_emitente = self._normalizar_documento(nf.get('emitente_cnpj', ''))
        
        if cnpj_emitente:
            if len(cnpj_emitente) == 11 and validar_cpf(cnpj_emitente):
                registrar_ajuste()
                self._emitir_ajuste(nf_num, "ACAO_NECESSARIA",
                                    f"Emitente está como CPF ({cnpj_emitente}) no lugar de CNPJ.")
                self._log_gui("ACAO_NECESSARIA", 
                              f"NF {nf_num}: Emitente é CPF ({cnpj_emitente}) no lugar de CNPJ.")
                self._log_gui("ACAO_NECESSARIA", 
                              f"   -> O registro foi mantido no TXT. Substitua por um CNPJ válido.")
            elif len(cnpj_emitente) != 14:
                registrar_ajuste()
                self._emitir_ajuste(nf_num, "ACAO_NECESSARIA",
                                    f"CNPJ Emitente com tamanho inválido ({len(cnpj_emitente)} dígitos).")
                self._log_gui("ACAO_NECESSARIA", 
                              f"NF {nf_num}: CNPJ Emitente tem tamanho incorreto "
                              f"({len(cnpj_emitente)} digitos: {cnpj_emitente}).")
            elif not validar_cnpj(cnpj_emitente):
                registrar_ajuste()
                self._emitir_ajuste(nf_num, "ACAO_NECESSARIA",
                                    f"CNPJ Emitente inválido ({cnpj_emitente}).")
                self._log_gui("ACAO_NECESSARIA", 
                              f"NF {nf_num}: CNPJ Emitente invalido ({cnpj_emitente}) "
                              f"- nao passa na validacao Modulo 11.")
    
    def _gerar_relatorio_final(self, total_processados: int):
        """Gera relatório final do processamento."""
        self._log_gui("INFO", "=" * 60)
        self._log_gui("INFO", "RELATÓRIO FINAL DE VALIDAÇÃO")
        self._log_gui("INFO", "=" * 60)
        self._log_gui("INFO", f"Total de registros processados: {total_processados}")
        self._log_gui("INFO", f"Registros corrigidos automaticamente: {self.registros_corrigidos_count}")
        self._log_gui("INFO", f"Registros com erros de validação: {self.registros_com_erros_count}")
        self._log_gui("INFO", f"Registros com erros CRÍTICOS: {self.registros_com_erros_criticos_count}")
        self._log_gui("INFO", f"Total de erros encontrados: {self.total_erros_encontrados}")
        self._log_gui("INFO", f"Ajustes manuais necessários: {self.ajustes_manuais_count}")
        self._log_gui("INFO", f"Total exportado para TXT: {total_processados}")
        self._log_gui("INFO", "=" * 60)
        
        if self.registros_com_erros_criticos_count > 0:
            self._log_gui("ALERTA", 
                          f"[!] ATENCAO: {self.registros_com_erros_criticos_count} registro(s) com erros CRITICOS!")
            self._log_gui("ALERTA", 
                          "O SIPROQUIM pode REJEITAR esses registros ao processar o arquivo.")
            self._log_gui("ALERTA", 
                          "Revise os erros acima e corrija manualmente no TXT gerado.")
    
    def obter_estatisticas(self) -> Dict:
        """
        Retorna estatísticas sobre o processamento realizado.
        
        Returns:
            Dicionário com estatísticas detalhadas
        """
        return {
            'total_rejeitados': 0,  # Não remove nada na estratégia híbrida
            'total_corrigidos': self.registros_corrigidos_count,
            'total_com_erros': self.registros_com_erros_count,
            'total_com_erros_criticos': self.registros_com_erros_criticos_count,
            'total_erros_encontrados': self.total_erros_encontrados,
            'total_ajustes_manuais': self.ajustes_manuais_count,
            'tem_rejeicoes': False,  # Não remove nada na estratégia híbrida
            'tem_correcoes': self.registros_corrigidos_count > 0,
            'tem_erros': self.registros_com_erros_count > 0,
            'tem_erros_criticos': self.registros_com_erros_criticos_count > 0,
        }
    
    def obter_relatorio_erros(self) -> str:
        """
        Gera relatório detalhado de todos os erros encontrados.
        
        Returns:
            String formatada com relatório completo
        """
        if not self.erros_por_nf:
            return "[OK] Nenhum erro de validacao encontrado."
        
        linhas = ["=" * 60]
        linhas.append("RELATÓRIO DETALHADO DE ERROS DE VALIDAÇÃO")
        linhas.append("=" * 60)
        linhas.append(f"Total de NFs com erros: {len(self.erros_por_nf)}")
        linhas.append(f"Total de erros encontrados: {self.total_erros_encontrados}")
        linhas.append("=" * 60)
        
        for nf_num, erros in self.erros_por_nf.items():
            linhas.append(f"\nNF {nf_num}: {len(erros)} erro(s)")
            for erro in erros:
                linhas.append(f"  [{erro.severidade}] {erro.campo}: {erro.mensagem}")
        
        linhas.append("=" * 60)
        
        return "\n".join(linhas)
