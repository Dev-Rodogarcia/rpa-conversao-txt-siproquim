"""
Validador de campos extraídos do PDF.
Implementa validação de checksum/integridade para cada campo crítico.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional
from .validacao_constants import (
    PATTERN_DATA_BR, PATTERN_NF_NUMERO, PATTERN_CTE_NUMERO,
    PATTERN_CNPJ, PATTERN_CPF,
    NF_NUMERO_MIN_DIGITOS, NF_NUMERO_MAX_DIGITOS,
    CTE_NUMERO_MIN_DIGITOS, CTE_NUMERO_MAX_DIGITOS,
    NOME_MIN_CARACTERES, RECEBEDOR_MIN_CARACTERES,
    MensagensErro, ConfigValidacao
)
from ..gerador.validators import validar_cpf, validar_cnpj


class ErroValidacao:
    """Representa um erro de validação com contexto."""
    
    def __init__(self, campo: str, mensagem: str, valor: str = "", severidade: str = "ERRO"):
        """
        Args:
            campo: Nome do campo que falhou
            mensagem: Mensagem de erro descritiva
            valor: Valor que causou o erro (opcional)
            severidade: Nível de severidade (ERRO, AVISO, CRITICO)
        """
        self.campo = campo
        self.mensagem = mensagem
        self.valor = valor
        self.severidade = severidade
    
    def __str__(self) -> str:
        return f"[{self.severidade}] {self.campo}: {self.mensagem}"
    
    def __repr__(self) -> str:
        return f"ErroValidacao(campo='{self.campo}', severidade='{self.severidade}')"


class ValidadorCampos:
    """
    Classe responsável por validar todos os campos críticos de um registro.
    Implementa validação de checksum, formato e integridade.
    
    Esta é a segunda linha de defesa: valida os dados APÓS extração mas ANTES de gerar TXT.
    """
    
    def __init__(self, fail_fast: bool = ConfigValidacao.FAIL_FAST):
        """
        Args:
            fail_fast: Se True, para no primeiro erro. Se False, coleta todos os erros.
        """
        self.fail_fast = fail_fast
        self.erros_encontrados: List[ErroValidacao] = []

    @staticmethod
    def _normalizar_texto(valor: object) -> str:
        """Normaliza valores extraidos do PDF para evitar falsos 'None'."""
        if valor is None:
            return ""
        texto = str(valor).strip()
        if texto.upper() in {"NONE", "NULL", "N/A", "NA", "NAN"}:
            return ""
        return texto

    @staticmethod
    def _normalizar_documento(valor: object) -> str:
        """Retorna somente digitos de documento com tratamento de valores nulos."""
        texto = ValidadorCampos._normalizar_texto(valor)
        return ''.join(filter(str.isdigit, texto))
    
    def validar_registro_completo(self, registro: Dict) -> List[ErroValidacao]:
        """
        Valida TODOS os campos críticos de um registro.
        
        Args:
            registro: Dicionário com dados extraídos do PDF
        
        Returns:
            Lista de erros encontrados (vazia se tudo OK)
        """
        self.erros_encontrados = []
        nf_num = registro.get('nf_numero', 'N/A')
        
        # Validação de NF Número
        erro = self._validar_nf_numero(registro)
        if erro:
            self.erros_encontrados.append(erro)
            if self.fail_fast:
                return self.erros_encontrados
        
        # Validação de NF Data
        erro = self._validar_nf_data(registro)
        if erro:
            self.erros_encontrados.append(erro)
            if self.fail_fast:
                return self.erros_encontrados
        
        # Validação de CTe Número
        erro = self._validar_cte_numero(registro)
        if erro:
            self.erros_encontrados.append(erro)
            if self.fail_fast:
                return self.erros_encontrados
        
        # Validação de CTe Data
        erro = self._validar_cte_data(registro)
        if erro:
            self.erros_encontrados.append(erro)
            if self.fail_fast:
                return self.erros_encontrados
        
        # Validação de CNPJs/CPFs
        erros_cnpj = self._validar_todos_cnpjs(registro)
        if erros_cnpj:
            self.erros_encontrados.extend(erros_cnpj)
            if self.fail_fast:
                return self.erros_encontrados
        
        # Validação de Nomes
        erros_nomes = self._validar_todos_nomes(registro)
        if erros_nomes:
            self.erros_encontrados.extend(erros_nomes)
            if self.fail_fast:
                return self.erros_encontrados
        
        # Validação de Recebedor (campo obrigatório)
        erro = self._validar_recebedor(registro)
        if erro:
            self.erros_encontrados.append(erro)
            if self.fail_fast:
                return self.erros_encontrados
        
        return self.erros_encontrados
    
    # ========================================================================
    # VALIDADORES ESPECÍFICOS POR CAMPO
    # ========================================================================
    
    def _validar_nf_numero(self, registro: Dict) -> Optional[ErroValidacao]:
        """Valida número da Nota Fiscal."""
        nf_num = self._normalizar_texto(registro.get('nf_numero', ''))
        
        if not nf_num:
            return ErroValidacao(
                campo='nf_numero',
                mensagem=MensagensErro.NF_NUMERO_VAZIO,
                severidade='CRITICO'
            )
        
        if not PATTERN_NF_NUMERO.match(nf_num):
            return ErroValidacao(
                campo='nf_numero',
                mensagem=MensagensErro.NF_NUMERO_INVALIDO.format(
                    valor=nf_num,
                    min=NF_NUMERO_MIN_DIGITOS,
                    max=NF_NUMERO_MAX_DIGITOS
                ),
                valor=nf_num,
                severidade='CRITICO'
            )
        
        return None
    
    def _validar_nf_data(self, registro: Dict) -> Optional[ErroValidacao]:
        """Valida data da Nota Fiscal."""
        return self._validar_data_generica(
            registro.get('nf_data', ''),
            campo_nome='nf_data',
            msg_vazia=MensagensErro.NF_DATA_VAZIA,
            msg_formato=MensagensErro.NF_DATA_FORMATO_INVALIDO,
            msg_invalida=MensagensErro.NF_DATA_INVALIDA
        )
    
    def _validar_cte_numero(self, registro: Dict) -> Optional[ErroValidacao]:
        """Valida número do CTe."""
        cte_num = self._normalizar_texto(registro.get('cte_numero', ''))
        
        if not cte_num:
            return ErroValidacao(
                campo='cte_numero',
                mensagem=MensagensErro.CTE_NUMERO_VAZIO,
                severidade='ERRO'
            )
        
        if not PATTERN_CTE_NUMERO.match(cte_num):
            return ErroValidacao(
                campo='cte_numero',
                mensagem=MensagensErro.CTE_NUMERO_INVALIDO.format(
                    valor=cte_num,
                    min=CTE_NUMERO_MIN_DIGITOS,
                    max=CTE_NUMERO_MAX_DIGITOS
                ),
                valor=cte_num,
                severidade='ERRO'
            )
        
        return None
    
    def _validar_cte_data(self, registro: Dict) -> Optional[ErroValidacao]:
        """Valida data do CTe."""
        return self._validar_data_generica(
            registro.get('cte_data', ''),
            campo_nome='cte_data',
            msg_vazia=MensagensErro.CTE_DATA_VAZIA,
            msg_formato=MensagensErro.CTE_DATA_FORMATO_INVALIDO,
            msg_invalida=MensagensErro.CTE_DATA_INVALIDA,
            severidade_vazio='ERRO',
            severidade_formato='ERRO'
        )
    
    def _validar_data_generica(self, data_str: str, campo_nome: str,
                               msg_vazia: str, msg_formato: str, msg_invalida: str,
                               severidade_vazio: str = 'CRITICO',
                               severidade_formato: str = 'CRITICO') -> Optional[ErroValidacao]:
        """
        Validação genérica de data (dd/mm/aaaa).
        
        Args:
            data_str: String da data a validar
            campo_nome: Nome do campo (para mensagem de erro)
            msg_vazia: Mensagem se data está vazia
            msg_formato: Mensagem se formato inválido
            msg_invalida: Mensagem se data não existe
        
        Returns:
            ErroValidacao ou None se válida
        """
        data_str = self._normalizar_texto(data_str)
        
        if not data_str:
            return ErroValidacao(
                campo=campo_nome,
                mensagem=msg_vazia,
                severidade=severidade_vazio
            )
        
        if not PATTERN_DATA_BR.match(data_str):
            return ErroValidacao(
                campo=campo_nome,
                mensagem=msg_formato.format(valor=data_str),
                valor=data_str,
                severidade=severidade_formato
            )
        
        # Validação adicional: verifica se a data existe no calendário
        if ConfigValidacao.VALIDAR_DATA_CALENDARIO:
            try:
                datetime.strptime(data_str, '%d/%m/%Y')
            except ValueError:
                return ErroValidacao(
                    campo=campo_nome,
                    mensagem=msg_invalida.format(valor=data_str),
                    valor=data_str,
                    severidade='ERRO'
                )
        
        return None
    
    def _validar_todos_cnpjs(self, registro: Dict) -> List[ErroValidacao]:
        """Valida todos os CNPJs/CPFs do registro."""
        erros = []

        # Emitente deve ser CNPJ (14 dígitos) - CPF não é aceito neste campo
        erro_emitente = self._validar_cnpj_emitente(registro.get('emitente_cnpj', ''))
        if erro_emitente:
            erros.append(erro_emitente)
            if self.fail_fast:
                return erros
        
        # Contratante e Destinatário podem ser CPF (11) ou CNPJ (14)
        campos_cnpj = [
            ('contratante_cnpj', 'CNPJ Contratante'),
            ('destinatario_cnpj', 'CNPJ Destinatário'),
        ]
        
        for chave, nome_campo in campos_cnpj:
            erro = self._validar_cnpj(registro.get(chave, ''), nome_campo)
            if erro:
                erros.append(erro)
                if self.fail_fast:
                    break
        
        return erros

    def _validar_cnpj_emitente(self, cnpj_raw: str) -> Optional[ErroValidacao]:
        """
        Valida CNPJ do Emitente (deve ser 14 dígitos).
        CPF não é aceito neste campo.
        """
        cnpj = self._normalizar_documento(cnpj_raw)
        
        if not cnpj:
            return ErroValidacao(
                campo='CNPJ Emitente',
                mensagem=MensagensErro.CNPJ_VAZIO.format(campo='CNPJ Emitente'),
                severidade='CRITICO'
            )
        
        # Se veio CPF válido no campo de emitente
        if len(cnpj) == 11 and validar_cpf(cnpj):
            return ErroValidacao(
                campo='CNPJ Emitente',
                mensagem=f"CNPJ Emitente está como CPF ({cnpj}). Substitua por um CNPJ válido.",
                valor=cnpj,
                severidade='CRITICO'
            )
        
        if len(cnpj) != 14:
            return ErroValidacao(
                campo='CNPJ Emitente',
                mensagem=f"CNPJ Emitente tamanho inválido: {len(cnpj)} dígitos (esperado: 14).",
                valor=cnpj,
                severidade='CRITICO'
            )
        
        if not validar_cnpj(cnpj):
            return ErroValidacao(
                campo='CNPJ Emitente',
                mensagem=MensagensErro.CNPJ_MODULO11_FALHOU.format(
                    campo='CNPJ Emitente',
                    valor=cnpj
                ),
                valor=cnpj,
                severidade='CRITICO'
            )
        
        return None
    
    def _validar_cnpj(self, cnpj_raw: str, campo_nome: str) -> Optional[ErroValidacao]:
        """
        Valida CNPJ/CPF com checksum (Módulo 11).
        
        Args:
            cnpj_raw: CNPJ/CPF bruto (pode ter formatação)
            campo_nome: Nome do campo para mensagem de erro
        
        Returns:
            ErroValidacao ou None se válido
        """
        cnpj = self._normalizar_documento(cnpj_raw)
        
        if not cnpj:
            return ErroValidacao(
                campo=campo_nome,
                mensagem=MensagensErro.CNPJ_VAZIO.format(campo=campo_nome),
                severidade='CRITICO'
            )
        
        # Valida tamanho (11 para CPF, 14 para CNPJ)
        if len(cnpj) == 11:
            # É CPF - valida com Módulo 11
            if not validar_cpf(cnpj):
                return ErroValidacao(
                    campo=campo_nome,
                    mensagem=MensagensErro.CPF_MODULO11_FALHOU.format(
                        campo=campo_nome,
                        valor=cnpj
                    ),
                    valor=cnpj,
                    severidade='CRITICO'
                )
        elif len(cnpj) == 14:
            # É CNPJ - valida com Módulo 11
            if not validar_cnpj(cnpj):
                return ErroValidacao(
                    campo=campo_nome,
                    mensagem=MensagensErro.CNPJ_MODULO11_FALHOU.format(
                        campo=campo_nome,
                        valor=cnpj
                    ),
                    valor=cnpj,
                    severidade='CRITICO'
                )
        else:
            return ErroValidacao(
                campo=campo_nome,
                mensagem=MensagensErro.CNPJ_TAMANHO_INVALIDO.format(
                    campo=campo_nome,
                    tamanho=len(cnpj)
                ),
                valor=cnpj,
                severidade='CRITICO'
            )
        
        return None
    
    def _validar_todos_nomes(self, registro: Dict) -> List[ErroValidacao]:
        """Valida todos os nomes/razões sociais do registro."""
        erros = []
        
        campos_nome = [
            ('emitente_nome', 'Nome Emitente'),
            ('contratante_nome', 'Nome Contratante'),
            ('destinatario_nome', 'Nome Destinatário'),
        ]
        
        for chave, nome_campo in campos_nome:
            erro = self._validar_nome(registro.get(chave, ''), nome_campo)
            if erro:
                erros.append(erro)
                if self.fail_fast:
                    break
        
        return erros
    
    def _validar_nome(self, nome: str, campo_nome: str) -> Optional[ErroValidacao]:
        """
        Valida nome/razão social.
        
        Args:
            nome: Nome a validar
            campo_nome: Nome do campo para mensagem de erro
        
        Returns:
            ErroValidacao ou None se válido
        """
        nome = self._normalizar_texto(nome)
        
        if not nome:
            return ErroValidacao(
                campo=campo_nome,
                mensagem=MensagensErro.NOME_VAZIO.format(campo=campo_nome),
                severidade='ERRO'
            )
        
        if len(nome) < NOME_MIN_CARACTERES:
            return ErroValidacao(
                campo=campo_nome,
                mensagem=MensagensErro.NOME_MUITO_CURTO.format(
                    campo=campo_nome,
                    valor=nome,
                    min_chars=NOME_MIN_CARACTERES
                ),
                valor=nome,
                severidade='ERRO'
            )
        
        return None
    
    def _validar_recebedor(self, registro: Dict) -> Optional[ErroValidacao]:
        """
        Valida recebedor (campo obrigatório no SIPROQUIM).
        
        Args:
            registro: Dicionário com dados do registro
        
        Returns:
            ErroValidacao ou None se válido
        """
        recebedor = self._normalizar_texto(registro.get('recebedor', ''))
        
        if not recebedor:
            return ErroValidacao(
                campo='recebedor',
                mensagem=MensagensErro.RECEBEDOR_VAZIO,
                severidade='CRITICO'
            )
        
        if len(recebedor) < RECEBEDOR_MIN_CARACTERES:
            return ErroValidacao(
                campo='recebedor',
                mensagem=MensagensErro.RECEBEDOR_MUITO_CURTO.format(
                    valor=recebedor,
                    min_chars=RECEBEDOR_MIN_CARACTERES
                ),
                valor=recebedor,
                severidade='ERRO'
            )
        
        return None
    
    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================
    
    def obter_relatorio(self, nf_numero: str = 'N/A') -> str:
        """
        Gera relatório detalhado sobre os erros encontrados.
        
        Args:
            nf_numero: Número da NF para contexto
        
        Returns:
            String formatada com relatório de erros
        """
        if not self.erros_encontrados:
            return f"NF {nf_numero}: [OK] Todos os campos validos"
        
        linhas = [f"NF {nf_numero}: [X] {len(self.erros_encontrados)} erro(s) encontrado(s)"]
        
        # Agrupa por severidade
        criticos = [e for e in self.erros_encontrados if e.severidade == 'CRITICO']
        erros = [e for e in self.erros_encontrados if e.severidade == 'ERRO']
        avisos = [e for e in self.erros_encontrados if e.severidade == 'AVISO']
        
        if criticos:
            linhas.append(f"\n  CRITICOS ({len(criticos)}):")
            for erro in criticos:
                linhas.append(f"    - {erro.mensagem}")
        
        if erros:
            linhas.append(f"\n  ERROS ({len(erros)}):")
            for erro in erros:
                linhas.append(f"    - {erro.mensagem}")
        
        if avisos:
            linhas.append(f"\n  AVISOS ({len(avisos)}):")
            for aviso in avisos:
                linhas.append(f"    - {aviso.mensagem}")
        
        return "\n".join(linhas)
