"""
Módulo principal de geração de arquivos TXT no formato SIPROQUIM/Rodogarcia.
Implementa as seções EM, TN e CC conforme especificação técnica.
"""

import warnings
import re
from typing import Dict, List, Optional
from .sanitizers import sanitizar_texto, sanitizar_numerico, sanitizar_alfanumerico
from .validators import validar_cnpj, validar_cpf, is_cpf_convertido, parece_pessoa_fisica_pelo_nome
from .layout_constants import (
    # Constantes EM
    EM_TAMANHO_TOTAL, EM_TAM_TIPO, EM_TAM_CNPJ, EM_TAM_MES, EM_TAM_ANO,
    EM_TIPO, mes_numero_para_alfanumerico, gerar_flags_em,
    # Constantes TN
    TN_TAMANHO_TOTAL, TN_TAM_TIPO, TN_TAM_CNPJ, TN_TAM_NOME, TN_TAM_NF_NUMERO, TN_TAM_NF_DATA, TN_TAM_LOCAL,
    TN_TIPO, TN_LOCAL_PROPRIO,
    # Constantes CC
    CC_TAMANHO_TOTAL, CC_TAM_TIPO, CC_TAM_CTE_NUMERO, CC_TAM_DATA, CC_TAM_RECEBEDOR, CC_TAM_MODAL,
    CC_TIPO, CC_MODAL_RODOVIARIO,
    # Constantes de validação
    MES_MINIMO, MES_MAXIMO, ANO_MINIMO, ANO_MAXIMO,
    # Constantes compartilhadas
    CNPJ_TAMANHO, RECEBEDOR_NAO_INFORMADO
)


