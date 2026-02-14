"""
Base de Conhecimento para Enriquecimento de Dados.

Esta classe centraliza o mapeamento de CNPJs para nomes de empresas,
permitindo que o sistema preencha automaticamente campos faltantes
quando o extrator de PDF falha em identificar o nome da empresa.
"""

import re
import unicodedata
from typing import Dict, Optional

from .aprendizado_store import AprendizadoStore


class BaseConhecimentoNomes:
    """
    Base de conhecimento para mapeamento CNPJ -> Nome da Empresa.
    
    Quando o extrator de PDF falha em identificar o nome de uma empresa,
    o sistema consulta esta base para preencher automaticamente o campo faltante.
    Isso evita que registros válidos sejam removidos por falta de nome.
    """
    
    # BASE DE CONHECIMENTO: Mapeamento CNPJ -> Nome Completo
    # Formato: {CNPJ_limpo_sem_mascara: 'Nome Completo da Empresa'}
    # 
    # IMPORTANTE: Os CNPJs devem estar SEM máscara (apenas números)
    # Exemplo: '08061365000308' e não '08.061.365/0003-08'
    #
    # Para adicionar novos clientes:
    # 1. Identifique o CNPJ que está falhando na extração
    # 2. Adicione uma nova entrada neste dicionário
    # 3. Use o nome exatamente como deve aparecer no TXT (sem acentos, maiúsculas)
    _MAPEAMENTO_CNPJ_NOMES: Dict[str, str] = {
        # --- CLIENTES RECORRENTES (Adições Manuais) ---
        '08061365000308': 'MODULAR DATA CENTERS INDUSTRIA COMERCIO E SERVICOS',
        '01157555001186': 'TENDA ATACADO SA',
        
        # --- EXTRAÍDO DE frete_produtos_controlados_12.2025_NHB.pdf ---
        '03746938001387': 'BR SUPPLY - SLO',
        '09093910018854': 'PROMIL PROMOTORA DE VENDAS LTDA',
        '09093910019311': 'PROMIL PROMOTORA DE VENDAS LTDA',
        '07249846012034': 'SOLDI PROMOTORA DE VENDAS LTDA',
        '03840986005831': 'SAINT-GOBAIN DISTRIBUICAO BRASIL LTDA',
        '03840986004002': 'SAINT-GOBAIN DISTRIBUICAO BRASIL LTDA',
        '75400218002690': 'CASSOL MATERIAIS DE CONSTRUCAO LTDA',
        '75400218001104': 'CASSOL MATERIAIS DE CONSTRUCAO LTDA',
        '45987005023996': 'COMERCIAL AUTOMOTIVA SA',
        '06980064012946': 'NACIONAL GAS BUTANO DISTRIBUIDORA L',
        '61412110011866': 'DROGARIA SAO PAULO S.A.',
        
        # --- EXTRAÍDO DE frete_produtos_controlados_12.2025_RJR.pdf ---
        '43996693000127': 'PPG SUM',
        '27376427000145': 'MAERSK SUPPLY AMERICA LATINA SERVICOS MARITIMOS LTDA',
        '09098215000161': 'MAERSK SUPPLY SERVICE APOIO MARITIMO LTDA',
        '40278681000179': 'TRANSOCEAN BRASIL LTDA',
        
        # --- EXTRAÍDO DE frete_produtos_controlados_12.2025_AGU.pdf ---
        '08406359000175': 'HIDRODOMI DO BRASIL',
        '52434156000184': 'REVAL ATACADO DE PAPELARIA LTDA',
        '15436940001762': 'AMAZON SERVICOS DE VAREJO DO BRASIL LTDA.',
        
        # --- EXTRAÍDO DE frete_produtos_controlados_12.2025_CAS.pdf ---
        '51602373000173': 'GEROMA',
        '61347167000118': 'GLAMIR IMP. DE PRODUTOS QUIMICOS LTDA-EPP',
        
        # --- EXTRAÍDO DE frete_produtos_controlados_12.2025_CPQ.pdf ---
        '01844555002800': 'CNH INDUSTRIAL BRASIL LTDA',
        '52771540000172': 'GRIMALDI IND DE EQUIP PARA TRANSP LTDA',
        '68210657000117': 'DINAMICA QUIMICA CONTEMPORANEA LTDA',
        '82421694000103': 'LABIQUIMICA COM DE PROD P LABORATORIOS LTDA',
        '21454868000131': 'NEON COMERCIO DE TINTAS LTDA',
        '45296126000193': 'COM DE TINTAS TRES DE MAIO LTDA',
        '01528473000129': 'KROHNE CONAUT INSTRUMENTACAO LTDA',
        '02990605001760': 'MARELLI SISTEMAS AUTOMOTIVOS INDUSTRIA E COMERCIO',
        '00253137002100': 'DANA INDUSTRIAS LTDA',
        '10378376000350': 'VS DE LIMA E CIA LTDA',
        '55999932000181': 'MURCIA PINTURAS TECNICAS LTDA',
        '43996693003061': 'PPG AMB',
        '40382646000103': 'TECHCOATING COMERCIO E SERVICOS LTDA',
        '05396883000386': 'EUCATEX DISTRIBUICAO SALTO',
        '66825498000130': 'LOUREIRO & FUMES LTDA',
        '14929498000186': 'VITORIO FERNANDO BARTOLI ME',
        '20773544000101': 'FRANCOLOSO & CASSOLA MATERIAIS PARA CONSTRUCAO LTDA',
        '02792081000135': 'PEDRINHO COMERCIO E SERVICOS PARA CONSTRUCOES EIRELI',
        '01753491000104': 'PEDERTRACTOR INDUSTRIA E COMERCIO DE PECAS TRATORE',
        '73056731000122': 'TECNAUT INDUSTRIA E COMERCIO DE METAIS LTDA',
        '10399413000144': 'EXODO CIENTIFICA',
        '12538002000118': 'ERMEX',
        '08874311000191': 'QUEST LABOR SOLUCOES PARA LABORATORIOS LTDA',
        '01961898000127': 'CARGILL ALIMENTOS LTDA',
        '20694873001554': 'VEICULOS CRUZEIRO COMERCIO LTDA',
        '06060908000177': 'BIADOLA COMERCIO DE TINTAS EM GERAL REPRESENT COML DE',
        '50637255000138': 'KALU IMPORT LTDA EPP',
        '01333183000120': 'TMA INDUSTRIA E COMERCIO LIMITADA',
        '14621778000122': 'DISTRIB HAMBURGO DE ABRASIVOS FERRAM E MAQ LTDA EP',
        '94219771000118': 'MECANICA ROSSA LTDA EPP',
        '85044683000131': 'VERTICAL COMERCIO',
        '04785438000183': 'CONVICTA INDUSTRIA E COMERCIO LTDA',
        '09045868000182': 'FABIAN E SILVESTRE LTDA',
        '05041668000109': 'MABRAFER TINTAS LTDA EPP',
        '61169235000104': 'OPCAO CAR PINTURA AUTOMOTIVA LTDA',
        '09026535000297': 'PALMA PARAFUSOS E FERRAMENTAS LTDA',
        '50222252000133': 'RECIFENSE REPARACAO AUTOMOTIVA LTDA',
        '03722089000198': 'UNIFER UNIVERSO DAS TINTAS LTDA',
        '04844206000159': 'FLASH INDUSTRIA E COMERCIO DE PRODUTOS E SISTEMAS',
        '36606953000145': 'FORT MAQ SOLUCOES INDUSTRIAIS LTDA',
        '44367514000317': 'DEPOSITO DE TINTAS AVARE LTDA',
        '44367514000155': 'DEPOSITO DE TINTAS AVARE LTDA',
        '44367514000236': 'DEPOSITO DE TINTAS AVARE LTDA',
        '89086144000540': 'RANDON SA IMPLEMENTOS E PARTICIPACOES',
        '62543665000107': 'PIATEX IND E COM DE FIBERGLASS LTDA',
        '59320820001509': 'GREIF EMBALAGENS INDUSTRIAIS DO BRASIL LTDA.',
        '17343071000190': 'METALSA CAMPO LARGO IND E COM DE CHASSIS LTDA',
        '33808332000156': 'RGLAB',
        '29557777000133': 'DB-DIAGNOSTICOS E ANALISES CLINICAS LTDA.',
        '49673346000220': 'TJ DISTRIB.DE ABRASIVOS E SOLDAS LTDA',
        '37089632000183': 'CHROME COMERCIO DE TINTAS E MATERIA DE PINTURA LTDA',
        '31288769000180': 'ROMILDA MARIA DOS SANTOS 06415234676',
        '14562779000143': 'LUMAX IND COM IMP EXP LTDA',
        '04394837000113': 'HRM CALDEIRARIA INDUSTRIAL EIRELI',
        '52944664000102': 'THYSSENKRUPP SPRINGS E STABILIZERS BRASIL LTDA',
        '61142063000339': 'RASSINI NHK AUTOPECAS LTDA',
        '52610274000104': 'NOVA PINTURA LTDA',
        '46356226000120': 'VULKAN DO BRASIL LTDA',
        '03920438000186': 'MIRASSOL COMERCIAL INDUSTRIAL IMPORTADORA E EXPORT',
        '60431889000193': 'ETHOS METALURGICA LTDA',
        '60119161000120': 'EDSON KOITI ISHII TINTAS',
        '31015773000175': 'MAQUINARIA ILHA REPARACAO AUTOMOTIVA LTDA',
        '03320963000160': 'LIZENIO CALHIERO',
        '40281895000102': 'SMP',
        '82075748000118': 'REAGEN PRODUTOS PARA LABORATORIOS LTDA',
        '19493288000101': 'ENOVA IMPLEMENTOS RODOVIARIOS LTDA',
        '39739741000124': 'LLC COMERCIO DE TINTAS AUTOMOTIVAS LTDA',
        '39838697000100': 'ADB COMERCIO E TRANSPORTES',
        '54727755000111': 'LABORATORIO DE ANAT.PATOLOGICA E CITOPATOLOGIA DE BAURU',
        '13261123000128': 'C4 CIENTIFICA',
        '15090456000167': 'JOST AGRICULTURE E CONSTRUCTION SOUTH AMERICA LTDA',
        
        # --- EXTRAÍDO DE frete_produtos_controlados_12.2025_CWB.pdf ---
        '84684471001802': 'BUSCHLE & LEPPER S.A.',
        '76518836002007': 'ARAUCO-JAGUARIAÍVA',
        '11054013000160': 'NAVE LAB COMERCIO DE PRODUTOS LABORATORIOS LTDA',
        '43829282000490': 'HB FULLER GRU',
        '53538416000124': 'TOTAL LIMP',
        '13655148000106': 'SHOPPING CIDADE - SOROCABA',
        '11214419000162': 'TANART',
        '04308344000113': 'ORG CAETANENSE DE EMP DE LUTO EIRELI',
        '43996693000208': 'PPG GVT',
        '32384763000170': 'COMERCIAL DE TINTAS DOIS IRMAOS LTDA',
        '77143402000170': 'HERBERT MATS P CONSTRUCAO LTDA',
        '44114040000130': 'CARBON CIENTIFICA',
        '32900127000153': 'LION MINING MINERADORA LTDA',
        '03447805000176': 'DIELAB COMERCIO DE PRODUTOS PARA LABORATORIOS LTDA ME',
        '04993269000177': 'DIPA QUIMICA',
        '43422189000113': 'RDBM COMERCIO',
        '00348003011660': 'CENTRO NAC DE PESQ TECNOL EM INFORM PARA A AGRICULTURA',
        '05350401000195': 'SANEX SOLUCOES LTDA',
        '78594025000158': 'FUNDACAO ABC PARA ASSISTENCIA E DIV TEC AGROPECUARIA',
        '13767262000128': 'ACS CIENTIFICA QUIMICA FINA',
        '10762800000101': 'HYGIECORP',
        '04692027001387': 'LUXOTTICA BRASIL PRODUTOS OTICOS E ESPORTIVOS LTDA',
        '48731450000180': 'DAIANE BURIN DOS SANTOS',
        
        # NOTA: O CPF 41303082896 (LEONARDO YURI DE ALMEIDA ALVES) foi intencionalmente
        # excluído desta base, pois é um CPF que será bloqueado pela REGRA DE BLOQUEIO #1
        # (CPF em campo de CNPJ não passa na validação matemática).
    }

    _store_aprendizado: Optional[AprendizadoStore] = None

    @classmethod
    def _obter_store_aprendizado(cls) -> Optional[AprendizadoStore]:
        """Obtém store de aprendizado sem interromper o fluxo em caso de falha."""
        if cls._store_aprendizado is None:
            try:
                cls._store_aprendizado = AprendizadoStore.get_instance()
            except Exception:
                cls._store_aprendizado = None
        return cls._store_aprendizado
    
    @classmethod
    def buscar_nome_por_cnpj(cls, cnpj: str) -> Optional[str]:
        """
        Busca o nome da empresa na base de conhecimento usando o CNPJ.
        
        Args:
            cnpj: CNPJ da empresa (com ou sem máscara, será limpo automaticamente)
            
        Returns:
            Nome da empresa se encontrado, None caso contrário
        """
        # Remove caracteres não numéricos para normalizar
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        # Busca na base de conhecimento
        nome = cls._MAPEAMENTO_CNPJ_NOMES.get(cnpj_limpo)
        if nome:
            return nome

        store = cls._obter_store_aprendizado()
        if store:
            nome_aprendido = store.buscar_nome_por_documento(cnpj_limpo)
            if nome_aprendido:
                return nome_aprendido

        return None

    @staticmethod
    def _normalizar_nome(nome: str) -> str:
        """Normaliza nome para comparacoes robustas (sem acento/pontuacao)."""
        if not nome:
            return ""
        texto = unicodedata.normalize('NFD', str(nome).upper())
        texto = ''.join(ch for ch in texto if unicodedata.category(ch) != 'Mn')
        texto = re.sub(r'[^A-Z0-9]+', ' ', texto)
        return re.sub(r'\s+', ' ', texto).strip()

    @classmethod
    def buscar_cnpj_por_nome(cls, nome: str, campo: Optional[str] = None) -> Optional[str]:
        """
        Busca CNPJ a partir do nome (exato ou prefixo unico).

        Retorna apenas quando encontra correspondencia unica para evitar
        preenchimento incorreto.
        """
        chave = cls._normalizar_nome(nome)
        if not chave or len(chave) < 8:
            return None

        # Match exato tem prioridade.
        candidatos_exatos = [
            cnpj for cnpj, nome_base in cls._MAPEAMENTO_CNPJ_NOMES.items()
            if cls._normalizar_nome(nome_base) == chave
        ]
        if len(candidatos_exatos) == 1:
            return candidatos_exatos[0]
        if len(candidatos_exatos) > 1:
            return None

        # Match por prefixo/contem, exigindo trecho significativo.
        candidatos_aprox = []
        for cnpj, nome_base in cls._MAPEAMENTO_CNPJ_NOMES.items():
            base = cls._normalizar_nome(nome_base)
            if not base:
                continue
            menor, maior = (chave, base) if len(chave) <= len(base) else (base, chave)
            if len(menor) >= 12 and (maior.startswith(menor) or menor in maior):
                candidatos_aprox.append(cnpj)

        if len(candidatos_aprox) == 1:
            return candidatos_aprox[0]

        store = cls._obter_store_aprendizado()
        if store:
            doc_aprendido = store.buscar_documento_por_nome(nome, campo=campo)
            if doc_aprendido:
                return doc_aprendido

        return None
    
    @classmethod
    def existe_cnpj(cls, cnpj: str) -> bool:
        """
        Verifica se um CNPJ existe na base de conhecimento.
        
        Args:
            cnpj: CNPJ da empresa (com ou sem máscara)
            
        Returns:
            True se o CNPJ está na base, False caso contrário
        """
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        if cnpj_limpo in cls._MAPEAMENTO_CNPJ_NOMES:
            return True

        store = cls._obter_store_aprendizado()
        if store:
            return store.existe_documento(cnpj_limpo)
        return False
    
    @classmethod
    def obter_todos_mapeamentos(cls) -> Dict[str, str]:
        """
        Retorna uma cópia de todos os mapeamentos CNPJ -> Nome.
        
        Returns:
            Dicionário com todos os mapeamentos (cópia para evitar modificações acidentais)
        """
        return cls._MAPEAMENTO_CNPJ_NOMES.copy()
    
    @classmethod
    def total_registros(cls) -> int:
        """
        Retorna o total de registros na base de conhecimento.
        
        Returns:
            Número total de CNPJs cadastrados
        """
        total_base = len(cls._MAPEAMENTO_CNPJ_NOMES)
        store = cls._obter_store_aprendizado()
        if not store:
            return total_base
        try:
            resumo = store.resumo_memoria()
            total_docs_memoria = int(resumo.get("total_documentos", 0))
            return total_base + total_docs_memoria
        except Exception:
            return total_base
    
    @classmethod
    def adicionar_mapeamento(cls, cnpj: str, nome: str) -> None:
        """
        Adiciona um novo mapeamento à base de conhecimento.
        
        ATENÇÃO: Esta função modifica a base de conhecimento permanentemente.
        Use apenas para adicionar novos registros durante a execução do programa.
        Para adicionar registros permanentes, edite diretamente o dicionário _MAPEAMENTO_CNPJ_NOMES.
        
        Args:
            cnpj: CNPJ da empresa (será limpo automaticamente)
            nome: Nome completo da empresa
        """
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        cls._MAPEAMENTO_CNPJ_NOMES[cnpj_limpo] = nome.upper().strip()
