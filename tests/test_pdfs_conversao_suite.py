import tempfile
import unittest
from pathlib import Path

from main import processar_pdf
from src.gerador.txt_parser import parse_txt_siproquim
from src.gerador.txt_validator import validar_txt_siproquim_arquivo


ROOT_DIR = Path(__file__).resolve().parents[1]
PDFS_DIR = ROOT_DIR / "docs" / "pdfs-conversao"

MAPA_FILIAIS = {
    "AGU": "60960473001134",
    "CAS": "60960473000596",
    "CPQ": "60960473000758",
    "CWB": "60960473000677",
    "NHB": "60960473001568",
    "SPO": "60960473000243",
}

RECEBEDORES_INVALIDOS = {"-", "ASSINATURA", "RUBRICA"}
EXPECTATIVAS_ARQUIVOS = {
    "frete_produtos_controlados_01.2026_AGU.pdf": {"tn": 2, "cc": 2},
    "frete_produtos_controlados_01.2026_CAS.pdf": {"tn": 21, "cc": 21},
    "frete_produtos_controlados_01.2026_CPQ.pdf": {"tn": 354, "cc": 352},
    "frete_produtos_controlados_01.2026_CWB.pdf": {"tn": 25, "cc": 24},
    "frete_produtos_controlados_01.2026_NHB.pdf": {"tn": 38, "cc": 38},
    "frete_produtos_controlados_01.2026_SPO.pdf": {"tn": 127, "cc": 127},
    "frete_produtos_controlados_20260311_1624.pdf": {"tn": 46, "cc": 46},
}


def _resolver_cnpj_filial(pdf_path: Path) -> str | None:
    nome = pdf_path.name.upper()
    for sigla, cnpj in MAPA_FILIAIS.items():
        if f"_{sigla}.PDF" in nome:
            return cnpj
    if "20260311_1624" in nome:
        return MAPA_FILIAIS["CWB"]
    return None


class TestPDFsConversaoSuite(unittest.TestCase):
    def test_todos_pdfs_reais_geram_txt_estruturalmente_valido(self) -> None:
        pdfs = sorted(PDFS_DIR.glob("frete_produtos_controlados_*.pdf"))
        self.assertTrue(pdfs, f"Nenhum PDF encontrado em {PDFS_DIR}")

        for pdf_path in pdfs:
            cnpj_filial = _resolver_cnpj_filial(pdf_path)
            with self.subTest(pdf=pdf_path.name):
                self.assertIsNotNone(cnpj_filial, f"Sem mapeamento de filial para {pdf_path.name}")

                eventos = []

                def callback(etapa, detalhes):
                    eventos.append((etapa, dict(detalhes)))

                with tempfile.TemporaryDirectory() as tmp:
                    caminho_saida = Path(tmp) / f"{pdf_path.stem}.txt"
                    processar_pdf(
                        str(pdf_path),
                        str(cnpj_filial),
                        str(caminho_saida),
                        callback_progresso=callback,
                        mes=1,
                        ano=2026,
                    )

                    resultado = validar_txt_siproquim_arquivo(caminho_saida)
                    self.assertTrue(
                        resultado.valido,
                        [erro.formatar() for erro in resultado.erros],
                    )

                    dados = parse_txt_siproquim(str(caminho_saida))
                    expectativas = EXPECTATIVAS_ARQUIVOS.get(pdf_path.name)
                    self.assertIsNotNone(expectativas, f"Sem expectativa cadastrada para {pdf_path.name}")
                    self.assertEqual(len(dados["tn"]), expectativas["tn"], "Quantidade TN divergente")
                    self.assertEqual(len(dados["cc"]), expectativas["cc"], "Quantidade CC divergente")

                    recebedores_invalidos = sorted(
                        {
                            cc["recebedor"]
                            for cc in dados["cc"]
                            if cc["recebedor"] in RECEBEDORES_INVALIDOS
                        }
                    )
                    self.assertEqual(recebedores_invalidos, [], f"Recebedores invalidos no CC: {recebedores_invalidos}")

                    mensagens_logs = [
                        detalhes.get("mensagem", "")
                        for etapa, detalhes in eventos
                        if etapa == "processar_log"
                    ]
                    mensagens_erros = [
                        detalhes.get("mensagem", "")
                        for etapa, detalhes in eventos
                        if etapa in {"processar_erro", "processar_critico"}
                    ]
                    self.assertEqual(mensagens_erros, [], f"Erros criticos/operacionais no callback: {mensagens_erros}")
                    self.assertTrue(
                        any("TXT validado localmente apos gravacao" in mensagem for mensagem in mensagens_logs),
                        "Validacao final do TXT nao registrada no callback",
                    )
                    if expectativas["cc"] < expectativas["tn"]:
                        ajustes = [
                            detalhes.get("mensagem", "")
                            for etapa, detalhes in eventos
                            if etapa == "ajuste_manual"
                        ]
                        self.assertTrue(
                            any("CT-e sem numero e data; a linha CC pode nao ser gerada." in msg for msg in ajustes),
                            "Diferenca TN/CC sem explicacao por CT-e ausente",
                        )


if __name__ == "__main__":
    unittest.main()
