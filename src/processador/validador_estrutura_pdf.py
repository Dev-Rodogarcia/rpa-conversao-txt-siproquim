"""
Validador de estrutura de PDF da Polícia Federal.
Detecta mudanças de layout verificando presença de labels obrigatórios.
"""

import re
from typing import Dict, List
from .validacao_constants import LABELS_OBRIGATORIOS_PDF, MensagensErro


class ValidadorEstruturaPDF:
    """
    Classe responsável por validar a estrutura do PDF antes da extração.
    Detecta se o PDF mudou de layout verificando labels obrigatórios.
    
    Esta é a primeira linha de defesa contra mudanças no formato do PDF da PF.
    """
    
    def __init__(self):
        """Inicializa o validador de estrutura."""
        self.labels_encontrados: Dict[str, bool] = {}
        self.labels_faltando: List[str] = []
    
    def validar_estrutura(self, texto_pagina: str) -> bool:
        """
        Verifica se o PDF contém os labels esperados.
        
        Args:
            texto_pagina: Texto completo de uma página do PDF
        
        Returns:
            True se a estrutura é válida, False caso contrário
        
        Raises:
            ValueError: Se labels obrigatórios estão faltando (PDF mudou de layout)
        """
        self.labels_encontrados = {}
        self.labels_faltando = []
        
        # Verifica cada label obrigatório
        for nome_label, pattern in LABELS_OBRIGATORIOS_PDF.items():
            encontrado = bool(re.search(pattern, texto_pagina, re.IGNORECASE))
            self.labels_encontrados[nome_label] = encontrado
            
            if not encontrado:
                self.labels_faltando.append(nome_label)
        
        # Se algum label está faltando, levanta erro
        if self.labels_faltando:
            raise ValueError(
                MensagensErro.PDF_LAYOUT_MUDOU.format(
                    labels_faltando=', '.join(self.labels_faltando)
                )
            )
        
        return True
    
    def validar_estrutura_silencioso(self, texto_pagina: str) -> Dict[str, bool]:
        """
        Verifica estrutura sem lançar exceção.
        
        Args:
            texto_pagina: Texto completo de uma página do PDF
        
        Returns:
            Dicionário com resultado da validação de cada label
        """
        self.labels_encontrados = {}
        
        for nome_label, pattern in LABELS_OBRIGATORIOS_PDF.items():
            encontrado = bool(re.search(pattern, texto_pagina, re.IGNORECASE))
            self.labels_encontrados[nome_label] = encontrado
        
        return self.labels_encontrados
    
    def obter_relatorio(self) -> str:
        """
        Gera relatório detalhado sobre a validação de estrutura.
        
        Returns:
            String formatada com relatório
        """
        if not self.labels_encontrados:
            return "Nenhuma validação realizada ainda."
        
        linhas = ["=== Validacao de Estrutura do PDF ==="]
        
        for nome_label, encontrado in self.labels_encontrados.items():
            status = "[OK] ENCONTRADO" if encontrado else "[X] FALTANDO"
            linhas.append(f"  {nome_label:15s}: {status}")
        
        if self.labels_faltando:
            linhas.append("\n[ALERTA] Labels faltando no PDF:")
            for label in self.labels_faltando:
                linhas.append(f"  - {label}")
            linhas.append("\nPossivel mudanca de layout pela Policia Federal.")
        else:
            linhas.append("\n[OK] Todos os labels obrigatorios foram encontrados.")
        
        return "\n".join(linhas)
