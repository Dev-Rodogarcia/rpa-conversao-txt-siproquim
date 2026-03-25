import tempfile
import unittest
from pathlib import Path

from main import processar_pdf
from src.gerador.txt_parser import parse_txt_siproquim
from src.gerador.txt_validator import validar_txt_siproquim_arquivo


ROOT_DIR = Path(__file__).resolve().parents[1]
PDF_EXEMPLO = ROOT_DIR / "docs" / "pdfs-conversao" / "frete_produtos_controlados_20260311_1624.pdf"
PDF_CWB_JAN = ROOT_DIR / "docs" / "pdfs-conversao" / "frete_produtos_controlados_01.2026_CWB.pdf"


class TestRealPDFPipeline(unittest.TestCase):
    def _processar_pdf_real(self, pdf_path: Path, cnpj_filial: str) -> tuple[Path, list[tuple[str, dict]]]:
        eventos: list[tuple[str, dict]] = []

        def callback(etapa, detalhes):
            eventos.append((etapa, dict(detalhes)))

        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        caminho_saida = Path(pasta.name) / f"{pdf_path.stem}.txt"
        processar_pdf(
            str(pdf_path),
            cnpj_filial,
            str(caminho_saida),
            callback_progresso=callback,
            mes=1,
            ano=2026,
        )
        return caminho_saida, eventos

    def test_pdf_exemplo_substitui_recebedor_placeholder_sem_quebrar_layout(self) -> None:
        if not PDF_EXEMPLO.exists():
            self.skipTest(f"PDF de exemplo ausente: {PDF_EXEMPLO}")

        caminho_saida, eventos = self._processar_pdf_real(PDF_EXEMPLO, "60960473000677")

        resultado = validar_txt_siproquim_arquivo(caminho_saida)
        self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])

        dados = parse_txt_siproquim(str(caminho_saida))
        recebedores = {registro["recebedor"] for registro in dados["cc"]}
        self.assertNotIn("-", recebedores)
        self.assertNotIn("ASSINATURA", recebedores)
        self.assertIn("SANDRA REGINA MASETTO ANTUNES CNPQ PROC", recebedores)

        mensagens = [
            detalhes.get("mensagem", "")
            for etapa, detalhes in eventos
            if etapa == "processar_log"
        ]
        self.assertFalse(any("Recebedor muito curto: '-'" in msg for msg in mensagens))

    def test_pdf_exemplo_exporta_cpfs_sem_zerofill_nos_campos_tn(self) -> None:
        if not PDF_EXEMPLO.exists():
            self.skipTest(f"PDF de exemplo ausente: {PDF_EXEMPLO}")

        caminho_saida, _ = self._processar_pdf_real(PDF_EXEMPLO, "60960473000677")
        linhas = caminho_saida.read_text(encoding="utf-8").splitlines()

        tn_por_nf = {}
        for linha in linhas:
            if linha.startswith("TN"):
                tn_por_nf[linha[86:96].strip()] = linha

        self.assertEqual(tn_por_nf["1373"][190:204], "   06748665922")
        self.assertEqual(tn_por_nf["32005"][190:204], "   14114817808")
        self.assertEqual(tn_por_nf["13064"][190:204], "   02089192445")

    def test_pdf_real_com_cte_ausente_gera_alerta_e_txt_valido(self) -> None:
        if not PDF_CWB_JAN.exists():
            self.skipTest(f"PDF de exemplo ausente: {PDF_CWB_JAN}")

        caminho_saida, eventos = self._processar_pdf_real(PDF_CWB_JAN, "60960473000677")

        resultado = validar_txt_siproquim_arquivo(caminho_saida)
        self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])

        dados = parse_txt_siproquim(str(caminho_saida))
        nfs_tn = {registro["nf_numero"] for registro in dados["tn"]}
        self.assertIn("18103", nfs_tn)
        self.assertLess(len(dados["cc"]), len(dados["tn"]))

        ajustes = [
            detalhes.get("mensagem", "")
            for etapa, detalhes in eventos
            if etapa == "ajuste_manual"
        ]
        self.assertTrue(any("linha CC pode nao ser gerada" in msg for msg in ajustes))


if __name__ == "__main__":
    unittest.main()
