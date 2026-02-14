"""
Processador de dados para SIPROQUIM.
Versão: HÍBRIDA (Auto-correção máxima + Delegação de erros para humano).
NENHUM REGISTRO É REMOVIDO.
"""

from typing import List, Dict, Optional, Callable
from ..gerador.validators import validar_cpf, validar_cnpj
from .base_conhecimento import BaseConhecimentoNomes


class SiproquimProcessor:
    """
    Processador HÍBRIDO: Corrige automaticamente o que pode, avisa sobre o que não consegue.
    
    Estratégia:
    - Tenta resolver automaticamente usando base de conhecimento
    - Mantém TODOS os registros no arquivo (não remove nada)
    - Avisa no log exatamente onde estão os problemas para correção manual
    """
    
    def __init__(self, callback_log: Optional[Callable[[str], None]] = None):
        """
        Args:
            callback_log: Função para imprimir logs na interface gráfica.
        """
        self.log = callback_log
        self.registros_corrigidos_count = 0
    
    def _log_gui(self, tipo: str, mensagem: str):
        """Envia mensagem para o log da tela preta ou GUI."""
        msg_formatada = f"[{tipo}] {mensagem}"
        if self.log:
            self.log(msg_formatada)
        else:
            print(msg_formatada)

    @staticmethod
    def _normalizar_texto(valor: object) -> str:
        if valor is None:
            return ""
        texto = str(valor).strip()
        if texto.upper() in {"NONE", "NULL", "N/A", "NA", "NAN"}:
            return ""
        return texto

    @staticmethod
    def _normalizar_documento(valor: object) -> str:
        texto = SiproquimProcessor._normalizar_texto(valor)
        return ''.join(filter(str.isdigit, texto))
    
    def filtrar_dados_validos(self, nfs_extraidas: List[Dict]) -> List[Dict]:
        """
        Processa as NFs: corrige o que pode, audita o que não pode, e retorna TUDO.
        
        Args:
            nfs_extraidas: Lista de dicionários com dados brutos extraídos do PDF
            
        Returns:
            Lista com TODOS os registros (nada é removido, apenas corrigido ou avisado)
        """
        nfs_finais: List[Dict] = []
        self.registros_corrigidos_count = 0
        
        self._log_gui("INFO", f"Processando {len(nfs_extraidas)} registros com estratégia HÍBRIDA...")
        
        for nf in nfs_extraidas:
            # 1. TENTA RESOLVER SOZINHO (Auto-correção)
            self._tentar_corrigir_dados(nf)
            
            # 2. AUDITA O QUE RESTOU (Aponta erros para o humano)
            self._auditar_para_humano(nf)
            
            # 3. MANTÉM O REGISTRO (Não deleta nada)
            nfs_finais.append(nf)
        
        self._log_gui("INFO", f"Processamento finalizado.")
        self._log_gui("INFO", f" -> Corrigidos automaticamente: {self.registros_corrigidos_count}")
        self._log_gui("INFO", f" -> Total exportado para TXT: {len(nfs_finais)}")
        
        return nfs_finais
    
    def _tentar_corrigir_dados(self, nf: Dict) -> None:
        """Tenta preencher nomes vazios usando a base de conhecimento."""
        campos = [
            ('destinatario_cnpj', 'destinatario_nome', 'Destinatário'),
            ('contratante_cnpj', 'contratante_nome', 'Contratante'),
            ('emitente_cnpj', 'emitente_nome', 'Emitente')
        ]

        for chave_cnpj, chave_nome, tipo_pessoa in campos:
            cnpj = self._normalizar_documento(nf.get(chave_cnpj, ''))
            nome = self._normalizar_texto(nf.get(chave_nome, ''))

            # Se tem CNPJ válido mas está sem nome
            if len(cnpj) == 14 and len(nome) < 2:
                nome_base = BaseConhecimentoNomes.buscar_nome_por_cnpj(cnpj)
                if nome_base:
                    nf[chave_nome] = nome_base
                    self.registros_corrigidos_count += 1
                    nf_num = nf.get('nf_numero', 'N/A')
                    self._log_gui("SUCESSO", f"NF {nf_num}: Auto-correção aplicada para CNPJ {cnpj} ({tipo_pessoa}) -> {nome_base}")

    def _auditar_para_humano(self, nf: Dict) -> None:
        """
        Verifica problemas que o robô não conseguiu resolver e avisa o humano.
        NÃO remove o registro. Aponta EXATAMENTE onde está o problema.
        """
        nf_num = nf.get('nf_numero', 'N/A')
        
        # --- VERIFICAÇÃO 1: CPF NO LUGAR DE CNPJ (Caso Leonardo/Thalita) ---
        # O SIPROQUIM exige CNPJ (14 dígitos). Se for CPF (11 dígitos), o humano precisa decidir.
        for chave, tipo_pessoa in [('contratante_cnpj', 'Contratante'), ('destinatario_cnpj', 'Destinatário')]:
            doc = self._normalizar_documento(nf.get(chave, ''))
            
            if len(doc) == 11 and validar_cpf(doc):
                self._log_gui("ACAO_NECESSARIA", f"NF {nf_num}: {tipo_pessoa} é CPF ({doc}) ao invés de CNPJ.")
                self._log_gui("ACAO_NECESSARIA", f"   -> O registro foi mantido no TXT. Abra o arquivo gerado, procure por '{doc}' (ou NF {nf_num}) e substitua por um CNPJ válido da empresa.")

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
                self._log_gui("ATENCAO", f"NF {nf_num}: CNPJ {cnpj} ({tipo_pessoa}) está SEM NOME (não encontrado na base de conhecimento).")
                self._log_gui("ATENCAO", f"   -> O registro foi mantido no TXT. Abra o arquivo gerado, procure por '{cnpj}' (ou NF {nf_num}) e preencha o nome da empresa manualmente.")
        
        # --- VERIFICAÇÃO 3: CNPJ EMITENTE INVÁLIDO ---
        cnpj_emitente = self._normalizar_documento(nf.get('emitente_cnpj', ''))
        
        if cnpj_emitente:
            if len(cnpj_emitente) != 14:
                self._log_gui("ACAO_NECESSARIA", f"NF {nf_num}: CNPJ Emitente tem tamanho incorreto ({len(cnpj_emitente)} dígitos: {cnpj_emitente}).")
                self._log_gui("ACAO_NECESSARIA", f"   -> O registro foi mantido no TXT. Abra o arquivo gerado, procure por NF {nf_num} e verifique o CNPJ do emitente.")
            elif not validar_cnpj(cnpj_emitente):
                self._log_gui("ACAO_NECESSARIA", f"NF {nf_num}: CNPJ Emitente inválido ({cnpj_emitente}) - não passa na validação matemática.")
                self._log_gui("ACAO_NECESSARIA", f"   -> O registro foi mantido no TXT. Abra o arquivo gerado, procure por NF {nf_num} e verifique o CNPJ do emitente.")
    
    def obter_estatisticas(self) -> Dict:
        """
        Retorna estatísticas sobre o processamento realizado.
        
        Returns:
            Dicionário com estatísticas (compatível com código existente)
        """
        return {
            'total_rejeitados': 0,  # Não remove nada na estratégia híbrida
            'total_corrigidos': self.registros_corrigidos_count,
            'tem_rejeicoes': False,  # Não remove nada na estratégia híbrida
            'tem_correcoes': self.registros_corrigidos_count > 0
        }
