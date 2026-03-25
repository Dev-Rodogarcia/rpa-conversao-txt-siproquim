import tempfile
import unittest
from pathlib import Path

from src.gerador import GeradorTXT
from src.processador.aprendizado_store import AprendizadoStore
from src.processador.base_conhecimento import BaseConhecimentoNomes


class TestAprendizadoStore(unittest.TestCase):
    def _registro(
        self,
        nf_numero: str,
        cte_numero: str,
        emitente_nome: str,
        emitente_cnpj: str,
        contratante_nome: str = "CONTRATANTE PADRAO LTDA",
        contratante_cnpj: str = "12538002000118",
        destinatario_nome: str = "DESTINATARIO PADRAO LTDA",
        destinatario_cnpj: str = "76108349001002",
    ) -> dict:
        return {
            "contratante_cnpj": contratante_cnpj,
            "contratante_nome": contratante_nome,
            "nf_numero": nf_numero,
            "nf_data": "01/01/2026",
            "emitente_cnpj": emitente_cnpj,
            "emitente_nome": emitente_nome,
            "destinatario_cnpj": destinatario_cnpj,
            "destinatario_nome": destinatario_nome,
            "local_retirada": "P",
            "local_entrega": "P",
            "cte_numero": cte_numero,
            "cte_data": "02/01/2026",
            "data_entrega": "03/01/2026",
            "recebedor": destinatario_nome,
        }

    def _gerar_txt(self, pasta: Path, nome: str, registros: list[dict]) -> Path:
        caminho = pasta / nome
        gerador = GeradorTXT("60960473000677")
        gerador.gerar_arquivo(registros, 1, 2026, str(caminho))
        return caminho

    def test_aprende_par_ativo_e_detecta_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store = AprendizadoStore(db_path=str(raiz / "memoria.sqlite3"))
            txt = self._gerar_txt(
                raiz,
                "aprendizado_ok.txt",
                [
                    self._registro("1001", "4800501", "LAB SUPPLY CENTRAL", "11054013000160"),
                    self._registro("1002", "4800502", "LAB SUPPLY CENTRAL", "11054013000160"),
                ],
            )

            resumo_1 = store.aprender_com_txt(str(txt))
            self.assertFalse(resumo_1["replay_detectado"])
            self.assertEqual(
                store.buscar_documento_por_nome("LAB SUPPLY CENTRAL", campo="emitente"),
                "11054013000160",
            )

            resumo_2 = store.aprender_com_txt(str(txt))
            self.assertTrue(resumo_2["replay_detectado"])

    def test_mantem_quarentena_quando_nome_tem_documentos_conflitantes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store = AprendizadoStore(db_path=str(raiz / "memoria.sqlite3"))
            txt = self._gerar_txt(
                raiz,
                "aprendizado_conflito.txt",
                [
                    self._registro("2001", "4800601", "EMPRESA CONFLITO", "11054013000160"),
                    self._registro("2002", "4800602", "EMPRESA CONFLITO", "44114040000130"),
                ],
            )

            resumo = store.aprender_com_txt(str(txt))
            self.assertFalse(resumo["replay_detectado"])
            self.assertIsNone(store.buscar_documento_por_nome("EMPRESA CONFLITO", campo="emitente"))

            memoria = store.resumo_memoria()
            self.assertGreaterEqual(memoria["pares_quarentena"], 2)

    def test_base_conhecimento_consulta_store_por_campo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            store = AprendizadoStore(db_path=str(raiz / "memoria.sqlite3"))
            txt = self._gerar_txt(
                raiz,
                "aprendizado_base.txt",
                [
                    self._registro("3001", "4800701", "INDUSTRIA TESTE CAMPO", "11054013000160"),
                    self._registro("3002", "4800702", "INDUSTRIA TESTE CAMPO", "11054013000160"),
                ],
            )
            store.aprender_com_txt(str(txt))

            anterior = BaseConhecimentoNomes._store_aprendizado
            BaseConhecimentoNomes._store_aprendizado = store
            try:
                self.assertEqual(
                    BaseConhecimentoNomes.buscar_cnpj_por_nome("INDUSTRIA TESTE CAMPO", campo="emitente"),
                    "11054013000160",
                )
                self.assertIsNone(
                    BaseConhecimentoNomes.buscar_cnpj_por_nome("INDUSTRIA TESTE CAMPO", campo="destinatario")
                )
            finally:
                BaseConhecimentoNomes._store_aprendizado = anterior


if __name__ == "__main__":
    unittest.main()
