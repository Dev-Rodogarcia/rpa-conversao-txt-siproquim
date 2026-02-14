"""
Memoria de aprendizado persistente (SQLite) para correcoes confirmadas.

Caracteristicas:
- Arquivo unico e portavel (facil de copiar entre computadores).
- Salvo dentro do proprio projeto para ficar junto aos arquivos da IDE.
- API simples para:
  - aprender com TXT corrigido
  - buscar nome por documento
  - buscar documento por nome
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import threading
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..gerador.txt_parser import parse_txt_siproquim
from ..gerador.validators import validar_cnpj, validar_cpf


class AprendizadoStore:
    """Store SQLite com cache em memoria para consultas rapidas."""

    DB_FILENAME = "memoria_aprendizado.sqlite3"
    MEM_DIRNAME = "memoria"
    STATUS_ATIVO = "ativo"
    STATUS_QUARENTENA = "quarentena"
    CONFLITO_MARGEM = 2  # Diferenca minima para desempate automatico
    # Evita auto-preenchimento por "one-shot" com baixa evidencia.
    MIN_OCORRENCIAS_POR_CAMPO = {
        "emitente": 2,
        "contratante": 2,
        "destinatario": 2,
    }
    MIN_RAZAO_LIDER_POR_CAMPO = {
        "emitente": 0.65,
        "contratante": 0.65,
        "destinatario": 0.70,
    }

    _instance: Optional["AprendizadoStore"] = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "AprendizadoStore":
        """Retorna singleton compartilhado pelo app."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        self._lock = threading.Lock()
        self._db_path = Path(db_path) if db_path else self._resolver_caminho_db()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._nome_para_docs: Dict[str, Dict[str, Dict[str, object]]] = {}
        self._doc_para_nomes: Dict[str, Dict[str, Dict[str, object]]] = {}
        self._nome_para_docs_por_campo: Dict[str, Dict[str, Dict[str, Dict[str, object]]]] = {}
        self._doc_para_nomes_por_campo: Dict[str, Dict[str, Dict[str, Dict[str, object]]]] = {}
        self._totais_status: Dict[str, int] = {
            self.STATUS_ATIVO: 0,
            self.STATUS_QUARENTENA: 0,
        }

        self._inicializar_schema()
        self._recarregar_cache()

    @property
    def db_path(self) -> Path:
        return self._db_path

    @property
    def memory_folder(self) -> Path:
        return self._db_path.parent

    def resumo_memoria(self) -> Dict[str, object]:
        """Retorna resumo util para logs/UI."""
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_pares,
                    COUNT(DISTINCT nome_key) AS total_nomes,
                    COUNT(DISTINCT documento) AS total_documentos,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS pares_ativos,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) AS pares_quarentena
                FROM learned_pairs
                """,
                (self.STATUS_ATIVO, self.STATUS_QUARENTENA),
            )
            row = cur.fetchone()
            total_pares = int(row[0] or 0)
            total_nomes = int(row[1] or 0)
            total_docs = int(row[2] or 0)
            pares_ativos = int(row[3] or 0)
            pares_quarentena = int(row[4] or 0)
        return {
            "arquivo_db": str(self._db_path),
            "pasta_memoria": str(self.memory_folder),
            "total_pares": total_pares,
            "total_nomes": total_nomes,
            "total_documentos": total_docs,
            "pares_ativos": pares_ativos,
            "pares_quarentena": pares_quarentena,
        }

    def buscar_documento_por_nome(self, nome: str, campo: Optional[str] = None) -> Optional[str]:
        """
        Retorna documento aprendido para um nome.

        So retorna automaticamente quando:
        - houver candidato unico, ou
        - lider tiver vantagem clara sobre o segundo.
        """
        nome_key = self._normalizar_nome_chave(nome)
        if not nome_key or len(nome_key) < 5:
            return None

        candidatos = None
        if campo:
            campo_key = self._normalizar_campo(campo)
            if campo_key:
                candidatos = self._nome_para_docs_por_campo.get(campo_key, {}).get(nome_key)

        # Fallback global apenas quando nao ha contexto de campo.
        if candidatos is None and not campo:
            candidatos = self._nome_para_docs.get(nome_key)
        if not candidatos:
            return None

        return self._selecionar_documento_por_confianca(candidatos, campo=campo_key if campo else None)

    def buscar_nome_por_documento(self, documento: str) -> Optional[str]:
        """Retorna nome aprendido para documento com regra de confianca."""
        doc = self._normalizar_documento(documento)
        if not doc:
            return None

        candidatos = self._doc_para_nomes.get(doc)
        if not candidatos:
            return None

        ranking = sorted(
            (
                (
                    nome_key,
                    str(info.get("nome_original", "")).strip(),
                    int(info.get("ocorrencias", 0)),
                )
                for nome_key, info in candidatos.items()
            ),
            key=lambda x: x[2],
            reverse=True,
        )
        if not ranking:
            return None
        if len(ranking) == 1:
            return ranking[0][1]
        if ranking[0][2] >= ranking[1][2] + self.CONFLITO_MARGEM:
            return ranking[0][1]
        return None

    def existe_documento(self, documento: str) -> bool:
        doc = self._normalizar_documento(documento)
        if not doc:
            return False
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM learned_pairs WHERE documento = ? LIMIT 1",
                (doc,),
            )
            return cur.fetchone() is not None

    def aprender_com_txt(self, caminho_txt: str) -> Dict[str, object]:
        """
        Aprende pares nome<->documento a partir de TXT corrigido.

        Retorna resumo detalhado para ser exibido no log da GUI.
        """
        caminho_resolvido = str(Path(caminho_txt).resolve())
        arquivo_sha256 = self._calcular_sha256_arquivo(caminho_resolvido)
        dados = parse_txt_siproquim(caminho_txt)
        registros_tn = list(dados.get("tn", []))

        candidatos: Dict[Tuple[str, str, str], Dict[str, object]] = {}
        ignorados = 0
        invalidas = len(dados.get("invalidas", []))

        for registro in registros_tn:
            nf = str(registro.get("nf_numero", "")).strip() or "N/A"
            campos = [
                ("contratante", registro.get("contratante_nome"), registro.get("contratante_cnpj")),
                ("emitente", registro.get("emitente_nome"), registro.get("emitente_cnpj")),
                ("destinatario", registro.get("destinatario_nome"), registro.get("destinatario_cnpj")),
            ]

            for campo, nome_raw, doc_raw in campos:
                nome = str(nome_raw or "").strip()
                nome_key = self._normalizar_nome_chave(nome)
                doc, tipo_doc = self._normalizar_e_validar_documento(doc_raw)

                if not nome_key or len(nome_key) < 5:
                    ignorados += 1
                    continue
                if not doc:
                    ignorados += 1
                    continue

                chave = (nome_key, doc, campo)
                item = candidatos.setdefault(
                    chave,
                    {
                        "campo": campo,
                        "nome_key": nome_key,
                        "nome_original": nome,
                        "documento": doc,
                        "tipo_documento": tipo_doc,
                        "ocorrencias": 0,
                        "nfs": set(),
                    },
                )
                item["ocorrencias"] = int(item["ocorrencias"]) + 1
                item["nfs"].add(nf)

        resumo = self._persistir_aprendizado(
            caminho_resolvido,
            arquivo_sha256,
            registros_tn,
            candidatos,
            ignorados,
            invalidas,
        )
        if not resumo.get("replay_detectado", False):
            self._recarregar_cache()
        return resumo

    def _persistir_aprendizado(
        self,
        caminho_txt: str,
        arquivo_sha256: str,
        registros_tn: List[Dict[str, str]],
        candidatos: Dict[Tuple[str, str, str], Dict[str, object]],
        ignorados: int,
        invalidas: int,
    ) -> Dict[str, object]:
        aprendidos = 0
        atualizados = 0
        promovidos = 0
        rebaixados = 0
        ativos_sessao = 0
        quarentena_sessao = 0
        detalhes: List[str] = []
        agora = datetime.now().isoformat(timespec="seconds")
        origem_arquivo = str(Path(caminho_txt).resolve())
        pendentes: List[Dict[str, object]] = []
        grupos_tocados: set[Tuple[str, str]] = set()

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, processado_em, arquivo_txt
                FROM learn_sessions
                WHERE arquivo_sha256 = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (arquivo_sha256,),
            )
            sessao_existente = cur.fetchone()
            if sessao_existente:
                sessao_id = int(sessao_existente["id"])
                processado_em = str(sessao_existente["processado_em"] or "")
                arquivo_ref = str(sessao_existente["arquivo_txt"] or "")
                return {
                    "arquivo_txt": origem_arquivo,
                    "arquivo_db": str(self._db_path),
                    "pasta_memoria": str(self.memory_folder),
                    "arquivo_sha256": arquivo_sha256,
                    "total_tn": len(registros_tn),
                    "candidatos": len(candidatos),
                    "aprendidos_novos": 0,
                    "atualizados": 0,
                    "promovidos": 0,
                    "rebaixados": 0,
                    "ativos_sessao": 0,
                    "quarentena_sessao": 0,
                    "ignorados": ignorados,
                    "linhas_invalidas": invalidas,
                    "replay_detectado": True,
                    "sessao_referencia_id": sessao_id,
                    "sessao_referencia_data": processado_em,
                    "sessao_referencia_arquivo": arquivo_ref,
                    "detalhes": [
                        f"[REPLAY] Arquivo ja aprendido (sessao #{sessao_id} em {processado_em}). "
                        "Nenhuma alteracao aplicada."
                    ],
                }

            cur.execute(
                """
                INSERT INTO learn_sessions
                (
                    arquivo_txt, arquivo_sha256, processado_em,
                    total_tn, candidatos, aprendidos, atualizados,
                    ignorados, linhas_invalidas
                )
                VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
                """,
                (
                    origem_arquivo,
                    arquivo_sha256,
                    agora,
                    len(registros_tn),
                    len(candidatos),
                    ignorados,
                    invalidas,
                ),
            )
            session_id = int(cur.lastrowid)

            for item in sorted(
                candidatos.values(),
                key=lambda x: (
                    str(x.get("campo", "")),
                    str(x.get("nome_original", "")),
                    str(x.get("documento", "")),
                ),
            ):
                nome_key = str(item["nome_key"])
                doc = str(item["documento"])
                campo = str(item["campo"])
                nome_original = str(item["nome_original"])
                tipo_doc = str(item["tipo_documento"])
                inc = int(item["ocorrencias"])
                nf_amostra = ",".join(sorted(item["nfs"]))[:120]
                campo_norm = self._normalizar_campo(campo)
                if not campo_norm:
                    continue

                cur.execute(
                    """
                    SELECT ocorrencias, status
                    FROM learned_pairs
                    WHERE nome_key = ? AND documento = ? AND campo = ?
                    """,
                    (nome_key, doc, campo_norm),
                )
                row = cur.fetchone()
                status_anterior = self.STATUS_QUARENTENA

                if row is None:
                    cur.execute(
                        """
                        INSERT INTO learned_pairs
                        (
                            nome_key, nome_original, documento, tipo_documento, campo,
                            ocorrencias, status, status_motivo,
                            origem_arquivo, primeira_ocorrencia, ultima_ocorrencia
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            nome_key,
                            nome_original,
                            doc,
                            tipo_doc,
                            campo_norm,
                            inc,
                            self.STATUS_QUARENTENA,
                            "novo_par",
                            origem_arquivo,
                            agora,
                            agora,
                        ),
                    )
                    acao_base = "novo"
                    aprendidos += 1
                else:
                    status_anterior = self._normalizar_status(row["status"])
                    total = int(row["ocorrencias"] or 0) + inc
                    cur.execute(
                        """
                        UPDATE learned_pairs
                        SET nome_original = ?, tipo_documento = ?, ocorrencias = ?, origem_arquivo = ?, ultima_ocorrencia = ?
                        WHERE nome_key = ? AND documento = ? AND campo = ?
                        """,
                        (
                            nome_original,
                            tipo_doc,
                            total,
                            origem_arquivo,
                            agora,
                            nome_key,
                            doc,
                            campo_norm,
                        ),
                    )
                    acao_base = "atualizado"
                    atualizados += 1

                grupos_tocados.add((nome_key, campo_norm))
                pendentes.append(
                    {
                        "acao_base": acao_base,
                        "campo": campo_norm,
                        "nome_original": nome_original,
                        "nome_key": nome_key,
                        "documento": doc,
                        "tipo_documento": tipo_doc,
                        "ocorrencias_arquivo": inc,
                        "nf_amostra": nf_amostra,
                        "status_anterior": status_anterior,
                    }
                )

            for nome_key, campo in grupos_tocados:
                self._reclassificar_nome_campo(cur, nome_key, campo, agora)

            for item in pendentes:
                nome_key = str(item["nome_key"])
                doc = str(item["documento"])
                campo = str(item["campo"])
                status_anterior = self._normalizar_status(str(item["status_anterior"]))

                cur.execute(
                    """
                    SELECT ocorrencias, status
                    FROM learned_pairs
                    WHERE nome_key = ? AND documento = ? AND campo = ?
                    """,
                    (nome_key, doc, campo),
                )
                row = cur.fetchone()
                if row is None:
                    continue
                total = int(row["ocorrencias"] or 0)
                status_final = self._normalizar_status(row["status"])

                if status_final == self.STATUS_ATIVO:
                    ativos_sessao += 1
                else:
                    quarentena_sessao += 1

                if status_anterior != self.STATUS_ATIVO and status_final == self.STATUS_ATIVO:
                    promovidos += 1
                elif status_anterior == self.STATUS_ATIVO and status_final != self.STATUS_ATIVO:
                    rebaixados += 1

                acao = self._montar_acao_sessao(
                    str(item["acao_base"]),
                    status_anterior=status_anterior,
                    status_final=status_final,
                )

                cur.execute(
                    """
                    INSERT INTO learn_session_items
                    (session_id, campo, nome_original, nome_key, documento, tipo_documento, acao, ocorrencias_arquivo, ocorrencias_total, nf_amostra)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        campo,
                        str(item["nome_original"]),
                        nome_key,
                        doc,
                        str(item["tipo_documento"]),
                        acao,
                        int(item["ocorrencias_arquivo"]),
                        total,
                        str(item["nf_amostra"]),
                    ),
                )

                if len(detalhes) < 40:
                    detalhes.append(
                        f"[{acao}] {campo}: '{item['nome_original']}' -> {doc} "
                        f"(+{item['ocorrencias_arquivo']}, total={total}, status={status_final}, "
                        f"NF={item['nf_amostra'] or 'N/A'})"
                    )

            cur.execute(
                """
                UPDATE learn_sessions
                SET aprendidos = ?, atualizados = ?
                WHERE id = ?
                """,
                (aprendidos, atualizados, session_id),
            )
            conn.commit()

        return {
            "arquivo_txt": origem_arquivo,
            "arquivo_db": str(self._db_path),
            "pasta_memoria": str(self.memory_folder),
            "arquivo_sha256": arquivo_sha256,
            "total_tn": len(registros_tn),
            "candidatos": len(candidatos),
            "aprendidos_novos": aprendidos,
            "atualizados": atualizados,
            "promovidos": promovidos,
            "rebaixados": rebaixados,
            "ativos_sessao": ativos_sessao,
            "quarentena_sessao": quarentena_sessao,
            "ignorados": ignorados,
            "linhas_invalidas": invalidas,
            "replay_detectado": False,
            "detalhes": detalhes,
        }

    def _resolver_caminho_db(self) -> Path:
        """
        Resolve caminho de memoria DENTRO do projeto.

        Estrategia:
        1) Pasta raiz do projeto (pai de `src/`) quando detectada
        2) Diretorio de trabalho atual (fallback)
        """
        arquivo_atual = Path(__file__).resolve()
        candidato_raiz = arquivo_atual.parents[2]  # .../<repo>/src/processador/aprendizado_store.py
        if (candidato_raiz / "src").exists():
            return candidato_raiz / self.MEM_DIRNAME / self.DB_FILENAME

        return Path.cwd() / self.MEM_DIRNAME / self.DB_FILENAME

    @staticmethod
    def _calcular_sha256_arquivo(caminho_txt: str) -> str:
        """Calcula hash SHA-256 do arquivo para detectar replay de aprendizado."""
        digest = hashlib.sha256()
        with open(caminho_txt, "rb") as arquivo:
            for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
                digest.update(bloco)
        return digest.hexdigest()

    @staticmethod
    def _normalizar_nome_chave(nome: str) -> str:
        if not nome:
            return ""
        texto = unicodedata.normalize("NFD", str(nome).upper())
        texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
        texto = re.sub(r"[^A-Z0-9]+", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip()
        if texto in {"NAO INFORMADO", "SEM NOME", "N/A", "NA", "NONE", "NULL"}:
            return ""
        return texto

    @staticmethod
    def _normalizar_documento(documento: str) -> str:
        return "".join(ch for ch in str(documento or "") if ch.isdigit())

    @staticmethod
    def _normalizar_campo(campo: str) -> str:
        texto = str(campo or "").strip().lower()
        if texto in {"emitente", "contratante", "destinatario"}:
            return texto
        return ""

    def _normalizar_status(self, status: object) -> str:
        texto = str(status or "").strip().lower()
        if texto == self.STATUS_ATIVO:
            return self.STATUS_ATIVO
        return self.STATUS_QUARENTENA

    def _montar_acao_sessao(
        self,
        acao_base: str,
        status_anterior: str,
        status_final: str,
    ) -> str:
        """Gera rotulo de auditoria do item aprendido na sessao."""
        base = str(acao_base or "atualizado").upper()
        if status_anterior != self.STATUS_ATIVO and status_final == self.STATUS_ATIVO:
            return f"{base}_PROMOVIDO"
        if status_anterior == self.STATUS_ATIVO and status_final != self.STATUS_ATIVO:
            return f"{base}_REBAIXADO"
        if status_final == self.STATUS_ATIVO:
            return f"{base}_ATIVO"
        return f"{base}_QUARENTENA"

    def _reclassificar_nome_campo(
        self,
        cur: sqlite3.Cursor,
        nome_key: str,
        campo: str,
        _agora: str,
    ) -> None:
        """
        Reclassifica todos os documentos de um (nome, campo) em ativo/quarentena.

        Regra:
        - somente um documento pode ficar ATIVO;
        - se nao houver confianca suficiente, todos ficam em QUARENTENA.
        """
        campo_norm = self._normalizar_campo(campo)
        if not campo_norm:
            return

        cur.execute(
            """
            SELECT documento, ocorrencias
            FROM learned_pairs
            WHERE nome_key = ? AND campo = ?
            """,
            (nome_key, campo_norm),
        )
        rows = cur.fetchall()
        if not rows:
            return

        candidatos = {
            str(row["documento"]): {"ocorrencias": int(row["ocorrencias"] or 0)}
            for row in rows
        }
        escolhido = self._selecionar_documento_por_confianca(candidatos, campo=campo_norm)

        if escolhido:
            cur.execute(
                """
                UPDATE learned_pairs
                SET status = ?, status_motivo = ?
                WHERE nome_key = ? AND campo = ? AND documento = ?
                """,
                (self.STATUS_ATIVO, "confianca_suficiente", nome_key, campo_norm, escolhido),
            )
            cur.execute(
                """
                UPDATE learned_pairs
                SET status = ?, status_motivo = ?
                WHERE nome_key = ? AND campo = ? AND documento <> ?
                """,
                (self.STATUS_QUARENTENA, "conflito_ou_baixa_confianca", nome_key, campo_norm, escolhido),
            )
            return

        cur.execute(
            """
            UPDATE learned_pairs
            SET status = ?, status_motivo = ?
            WHERE nome_key = ? AND campo = ?
            """,
            (self.STATUS_QUARENTENA, "baixa_confianca", nome_key, campo_norm),
        )

    def _selecionar_documento_por_confianca(
        self,
        candidatos: Dict[str, Dict[str, object]],
        campo: Optional[str] = None,
    ) -> Optional[str]:
        """Seleciona documento apenas quando ha confianca suficiente."""
        ranking = sorted(
            ((doc, int(info.get("ocorrencias", 0))) for doc, info in candidatos.items()),
            key=lambda x: x[1],
            reverse=True,
        )
        if not ranking:
            return None
        top_doc, top_count = ranking[0]
        sec_count = ranking[1][1] if len(ranking) > 1 else 0
        total_count = sum(count for _, count in ranking)

        if len(ranking) > 1 and top_count < sec_count + self.CONFLITO_MARGEM:
            return None

        campo_key = self._normalizar_campo(campo or "")
        if campo_key:
            min_occ = int(self.MIN_OCORRENCIAS_POR_CAMPO.get(campo_key, 1))
            min_ratio = float(self.MIN_RAZAO_LIDER_POR_CAMPO.get(campo_key, 0.0))
            ratio = (top_count / total_count) if total_count else 0.0
            if top_count < min_occ:
                return None
            if ratio < min_ratio:
                return None

        return top_doc

    def _normalizar_e_validar_documento(self, documento: str) -> Tuple[Optional[str], Optional[str]]:
        doc = self._normalizar_documento(documento)
        if len(doc) == 14 and validar_cnpj(doc):
            return doc, "CNPJ"
        if len(doc) == 11 and validar_cpf(doc):
            return doc, "CPF"
        return None, None

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _inicializar_schema(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS learned_pairs (
                    nome_key TEXT NOT NULL,
                    nome_original TEXT NOT NULL,
                    documento TEXT NOT NULL,
                    tipo_documento TEXT NOT NULL,
                    campo TEXT NOT NULL,
                    ocorrencias INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'quarentena',
                    status_motivo TEXT,
                    origem_arquivo TEXT,
                    primeira_ocorrencia TEXT NOT NULL,
                    ultima_ocorrencia TEXT NOT NULL,
                    PRIMARY KEY (nome_key, documento, campo)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS learn_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    arquivo_txt TEXT NOT NULL,
                    arquivo_sha256 TEXT,
                    processado_em TEXT NOT NULL,
                    total_tn INTEGER NOT NULL DEFAULT 0,
                    candidatos INTEGER NOT NULL DEFAULT 0,
                    aprendidos INTEGER NOT NULL DEFAULT 0,
                    atualizados INTEGER NOT NULL DEFAULT 0,
                    ignorados INTEGER NOT NULL DEFAULT 0,
                    linhas_invalidas INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS learn_session_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    campo TEXT NOT NULL,
                    nome_original TEXT NOT NULL,
                    nome_key TEXT NOT NULL,
                    documento TEXT NOT NULL,
                    tipo_documento TEXT NOT NULL,
                    acao TEXT NOT NULL,
                    ocorrencias_arquivo INTEGER NOT NULL DEFAULT 1,
                    ocorrencias_total INTEGER NOT NULL DEFAULT 1,
                    nf_amostra TEXT,
                    FOREIGN KEY(session_id) REFERENCES learn_sessions(id)
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_learned_pairs_doc ON learned_pairs(documento)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_learned_pairs_nome ON learned_pairs(nome_key)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_learn_items_session ON learn_session_items(session_id)")

            cur.execute("PRAGMA table_info(learned_pairs)")
            colunas = {str(row[1]) for row in cur.fetchall()}
            if "status" not in colunas:
                cur.execute(
                    "ALTER TABLE learned_pairs ADD COLUMN status TEXT NOT NULL DEFAULT 'quarentena'"
                )
            if "status_motivo" not in colunas:
                cur.execute("ALTER TABLE learned_pairs ADD COLUMN status_motivo TEXT")

            cur.execute("CREATE INDEX IF NOT EXISTS idx_learned_pairs_status ON learned_pairs(status)")

            cur.execute("PRAGMA table_info(learn_sessions)")
            colunas_sessao = {str(row[1]) for row in cur.fetchall()}
            if "arquivo_sha256" not in colunas_sessao:
                cur.execute("ALTER TABLE learn_sessions ADD COLUMN arquivo_sha256 TEXT")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_learn_sessions_sha256 ON learn_sessions(arquivo_sha256)")

            cur.execute(
                """
                SELECT id, arquivo_txt
                FROM learn_sessions
                WHERE arquivo_sha256 IS NULL OR arquivo_sha256 = ''
                """
            )
            for row in cur.fetchall():
                sessao_id = int(row[0])
                arquivo_txt = str(row[1] or "").strip()
                if not arquivo_txt:
                    continue
                try:
                    caminho = Path(arquivo_txt)
                    if not caminho.exists():
                        continue
                    sha = self._calcular_sha256_arquivo(str(caminho))
                    cur.execute(
                        "UPDATE learn_sessions SET arquivo_sha256 = ? WHERE id = ?",
                        (sha, sessao_id),
                    )
                except Exception:
                    # Sessao historica sem arquivo disponivel: mantem sem hash.
                    continue

            # Reclassifica historico existente para ligar modo assistido sem perder dados.
            cur.execute("SELECT DISTINCT nome_key, campo FROM learned_pairs")
            grupos = [(str(row[0]), str(row[1])) for row in cur.fetchall()]
            agora = datetime.now().isoformat(timespec="seconds")
            for nome_key, campo in grupos:
                self._reclassificar_nome_campo(cur, nome_key, campo, agora)
            conn.commit()

    def _recarregar_cache(self) -> None:
        with self._lock:
            nome_para_docs: Dict[str, Dict[str, Dict[str, object]]] = {}
            doc_para_nomes: Dict[str, Dict[str, Dict[str, object]]] = {}
            nome_para_docs_por_campo: Dict[str, Dict[str, Dict[str, Dict[str, object]]]] = {}
            doc_para_nomes_por_campo: Dict[str, Dict[str, Dict[str, Dict[str, object]]]] = {}
            totais_status = {
                self.STATUS_ATIVO: 0,
                self.STATUS_QUARENTENA: 0,
            }

            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT nome_key, documento, campo, nome_original, ocorrencias, status
                    FROM learned_pairs
                    """
                )
                for row in cur.fetchall():
                    nome_key = str(row["nome_key"])
                    doc = str(row["documento"])
                    campo = self._normalizar_campo(str(row["campo"]))
                    nome_original = str(row["nome_original"] or "").strip()
                    total = int(row["ocorrencias"] or 0)
                    status = self._normalizar_status(row["status"])

                    if not campo:
                        continue

                    totais_status[status] = totais_status.get(status, 0) + 1

                    # Apenas pares ATIVOS podem participar da inferencia automatica.
                    if status != self.STATUS_ATIVO:
                        continue

                    # Cache por campo (mais seguro para inferencia contextual)
                    nome_para_docs_por_campo.setdefault(campo, {})
                    nome_para_docs_por_campo[campo].setdefault(nome_key, {})
                    nome_para_docs_por_campo[campo][nome_key][doc] = {
                        "nome_original": nome_original,
                        "ocorrencias": total,
                    }

                    doc_para_nomes_por_campo.setdefault(campo, {})
                    doc_para_nomes_por_campo[campo].setdefault(doc, {})
                    doc_para_nomes_por_campo[campo][doc][nome_key] = {
                        "nome_original": nome_original,
                        "ocorrencias": total,
                    }

                    # Cache global (uso geral/retrocompatibilidade)
                    nome_para_docs.setdefault(nome_key, {})
                    if doc not in nome_para_docs[nome_key]:
                        nome_para_docs[nome_key][doc] = {
                            "nome_original": nome_original,
                            "ocorrencias": 0,
                        }
                    nome_para_docs[nome_key][doc]["ocorrencias"] = int(
                        nome_para_docs[nome_key][doc]["ocorrencias"]
                    ) + total

                    doc_para_nomes.setdefault(doc, {})
                    if nome_key not in doc_para_nomes[doc]:
                        doc_para_nomes[doc][nome_key] = {
                            "nome_original": nome_original,
                            "ocorrencias": 0,
                        }
                    doc_para_nomes[doc][nome_key]["ocorrencias"] = int(
                        doc_para_nomes[doc][nome_key]["ocorrencias"]
                    ) + total

            self._nome_para_docs = nome_para_docs
            self._doc_para_nomes = doc_para_nomes
            self._nome_para_docs_por_campo = nome_para_docs_por_campo
            self._doc_para_nomes_por_campo = doc_para_nomes_por_campo
            self._totais_status = totais_status