class GeradorTXT:
    """Classe responsável pela geração do arquivo TXT no formato SIPROQUIM."""
    
    def __init__(self, cnpj_rodogarcia: str):
        """
        Inicializa o gerador com o CNPJ da Rodogarcia.
        
        Args:
            cnpj_rodogarcia: CNPJ da Rodogarcia (será usado na seção EM)
        """
        self.cnpj_rodogarcia = sanitizar_numerico(cnpj_rodogarcia, EM_TAM_CNPJ)

    def _emitir_alerta(self, mensagem: str, callback_progresso=None, tipo: str = "ACAO_NECESSARIA",
                       nf_num: Optional[str] = None) -> None:
        """
        Emite aviso para CLI (warnings) e para GUI (callback_progresso).
        """
        # CLI / stdout
        warnings.warn(mensagem.replace('\n', ' '), UserWarning)
        # GUI / callback
        if callback_progresso:
            callback_progresso('processar_log', {
                'tipo': tipo,
                'mensagem': mensagem
            })
            callback_progresso('ajuste_manual', {
                'nf': nf_num,
                'tipo': tipo,
                'mensagem': mensagem
            })
    
    def gerar_linha_EM(self, mes: int, ano: int) -> str:
        """
        Gera a linha EM (Cabeçalho) do arquivo conforme Manual SIPROQUIM 3.1.1.
        
        Args:
            mes: Mês de referência (1-12)
            ano: Ano de referência (ex: 2025)
        
        Returns:
            Linha EM formatada com exatamente {EM_TAMANHO_TOTAL} caracteres
        """
        # Validação de entrada usando constantes
        if not (MES_MINIMO <= mes <= MES_MAXIMO):
            raise ValueError(f"Mês deve estar entre {MES_MINIMO} e {MES_MAXIMO}, recebido: {mes}")
        if not (ANO_MINIMO <= ano <= ANO_MAXIMO):
            raise ValueError(f"Ano deve estar entre {ANO_MINIMO} e {ANO_MAXIMO}, recebido: {ano}")
        
        # Validação do CNPJ
        if len(self.cnpj_rodogarcia) != EM_TAM_CNPJ:
            raise ValueError(f"CNPJ deve ter {EM_TAM_CNPJ} dígitos, recebido: {len(self.cnpj_rodogarcia)}")
        
        # Converter mês numérico para alfanumérico (JAN, FEV, etc.)
        mes_alfanumerico = mes_numero_para_alfanumerico(mes)
        
        # Montar linha com posições corretas usando constantes
        linha = EM_TIPO
        linha += self.cnpj_rodogarcia
        linha += sanitizar_texto(mes_alfanumerico, EM_TAM_MES)
        linha += sanitizar_numerico(str(ano), EM_TAM_ANO)
        
        # Flags na posição correta usando função helper
        flags = gerar_flags_em(transporte=True)
        linha += flags
        
        # Validação crítica: linha deve ter exatamente EM_TAMANHO_TOTAL caracteres
        if len(linha) != EM_TAMANHO_TOTAL:
            raise ValueError(
                f"Linha EM deve ter exatamente {EM_TAMANHO_TOTAL} caracteres, mas tem {len(linha)}. "
                f"CNPJ: {self.cnpj_rodogarcia}, Mês: {mes_alfanumerico}, Ano: {ano}"
            )
        
        return linha
    
    def gerar_linha_TN(self, dados_nf: Dict, callback_progresso=None) -> str:
        """
        Gera a linha TN (Transporte Nacional) conforme layout 3.1.9.
        
        Args:
            dados_nf: Dicionário com os dados da Nota Fiscal extraídos do PDF
            callback_progresso: Callback opcional para logs na GUI
        
        Returns:
            Linha TN formatada com exatamente TN_TAMANHO_TOTAL caracteres
        
        Observação:
            Erros de documento (CPF/CNPJ inválido) geram avisos para ajuste manual,
            mas não impedem a geração do arquivo.
        """
        # CRÍTICO: Validação ANTES de formatar para evitar enviar "lixo" ao SIPROQUIM
        # O validador do SIPROQUIM valida o número formatado (14 dígitos) como CNPJ
        # Se formatarmos um CPF válido para 14 dígitos, ele não passará na validação de CNPJ
        
        # Extrai apenas dígitos dos valores originais (ANTES de formatar)
        cnpj_contratante_raw = dados_nf.get('contratante_cnpj', '')
        cnpj_origem_raw = dados_nf.get('emitente_cnpj', '')
        cnpj_destino_raw = dados_nf.get('destinatario_cnpj', '')
        
        cnpj_contratante_limpo = ''.join(filter(str.isdigit, str(cnpj_contratante_raw)))
        cnpj_origem_limpo = ''.join(filter(str.isdigit, str(cnpj_origem_raw)))
        cnpj_destino_limpo = ''.join(filter(str.isdigit, str(cnpj_destino_raw)))
        
        # Validação de CNPJs/CPFs usando algoritmo oficial
        # CRÍTICO: Diferencia CPF de CNPJ baseado apenas no tamanho (11 vs 14 dígitos)
        nf_num_display = str(dados_nf.get('nf_numero', '')).strip() or "N/A"

        def alertar(mensagem: str, tipo: str = "ACAO_NECESSARIA") -> None:
            self._emitir_alerta(mensagem, callback_progresso, tipo=tipo, nf_num=nf_num_display)
        
        # Validação para CNPJ Contratante: pode ser CPF (11 dígitos) ou CNPJ (14 dígitos)
        # CORREÇÃO: Usa dados_nf.get() diretamente pois nome_contratante ainda não foi definido
        nome_contratante_raw = dados_nf.get('contratante_nome', '')
        if not cnpj_contratante_limpo:
            alertar(
                f"NF {nf_num_display}: Documento Contratante vazio. "
                f"Verifique o CNPJ/CPF extraído do PDF."
            )
        elif len(cnpj_contratante_limpo) == 11:
            # É CPF - valida como CPF
            if not validar_cpf(cnpj_contratante_limpo):
                alertar(
                    f"NF {nf_num_display}: CPF Contratante inválido: {cnpj_contratante_limpo}. "
                    f"Nome: {nome_contratante_raw[:50]}. "
                    f"Verifique se o CPF foi extraído corretamente do PDF."
                )
        elif len(cnpj_contratante_limpo) == 14:
            # É CNPJ - valida como CNPJ
            if not validar_cnpj(cnpj_contratante_limpo):
                # Verifica se o nome parece ser de pessoa física
                if parece_pessoa_fisica_pelo_nome(nome_contratante_raw):
                    alertar(
                        f"NF {nf_num_display}: CNPJ Contratante inválido ({cnpj_contratante_limpo}), "
                        f"mas o nome indica pessoa física. Verifique o documento.",
                        tipo="ATENCAO"
                    )
                else:
                    alertar(
                        f"NF {nf_num_display}: CNPJ Contratante inválido: {cnpj_contratante_limpo}. "
                        f"Nome: {nome_contratante_raw[:50]}. "
                        f"Verifique se o CNPJ foi extraído corretamente do PDF."
                    )
        else:
            alertar(
                f"NF {nf_num_display}: Documento Contratante inválido "
                f"(deve ter 11 ou 14 dígitos): {cnpj_contratante_limpo}. "
                f"Nome: {nome_contratante_raw[:50]}."
            )
        
        # Validação para CNPJ Origem (Emitente) - deve ser CNPJ (14 dígitos)
        # CORREÇÃO: Usa dados_nf.get() diretamente pois nome_origem ainda não foi definido
        nome_origem_raw = dados_nf.get('emitente_nome', '')
        if not cnpj_origem_limpo:
            alertar(
                f"NF {nf_num_display}: CNPJ Emitente vazio. Verifique o emitente no PDF."
            )
        elif len(cnpj_origem_limpo) == 11 and validar_cpf(cnpj_origem_limpo):
            alertar(
                f"NF {nf_num_display}: Emitente está com CPF ({cnpj_origem_limpo}) no lugar de CNPJ. "
                f"Nome: {nome_origem_raw[:50]}."
            )
        elif len(cnpj_origem_limpo) != 14:
            alertar(
                f"NF {nf_num_display}: CNPJ Origem (Emitente) deve ter 14 dígitos, "
                f"recebido: {len(cnpj_origem_limpo)}. Valor: {cnpj_origem_limpo}. "
                f"Nome: {nome_origem_raw[:50]}."
            )
        elif not validar_cnpj(cnpj_origem_limpo):
            alertar(
                f"NF {nf_num_display}: CNPJ Origem (Emitente) inválido: {cnpj_origem_limpo}. "
                f"Nome: {nome_origem_raw[:50]}. "
                f"Verifique se o CNPJ foi extraído corretamente do PDF."
            )
        
        # Validação para CNPJ Destino: pode ser CPF (11 dígitos) ou CNPJ (14 dígitos)
        # CORREÇÃO: Usa dados_nf.get() diretamente pois nome_destino ainda não foi definido
        nome_destino_raw = dados_nf.get('destinatario_nome', '')
        if not cnpj_destino_limpo:
            alertar(
                f"NF {nf_num_display}: Documento Destino vazio. Verifique o destinatário no PDF."
            )
        elif len(cnpj_destino_limpo) == 11:
            # É CPF - valida como CPF
            if not validar_cpf(cnpj_destino_limpo):
                alertar(
                    f"NF {nf_num_display}: CPF Destino (Destinatário) inválido: {cnpj_destino_limpo}. "
                    f"Nome: {nome_destino_raw[:50]}. "
                    f"Verifique se o CPF foi extraído corretamente do PDF."
                )
        elif len(cnpj_destino_limpo) == 14:
            # É CNPJ - valida como CNPJ
            if not validar_cnpj(cnpj_destino_limpo):
                # Verifica se o nome parece ser de pessoa física
                if parece_pessoa_fisica_pelo_nome(nome_destino_raw):
                    alertar(
                        f"NF {nf_num_display}: CNPJ Destino inválido ({cnpj_destino_limpo}), "
                        f"mas o nome indica pessoa física. Verifique o documento.",
                        tipo="ATENCAO"
                    )
                else:
                    alertar(
                        f"NF {nf_num_display}: CNPJ Destino (Destinatário) inválido: {cnpj_destino_limpo}. "
                        f"Nome: {nome_destino_raw[:50]}. "
                        f"Verifique se o CNPJ foi extraído corretamente do PDF."
                    )
        else:
            alertar(
                f"NF {nf_num_display}: Documento Destino inválido "
                f"(deve ter 11 ou 14 dígitos): {cnpj_destino_limpo}. "
                f"Nome: {nome_destino_raw[:50]}."
            )
        
        # VALIDAÇÃO CRÍTICA: Verifica se CPF formatado para 14 dígitos passará na validação do SIPROQUIM
        # O SIPROQUIM valida o número formatado (14 dígitos) como CNPJ
        # Se um CPF válido for formatado para 14 dígitos, ele NÃO passará na validação de CNPJ
        # Isso causa o erro "O CPF/CNPJ ... é inválido" no SIPROQUIM
        
        def verificar_cpf_formatado_sera_rejeitado(cpf_limpo: str, nome: str, campo: str) -> None:
            """
            Verifica se um CPF válido, quando formatado para 14 dígitos, falha na validação de CNPJ.
            
            CORREÇÃO: Mudado de raise ValueError para warnings.warn para permitir geração do arquivo.
            Um CPF formatado com zeros à esquerda NUNCA será um CNPJ válido matematicamente,
            mas o arquivo deve ser gerado para tentativa de envio ou análise manual.
            """
            if len(cpf_limpo) == 11 and validar_cpf(cpf_limpo):
                # Formata o CPF para 14 dígitos (zeros à esquerda)
                cpf_formatado = cpf_limpo.zfill(14)
                # Verifica se o número formatado passa na validação de CNPJ
                # Sabemos que vai falhar na validação matemática de CNPJ
                if not validar_cnpj(cpf_formatado):
                    self._emitir_alerta(
                        f"NF {nf_num_display}: CPF {campo} válido ({cpf_limpo}) não passa na validação "
                        f"matemática de CNPJ quando formatado com zeros ({cpf_formatado}). "
                        f"Nome: {nome[:50]}. O SIPROQUIM pode rejeitar este registro.",
                        callback_progresso,
                        tipo="ALERTA",
                        nf_num=nf_num_display
                    )
        
        # Verifica cada campo que pode conter CPF
        verificar_cpf_formatado_sera_rejeitado(cnpj_contratante_limpo, dados_nf.get('contratante_nome', ''), "Contratante")
        verificar_cpf_formatado_sera_rejeitado(cnpj_destino_limpo, dados_nf.get('destinatario_nome', ''), "Destino")
        
        # NOVA VALIDAÇÃO: Avisa se contratante e destino são iguais
        # (pode causar erro no SIPROQUIM se não estiver configurado corretamente)
        # Usa os valores já limpos da validação anterior
        if (cnpj_contratante_limpo == cnpj_destino_limpo and 
            cnpj_contratante_limpo != "0" * 14 and
            cnpj_contratante_limpo != "0" * 11 and
            len(cnpj_contratante_limpo) in [11, 14]):
            # Avisa mas não bloqueia - pode ser válido em alguns casos
            nf_num_display = str(dados_nf.get('nf_numero', '')).strip() if dados_nf.get('nf_numero') else "N/A"
            tipo_doc = "CPF" if len(cnpj_contratante_limpo) == 11 else "CNPJ"
            self._emitir_alerta(
                f"NF {nf_num_display}: {tipo_doc} Contratante ({cnpj_contratante_limpo}) igual ao "
                f"{tipo_doc} Destino. Isso pode causar erro no SIPROQUIM.",
                callback_progresso,
                tipo="ATENCAO",
                nf_num=nf_num_display
            )
        
        # AGORA sim, formata os valores após validação
        nome_contratante = sanitizar_texto(dados_nf.get('contratante_nome'), TN_TAM_NOME)
        nf_numero = sanitizar_alfanumerico(dados_nf.get('nf_numero'), TN_TAM_NF_NUMERO)
        nf_data = sanitizar_texto(dados_nf.get('nf_data'), TN_TAM_NF_DATA)
        nome_origem = sanitizar_texto(dados_nf.get('emitente_nome'), TN_TAM_NOME)
        nome_destino = sanitizar_texto(dados_nf.get('destinatario_nome'), TN_TAM_NOME)
        local_retirada = dados_nf.get('local_retirada', TN_LOCAL_PROPRIO)
        local_entrega = dados_nf.get('local_entrega', TN_LOCAL_PROPRIO)

        # Alerta se algum nome ficou vazio após sanitização (campo obrigatório no layout)
        def verificar_nome_vazio(nome_sanitizado: str, campo: str, cnpj_raw: str) -> None:
            if not nome_sanitizado.strip():
                cnpj_limpo = ''.join(filter(str.isdigit, str(cnpj_raw))) or "N/A"
                alertar(
                    f"NF {nf_num_display}: {campo} vazio no TXT (CNPJ {cnpj_limpo}). "
                    f"Preencha manualmente no arquivo gerado.",
                    tipo="ACAO_NECESSARIA"
                )

        verificar_nome_vazio(nome_contratante, "Nome Contratante", cnpj_contratante_raw)
        verificar_nome_vazio(nome_origem, "Nome Emitente", cnpj_origem_raw)
        verificar_nome_vazio(nome_destino, "Nome Destinatário", cnpj_destino_raw)
        
        # Formata os CNPJs/CPFs para 14 dígitos (após validação)
        cnpj_contratante = sanitizar_numerico(cnpj_contratante_raw, TN_TAM_CNPJ)
        cnpj_origem = sanitizar_numerico(cnpj_origem_raw, TN_TAM_CNPJ)
        cnpj_destino = sanitizar_numerico(cnpj_destino_raw, TN_TAM_CNPJ)
        
        # Montagem posicional rígida usando constantes
        linha = TN_TIPO
        linha += cnpj_contratante
        linha += nome_contratante
        linha += nf_numero
        linha += nf_data
        linha += cnpj_origem
        linha += nome_origem
        linha += cnpj_destino
        linha += nome_destino
        linha += local_retirada
        linha += local_entrega
        
        # Validação crítica: linha deve ter exatamente TN_TAMANHO_TOTAL caracteres
        if len(linha) != TN_TAMANHO_TOTAL:
            raise ValueError(
                f"Linha TN deve ter exatamente {TN_TAMANHO_TOTAL} caracteres, mas tem {len(linha)}. "
                f"Campos: Tipo={len(TN_TIPO)}, CNPJ_Cont={len(cnpj_contratante)}, "
                f"Nome_Cont={len(nome_contratante)}, NF={len(nf_numero)}, "
                f"Data={len(nf_data)}, CNPJ_Orig={len(cnpj_origem)}, "
                f"Nome_Orig={len(nome_origem)}, CNPJ_Dest={len(cnpj_destino)}, "
                f"Nome_Dest={len(nome_destino)}"
            )
        
        return linha
    
    def gerar_linha_CC(self, dados_cte: Dict, callback_progresso=None) -> str:
        """
        Gera a linha CC (Conhecimento de Carga) conforme layout 3.1.9.1.
        
        Args:
            dados_cte: Dicionário com os dados do CTe extraídos do PDF
            callback_progresso: Callback opcional para logs na GUI
        
        Returns:
            Linha CC formatada com exatamente CC_TAMANHO_TOTAL caracteres
        
        Raises:
            ValueError: Se o CTe número ou data estiverem inválidos
        """
        # NOVA VALIDAÇÃO: Verifica se o CTe tem dados válidos antes de processar
        cte_numero_raw = dados_cte.get('cte_numero', '')
        cte_data_raw = dados_cte.get('cte_data', '')
        
        # Se o CTe número está vazio ou None, pode causar erro no SIPROQUIM
        if not cte_numero_raw or str(cte_numero_raw).strip() == '':
            raise ValueError(
                f"CTe número inválido ou não encontrado. "
                f"Verifique se o CTe foi extraído corretamente do PDF. "
                f"NF: {dados_cte.get('nf_numero', 'N/A')}"
            )
        
        # Sanitização usando constantes
        cte_numero = sanitizar_numerico(cte_numero_raw, CC_TAM_CTE_NUMERO)
        
        # Se o CTe número está vazio ou só zeros após sanitização, pode causar erro
        if cte_numero == "0" * CC_TAM_CTE_NUMERO:
            raise ValueError(
                f"CTe número inválido (apenas zeros). "
                f"Verifique se o CTe foi extraído corretamente do PDF. "
                f"NF: {dados_cte.get('nf_numero', 'N/A')}"
            )
        
        # Se a data do CTe está vazia, pode causar erro
        if not cte_data_raw or str(cte_data_raw).strip() == '':
            raise ValueError(
                f"CTe data inválida ou não encontrada. "
                f"Verifique se a data do CTe foi extraída corretamente do PDF. "
                f"NF: {dados_cte.get('nf_numero', 'N/A')}"
            )
        
        cte_data = sanitizar_texto(cte_data_raw, CC_TAM_DATA)
        
        # Se a data do CTe está vazia após sanitização, pode causar erro
        if not cte_data or cte_data.strip() == "" or cte_data.strip() == " " * CC_TAM_DATA:
            raise ValueError(
                f"CTe data inválida (apenas espaços). "
                f"Verifique se a data do CTe foi extraída corretamente do PDF. "
                f"NF: {dados_cte.get('nf_numero', 'N/A')}"
            )
        
        # Data Recebimento: se vazio, repete data CTe
        data_recebimento = dados_cte.get('data_entrega', '')
        if not data_recebimento:
            data_recebimento = cte_data
        data_recebimento = sanitizar_texto(data_recebimento, CC_TAM_DATA)
        
        # FALLBACK CRÍTICO: Campo "Responsável pelo Recebimento" é OBRIGATÓRIO no SIPROQUIM
        # Se não encontrou recebedor, usa destinatário (quem recebe a carga)
        recebedor = dados_cte.get('recebedor')
        if not recebedor:
            recebedor = dados_cte.get('destinatario_nome')
        if not recebedor:
            recebedor = dados_cte.get('contratante_nome')
        if not recebedor:
            recebedor = dados_cte.get('emitente_nome')
        
        # NOVA VALIDAÇÃO: Garante que o recebedor não seja muito curto
        # O SIPROQUIM pode rejeitar recebedores com menos de 3 caracteres
        if recebedor:
            recebedor_limpo = str(recebedor).strip()
            # Se o recebedor tem menos de 3 caracteres, tenta usar alternativas
            if len(recebedor_limpo) < 3:
                # Tenta usar destinatário se disponível e válido
                if dados_cte.get('destinatario_nome'):
                    dest_limpo = str(dados_cte.get('destinatario_nome')).strip()
                    if len(dest_limpo) >= 3:
                        recebedor = dados_cte.get('destinatario_nome')
                    elif dados_cte.get('contratante_nome'):
                        cont_limpo = str(dados_cte.get('contratante_nome')).strip()
                        if len(cont_limpo) >= 3:
                            recebedor = dados_cte.get('contratante_nome')
                    elif dados_cte.get('emitente_nome'):
                        emit_limpo = str(dados_cte.get('emitente_nome')).strip()
                        if len(emit_limpo) >= 3:
                            recebedor = dados_cte.get('emitente_nome')
        
        # Se ainda estiver vazio após todos os fallbacks, usa valor padrão
        if not recebedor:
            recebedor = RECEBEDOR_NAO_INFORMADO
        else:
            # Verifica novamente após fallbacks
            recebedor_limpo_final = str(recebedor).strip()
            if len(recebedor_limpo_final) < 3:
                recebedor = RECEBEDOR_NAO_INFORMADO

        # Revisão e alerta para recebedores suspeitos (assinatura/rubrica/CPF/etc.)
        nf_num_display = str(dados_cte.get('nf_numero', '')).strip() or "N/A"
        recebedor_raw = str(recebedor).strip()

        def motivos_suspeitos(valor: str) -> list:
            motivos = []
            if not valor:
                return motivos
            valor_upper = valor.upper()
            termos_suspeitos = [
                "ASSINATURA", "ASSINADO", "ASSINADO E CARIMBADO",
                "RUBRICA", "ASS"
            ]
            if valor_upper in termos_suspeitos or any(t in valor_upper for t in termos_suspeitos):
                motivos.append("texto de assinatura/rubrica")
            if len(valor) < 5:
                motivos.append("muito curto")
            if re.search(r"\b\d{11}\b", valor):
                motivos.append("contém CPF")
            if valor == RECEBEDOR_NAO_INFORMADO:
                motivos.append("não informado")
            return motivos

        def candidato_valido(valor: str) -> bool:
            if not valor:
                return False
            valor_limpo = str(valor).strip()
            if len(valor_limpo) < 5:
                return False
            if "ASSINATURA" in valor_limpo.upper() or "RUBRICA" in valor_limpo.upper():
                return False
            return True

        motivos = motivos_suspeitos(recebedor_raw)
        if motivos:
            # Se parece assinatura/CPF/não informado, tenta substituir por destinatário/contratante/emitente
            auto_revisar = any(m in ("texto de assinatura/rubrica", "contém CPF", "não informado") for m in motivos)
            if auto_revisar:
                candidatos = [
                    dados_cte.get('destinatario_nome'),
                    dados_cte.get('contratante_nome'),
                    dados_cte.get('emitente_nome')
                ]
                substituto = None
                for cand in candidatos:
                    if candidato_valido(cand):
                        substituto = str(cand).strip()
                        break
                if substituto:
                    self._emitir_alerta(
                        f"NF {nf_num_display}: Recebedor suspeito ({', '.join(motivos)}): "
                        f"'{recebedor_raw}'. Substituído por '{substituto}'.",
                        callback_progresso,
                        tipo="ATENCAO",
                        nf_num=nf_num_display
                    )
                    recebedor_raw = substituto
                else:
                    self._emitir_alerta(
                        f"NF {nf_num_display}: Recebedor suspeito ({', '.join(motivos)}): '{recebedor_raw}'. "
                        f"Verifique e ajuste manualmente se necessário.",
                        callback_progresso,
                        tipo="ATENCAO",
                        nf_num=nf_num_display
                    )
            else:
                # Muito curto: apenas alerta (não substitui automaticamente)
                self._emitir_alerta(
                    f"NF {nf_num_display}: Recebedor suspeito ({', '.join(motivos)}): '{recebedor_raw}'. "
                    f"Verifique e ajuste manualmente se necessário.",
                    callback_progresso,
                    tipo="ATENCAO",
                    nf_num=nf_num_display
                )

        recebedor = recebedor_raw if recebedor_raw else RECEBEDOR_NAO_INFORMADO
        
        recebedor = sanitizar_texto(recebedor, CC_TAM_RECEBEDOR)
        
        # Montagem posicional usando constantes
        linha = CC_TIPO
        linha += cte_numero
        linha += cte_data
        linha += data_recebimento
        linha += recebedor
        linha += CC_MODAL_RODOVIARIO
        
        # Validação: linha deve ter exatamente CC_TAMANHO_TOTAL caracteres
        if len(linha) != CC_TAMANHO_TOTAL:
            raise ValueError(
                f"Linha CC deve ter exatamente {CC_TAMANHO_TOTAL} caracteres, mas tem {len(linha)}. "
                f"Campos: Tipo={len(CC_TIPO)}, CTe={len(cte_numero)}, "
                f"Data_CTe={len(cte_data)}, Data_Rec={len(data_recebimento)}, "
                f"Recebedor={len(recebedor)}, Modal={len(CC_MODAL_RODOVIARIO)}"
            )
        
        return linha
    
    def gerar_arquivo(self, nfs_deduplicadas: list, mes: int, ano: int, 
                     caminho_saida: str, callback_progresso=None) -> str:
        """
        Gera o arquivo TXT completo com todas as seções.
        
        Args:
            nfs_deduplicadas: Lista de dicionários, cada um representando uma NF única
                             com seus dados e CTe associado
            mes: Mês de referência
            ano: Ano de referência
            caminho_saida: Caminho onde o arquivo será salvo
            callback_progresso: Função opcional chamada durante geração.
                               Recebe (etapa, detalhes) como parâmetros.
                               Etapas: 'gerar', 'aviso', 'finalizar'
        
        Returns:
            Caminho do arquivo gerado
        
        Observação:
            Inconsistências de CPF/CNPJ e possíveis rejeições são registradas como alertas,
            mas o arquivo é gerado para permitir ajustes manuais.
        """
        linhas = []
        cnpjs_validos_alertas = set()  # Para coletar CNPJs que podem não estar cadastrados
        
        # Linha EM (cabeçalho - apenas uma por arquivo)
        linhas.append(self.gerar_linha_EM(mes, ano))
        
        # Para cada NF, gerar linha TN seguida de sua linha CC
        for nf in nfs_deduplicadas:
            try:
                linhas.append(self.gerar_linha_TN(nf, callback_progresso=callback_progresso))
            except ValueError as e:
                # Erro estrutural inesperado (ex.: tamanho da linha)
                raise ValueError(
                    f"Erro ao gerar linha TN para NF {nf.get('nf_numero', 'N/A')}: {str(e)}"
                ) from e
            
            # Coleta CNPJs para aviso (mesmo sendo válidos, podem não estar cadastrados)
            cnpj_contratante = nf.get('contratante_cnpj', '')
            cnpj_origem = nf.get('emitente_cnpj', '')
            cnpj_destino = nf.get('destinatario_cnpj', '')
            
            if cnpj_contratante and validar_cnpj(cnpj_contratante):
                cnpjs_validos_alertas.add(cnpj_contratante)
            if cnpj_origem and validar_cnpj(cnpj_origem):
                cnpjs_validos_alertas.add(cnpj_origem)
            if cnpj_destino and validar_cnpj(cnpj_destino):
                cnpjs_validos_alertas.add(cnpj_destino)
            
            # Se houver CTe associado, gerar linha CC
            if nf.get('cte_numero'):
                try:
                    linhas.append(self.gerar_linha_CC(nf, callback_progresso=callback_progresso))
                except ValueError as e:
                    # NOVO: Se houver erro ao gerar CC, avisa mas não bloqueia o processamento
                    # (pode ser que o CTe tenha dados inválidos, mas a NF ainda é válida)
                    nf_num = nf.get('nf_numero', 'N/A')
                    aviso_cc = (
                        f"AVISO: Linha CC não gerada para NF {nf_num}: {str(e)}\n"
                        f"A linha TN foi gerada com sucesso, mas a linha CC correspondente foi pulada.\n"
                        f"Verifique se os dados do CTe foram extraídos corretamente do PDF."
                    )
                    self._emitir_alerta(aviso_cc, callback_progresso, tipo="ALERTA", nf_num=nf_num)
        
        # Aviso sobre CNPJs válidos mas que podem não estar cadastrados no SIPROQUIM
        if cnpjs_validos_alertas:
            aviso = (
                f"ATENÇÃO: Os CNPJs foram validados e estão corretos segundo o algoritmo oficial, "
                f"mas podem não estar cadastrados no sistema SIPROQUIM.\n"
                f"Se ocorrer erro 'ConstraintViolationException' ao processar o arquivo, "
                f"verifique se todos os CNPJs estão cadastrados no sistema.\n"
                f"Total de CNPJs distintos: {len(cnpjs_validos_alertas)}.\n"
                f"Caso o problema persista, entre em contato com o suporte: lucasmac.dev@gmail.com"
            )
            self._emitir_alerta(aviso, callback_progresso, tipo="ALERTA", nf_num=None)
        
        # Escrever arquivo
        # CRÍTICO: Garantir que nenhuma linha contenha quebras de linha internas
        # MAS preservar os espaços de preenchimento (ljust) que são necessários para o layout
        import re
        linhas_finais = []
        for linha in linhas:
            # CRÍTICO: Para linhas TN, CC e EM, NÃO fazer strip() pois isso remove espaços de preenchimento
            # Apenas remove quebras de linha que possam ter vindo
            if linha.startswith(TN_TIPO) or linha.startswith(CC_TIPO) or linha.startswith(EM_TIPO):
                # Remove apenas quebras de linha, mas preserva espaços de preenchimento
                linha_limpa = str(linha).replace('\n', '').replace('\r', '')
                # Remove apenas caracteres não imprimíveis (exceto espaço)
                linha_limpa = ''.join(c for c in linha_limpa if c.isprintable() or c == ' ')
            else:
                # Para outras linhas, pode fazer limpeza normal
                linha_limpa = str(linha).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                linha_limpa = re.sub(r'\s+', ' ', linha_limpa).strip()
            linhas_finais.append(linha_limpa)
        
        # Escreve o arquivo garantindo que cada linha seja uma linha física separada
        # mas sem quebras de linha DENTRO de cada linha
        # Encoding UTF-8 conforme Manual Técnico SIPROQUIM (seção 2.2)
        with open(caminho_saida, 'w', encoding='utf-8', newline='') as f:
            for i, linha in enumerate(linhas_finais):
                # Garantia final: remove apenas quebras de linha, preserva espaços
                linha_final = linha.replace('\n', '').replace('\r', '')
                # Adiciona quebra de linha em todas as linhas, incluindo a última
                f.write(linha_final)
                f.write('\n')  # Quebra de linha explícita para cada linha
        
        if callback_progresso:
            callback_progresso('finalizar', {'caminho_gerado': caminho_saida})
        
        return caminho_saida
