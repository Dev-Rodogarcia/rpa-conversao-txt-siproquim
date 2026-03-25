"""Worker Qt que adapta o pipeline SIPROQUIM ao painel operacional do RPA."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal
from unidecode import unidecode

from main import ProcessamentoInterrompido, processar_pdf
from src.gerador.layout_constants import mes_numero_para_alfanumerico
from src.ui.logger import CentralLogsPainel, ContextoLinhaPainel


def _downloads_dir() -> Path:
    home = Path.home()
    downloads = home / "Downloads"
    return downloads if downloads.exists() else home


def _gerar_nome_arquivo_saida(
    ano: int,
    mes_abreviado: str,
    cnpj: str,
    nome_pdf: str,
) -> str:
    nome_base = f"M{ano}{mes_abreviado.upper()}{cnpj}"
    nome_sem_ext = Path(nome_pdf).stem
    nome_sanitizado = unidecode(nome_sem_ext).upper()
    nome_sanitizado = re.sub(r"[^A-Z0-9]", "_", nome_sanitizado)
    nome_sanitizado = re.sub(r"_+", "_", nome_sanitizado).strip("_")
    if len(nome_sanitizado) > 30:
        nome_sanitizado = nome_sanitizado[:30]
    return f"{nome_base}_{nome_sanitizado}.txt"


class TrabalhadorExecucaoRpa(QThread):
    painel_limpo = Signal()
    status_alterado = Signal(str)
    estatisticas_atualizadas = Signal(dict)
    progresso_atualizado = Signal(dict)
    registro_log_adicionado = Signal(dict)
    erro_fatal = Signal(str)
    execucao_encerrada = Signal(dict)

    def __init__(
        self,
        valor_reajuste: float,
        contexto_execucao: dict,
        modo_execucao: str = "completa",
        contexto_reprocessamento: Optional[dict] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.valor_reajuste = valor_reajuste
        self.contexto_execucao = dict(contexto_execucao)
        self.modo_execucao = modo_execucao
        self.contexto_reprocessamento = contexto_reprocessamento or {}
        self.central_logs = CentralLogsPainel()
        self.parada_solicitada = False

    def solicitar_parada(self) -> None:
        self.parada_solicitada = True
        self._emitir_registro(
            self.central_logs.registrar_mensagem_sistema(
                "Executando",
                "Solicitacao de parada recebida. Encerrando no proximo checkpoint seguro.",
            )
        )

    def run(self) -> None:
        if self.modo_execucao == "completa":
            self.central_logs.reiniciar()
            self.painel_limpo.emit()

        self.status_alterado.emit("Executando")
        self._emitir_registro(
            self.central_logs.registrar_mensagem_sistema(
                "Executando",
                (
                    "Execucao iniciada com valor de reajuste "
                    f"{self.valor_reajuste:.2f}. Adapter temporario usando o pipeline SIPROQUIM."
                ),
            )
        )
        if self.modo_execucao == "reprocessamento":
            nf_foco = self.contexto_reprocessamento.get("id_linha", "-")
            self._emitir_registro(
                self.central_logs.registrar_mensagem_sistema(
                    "Executando",
                    (
                        f"Reprocessamento solicitado para a linha {nf_foco}. "
                        "O adapter temporario executa uma nova rodada completa do lote."
                    ),
                )
            )
        self._emitir_estado_painel()
        self._emitir_progresso(
            {
                "atual": 0,
                "total": 0,
                "percentual": 0,
                "descricao": "Aguardando abertura do arquivo de origem.",
            }
        )

        caminho_saida = self._resolver_caminho_saida()

        try:
            caminho_gerado = processar_pdf(
                self.contexto_execucao["pdf"],
                self.contexto_execucao["cnpj"],
                str(caminho_saida),
                callback_progresso=self._processar_callback_backend,
                mes=int(self.contexto_execucao["mes"]),
                ano=int(self.contexto_execucao["ano"]),
                callback_cancelamento=self.deve_interromper,
            )
            self.status_alterado.emit("Sucesso")
            self._emitir_registro(
                self.central_logs.registrar_mensagem_sistema(
                    "Sucesso",
                    f"Arquivo gerado com sucesso em {caminho_gerado}.",
                )
            )
            self._emitir_progresso(
                {
                    "atual": self.central_logs.estatisticas.total_registros,
                    "total": self.central_logs.estatisticas.total_registros,
                    "percentual": 100,
                    "descricao": "Arquivo TXT validado e pronto para envio.",
                }
            )
            self.execucao_encerrada.emit(
                {
                    "status": "Sucesso",
                    "caminho_gerado": str(caminho_gerado),
                    "estatisticas": self.central_logs.estatisticas.para_dict(),
                }
            )
        except ProcessamentoInterrompido as erro:
            if caminho_saida.exists():
                caminho_saida.unlink(missing_ok=True)
            self.status_alterado.emit("Parado")
            self._emitir_registro(
                self.central_logs.registrar_mensagem_sistema("Parado", str(erro))
            )
            self.execucao_encerrada.emit(
                {
                    "status": "Parado",
                    "estatisticas": self.central_logs.estatisticas.para_dict(),
                }
            )
        except Exception as erro:  # pragma: no cover - erro exibido para o usuario
            self.status_alterado.emit("Erro")
            self._emitir_registro(
                self.central_logs.registrar_mensagem_sistema("Erro", str(erro))
            )
            self.erro_fatal.emit(str(erro))
            self.execucao_encerrada.emit(
                {
                    "status": "Erro",
                    "estatisticas": self.central_logs.estatisticas.para_dict(),
                }
            )

    def deve_interromper(self) -> bool:
        return self.parada_solicitada

    def _resolver_caminho_saida(self) -> Path:
        mes_abreviado = mes_numero_para_alfanumerico(int(self.contexto_execucao["mes"]))
        nome = _gerar_nome_arquivo_saida(
            int(self.contexto_execucao["ano"]),
            mes_abreviado,
            str(self.contexto_execucao["cnpj"]),
            Path(self.contexto_execucao["pdf"]).name,
        )
        return _downloads_dir() / nome

    def _processar_callback_backend(self, etapa: str, detalhes: dict) -> None:
        if etapa == "abrir":
            arquivo = str(detalhes.get("arquivo", "")).strip()
            self._emitir_registro(
                self.central_logs.registrar_mensagem_sistema(
                    "Executando",
                    f"Abrindo arquivo de origem {arquivo}.",
                )
            )
            self._emitir_progresso(
                {
                    "atual": 0,
                    "total": 0,
                    "percentual": 5,
                    "descricao": "Abrindo arquivo de origem.",
                }
            )
            return

        if etapa == "extrair":
            pagina_atual = int(detalhes.get("pagina_atual", 0) or 0)
            total_paginas = int(detalhes.get("total_paginas", 0) or 0)
            percentual = 5
            if total_paginas > 0:
                percentual = 5 + int((pagina_atual / total_paginas) * 40)
            self._emitir_progresso(
                {
                    "atual": pagina_atual,
                    "total": total_paginas,
                    "percentual": min(percentual, 45),
                    "descricao": f"Leitura do PDF: pagina {pagina_atual}/{total_paginas}",
                }
            )
            return

        if etapa == "deduplicar":
            total_registros = int(detalhes.get("total_registros", 0) or 0)
            total_nfs = int(detalhes.get("total_nfs", 0) or 0)
            self.central_logs.substituir_estatisticas(
                total_registros=total_nfs,
                processados=0,
                sucessos=0,
                falhas=0,
            )
            self._emitir_estado_painel()
            self._emitir_registro(
                self.central_logs.registrar_mensagem_sistema(
                    "Processando",
                    (
                        f"Deduplicacao concluida: {total_registros} registro(s) extraido(s) "
                        f"e {total_nfs} registro(s) unico(s)."
                    ),
                )
            )
            self._emitir_progresso(
                {
                    "atual": 0,
                    "total": total_nfs,
                    "percentual": 55,
                    "descricao": f"{total_nfs} registro(s) prontos para validacao.",
                }
            )
            return

        if etapa == "processar":
            if "total_registros" in detalhes:
                total = int(detalhes.get("total_registros", 0) or 0)
                self._emitir_registro(
                    self.central_logs.registrar_mensagem_sistema(
                        "Processando",
                        f"Validando {total} registro(s) com a camada robusta.",
                    )
                )
                self._emitir_progresso(
                    {
                        "atual": 0,
                        "total": total,
                        "percentual": 70,
                        "descricao": f"Validando {total} registro(s) extraido(s).",
                    }
                )
                return

            total_aprovados = int(detalhes.get("total_aprovados", 0) or 0)
            total_criticos = int(detalhes.get("total_com_erros_criticos", 0) or 0)
            total_ajustes = int(detalhes.get("total_ajustes_manuais", 0) or 0)
            sucessos = max(total_aprovados - total_criticos, 0)
            falhas = max(total_criticos, 0)
            self.central_logs.substituir_estatisticas(
                total_registros=total_aprovados,
                processados=total_aprovados,
                sucessos=sucessos,
                falhas=falhas,
            )
            self._emitir_estado_painel()
            self._emitir_registro(
                self.central_logs.registrar_mensagem_sistema(
                    "Processando",
                    (
                        f"Validacao concluida: {sucessos} sucesso(s), {falhas} falha(s) "
                        f"e {total_ajustes} ajuste(s) manual(is)."
                    ),
                )
            )
            self._emitir_progresso(
                {
                    "atual": total_aprovados,
                    "total": total_aprovados,
                    "percentual": 80,
                    "descricao": "Validacao concluida. Preparando geracao do arquivo final.",
                }
            )
            return

        if etapa == "gerar":
            total_nfs = int(detalhes.get("total_nfs", 0) or 0)
            self._emitir_registro(
                self.central_logs.registrar_mensagem_sistema(
                    "Processando",
                    f"Gerando arquivo TXT com {total_nfs} registro(s).",
                )
            )
            self._emitir_progresso(
                {
                    "atual": total_nfs,
                    "total": total_nfs,
                    "percentual": 92,
                    "descricao": f"Gerando arquivo TXT com {total_nfs} registro(s).",
                }
            )
            return

        if etapa == "ajuste_manual":
            self._registrar_ajuste_manual(detalhes)
            return

        if etapa == "processar_log":
            self._registrar_log_backend(detalhes)
            return

        if etapa == "finalizar":
            caminho_gerado = str(detalhes.get("caminho_gerado", "")).strip()
            self._emitir_progresso(
                {
                    "atual": self.central_logs.estatisticas.total_registros,
                    "total": self.central_logs.estatisticas.total_registros,
                    "percentual": 100,
                    "descricao": "Arquivo TXT validado e pronto para envio.",
                }
            )
            if caminho_gerado:
                self._emitir_registro(
                    self.central_logs.registrar_mensagem_sistema(
                        "Sucesso",
                        f"Validacao local concluida. Saida em {caminho_gerado}.",
                    )
                )

    def _registrar_ajuste_manual(self, detalhes: dict) -> None:
        mensagem = str(detalhes.get("mensagem", "")).strip()
        nf = self._normalizar_nf(detalhes.get("nf"))
        tipo = str(detalhes.get("tipo", "")).strip().upper()
        contexto = self._criar_contexto_nf(nf, tipo or "ajuste")
        registro = self.central_logs.registrar_evento(
            contexto,
            "Erro",
            mensagem or "Pendencia manual identificada durante o processamento.",
            pode_reprocessar=bool(nf),
        )
        self._emitir_registro(registro)

    def _registrar_log_backend(self, detalhes: dict) -> None:
        mensagem = str(detalhes.get("mensagem", "")).strip()
        tipo = str(detalhes.get("tipo", "INFO")).strip().upper()
        if not mensagem:
            return

        nf = self._extrair_nf_mensagem(mensagem)
        status = self._mapear_status_log(tipo, nf is not None)
        pode_reprocessar = bool(
            nf and tipo in {"ERRO", "CRITICO", "ALERTA", "ACAO_NECESSARIA"}
        )

        if nf:
            contexto = self._criar_contexto_nf(nf, tipo)
            registro = self.central_logs.registrar_evento(
                contexto,
                status,
                mensagem,
                pode_reprocessar=pode_reprocessar,
            )
        else:
            registro = self.central_logs.registrar_mensagem_sistema(status, mensagem)

        self._emitir_registro(registro)

    def _emitir_registro(self, registro) -> None:
        self.registro_log_adicionado.emit(registro.para_dict())

    def _emitir_estado_painel(self) -> None:
        self.estatisticas_atualizadas.emit(self.central_logs.estatisticas.para_dict())

    def _emitir_progresso(self, dados: dict) -> None:
        self.progresso_atualizado.emit(dados)

    def _criar_contexto_nf(self, nf: Optional[str], origem: str) -> ContextoLinhaPainel:
        nf_normalizada = self._normalizar_nf(nf)
        return ContextoLinhaPainel(
            id_linha=nf_normalizada or "-",
            cliente=f"NF {nf_normalizada}" if nf_normalizada else "Sistema",
            identificador=f"{origem.lower()}:{nf_normalizada or 'sistema'}",
            numero_pagina=0,
            numero_linha=0,
            texto_linha=nf_normalizada or "",
        )

    @staticmethod
    def _mapear_status_log(tipo: str, tem_nf: bool) -> str:
        if tipo in {"ERRO", "CRITICO", "ALERTA", "ACAO_NECESSARIA"}:
            return "Erro"
        if tipo in {"SUCESSO", "CHECK"}:
            return "Sucesso"
        if tem_nf and tipo in {"ATENCAO", "AVISO"}:
            return "Erro"
        return "Processando"

    @staticmethod
    def _extrair_nf_mensagem(mensagem: str) -> Optional[str]:
        correspondencia = re.search(r"\bNF\s+([A-Z0-9.-]+)\b", mensagem, re.IGNORECASE)
        if not correspondencia:
            return None
        return correspondencia.group(1).strip().upper()

    @staticmethod
    def _normalizar_nf(valor: object) -> Optional[str]:
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None
