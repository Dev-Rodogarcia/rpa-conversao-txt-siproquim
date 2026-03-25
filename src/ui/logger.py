"""Estado e historico exibidos pelo painel operacional do RPA."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass(slots=True)
class ContextoLinhaPainel:
    """Representa a origem operacional de uma linha exibida na tabela."""

    id_linha: str
    cliente: str
    identificador: str
    numero_pagina: int = 0
    numero_linha: int = 0
    texto_linha: str = ""


@dataclass(slots=True)
class RegistroLogPainel:
    id_linha: str
    cliente: str
    status: str
    mensagem: str
    horario: str
    identificador: str
    numero_pagina: int
    numero_linha: int
    pode_reprocessar: bool

    def para_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ResumoExecucaoPainel:
    total_registros: int = 0
    processados: int = 0
    sucessos: int = 0
    falhas: int = 0

    def para_dict(self) -> Dict[str, int]:
        return asdict(self)


class CentralLogsPainel:
    """Centraliza estatisticas e registros exibidos pelo painel."""

    def __init__(self) -> None:
        self.reiniciar()

    def reiniciar(self) -> None:
        self.estatisticas = ResumoExecucaoPainel()
        self.contexto_em_processamento: Optional[ContextoLinhaPainel] = None

    def definir_total_registros(self, total_registros: int) -> None:
        self.estatisticas.total_registros = max(0, int(total_registros))

    def substituir_estatisticas(
        self,
        *,
        total_registros: Optional[int] = None,
        processados: Optional[int] = None,
        sucessos: Optional[int] = None,
        falhas: Optional[int] = None,
    ) -> None:
        if total_registros is not None:
            self.estatisticas.total_registros = max(0, int(total_registros))
        if processados is not None:
            self.estatisticas.processados = max(0, int(processados))
        if sucessos is not None:
            self.estatisticas.sucessos = max(0, int(sucessos))
        if falhas is not None:
            self.estatisticas.falhas = max(0, int(falhas))

    def registrar_processando(
        self,
        contexto: ContextoLinhaPainel,
        mensagem: str = "Processando registro.",
    ) -> RegistroLogPainel:
        self.contexto_em_processamento = contexto
        return self._criar_registro(contexto, "Processando", mensagem, False)

    def registrar_sucesso(
        self,
        contexto: ContextoLinhaPainel,
        mensagem: str,
    ) -> RegistroLogPainel:
        self.contexto_em_processamento = None
        self.estatisticas.processados += 1
        self.estatisticas.sucessos += 1
        return self._criar_registro(contexto, "Sucesso", mensagem, False)

    def registrar_falha(
        self,
        contexto: ContextoLinhaPainel,
        mensagem: str,
    ) -> RegistroLogPainel:
        self.contexto_em_processamento = None
        self.estatisticas.processados += 1
        self.estatisticas.falhas += 1
        return self._criar_registro(contexto, "Erro", mensagem, True)

    def registrar_evento(
        self,
        contexto: ContextoLinhaPainel,
        status: str,
        mensagem: str,
        *,
        pode_reprocessar: bool = False,
    ) -> RegistroLogPainel:
        return self._criar_registro(contexto, status, mensagem, pode_reprocessar)

    def registrar_mensagem_sistema(
        self,
        status: str,
        mensagem: str,
    ) -> RegistroLogPainel:
        return RegistroLogPainel(
            id_linha="-",
            cliente="Sistema",
            status=status,
            mensagem=mensagem,
            horario=datetime.now().strftime("%H:%M:%S"),
            identificador="sistema",
            numero_pagina=0,
            numero_linha=0,
            pode_reprocessar=False,
        )

    def obter_progresso(self) -> Dict[str, int]:
        total = self.estatisticas.total_registros
        atual = self.estatisticas.processados
        if self.contexto_em_processamento is not None and total > atual:
            atual += 1

        percentual = 0
        if total > 0:
            percentual = min(100, int((atual / total) * 100))

        return {
            "atual": atual,
            "total": total,
            "percentual": percentual,
        }

    def _criar_registro(
        self,
        contexto: ContextoLinhaPainel,
        status: str,
        mensagem: str,
        pode_reprocessar: bool,
    ) -> RegistroLogPainel:
        return RegistroLogPainel(
            id_linha=contexto.id_linha,
            cliente=contexto.cliente,
            status=status,
            mensagem=mensagem,
            horario=datetime.now().strftime("%H:%M:%S"),
            identificador=contexto.identificador,
            numero_pagina=contexto.numero_pagina,
            numero_linha=contexto.numero_linha,
            pode_reprocessar=pode_reprocessar,
        )
