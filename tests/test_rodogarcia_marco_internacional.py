import tempfile
import unittest
from pathlib import Path

from main import processar_pdf
from src.gerador.txt_validator import validar_txt_siproquim_arquivo


ROOT_DIR = Path(__file__).resolve().parents[1]
PDF_RODOGARCIA_MARCO = ROOT_DIR / "docs" / "contexto" / "Rodogarcia - CPQ - Março.pdf"


class TestRodogarciaMarcoInternacional(unittest.TestCase):
    def test_nf_exterior_sem_documento_vira_ti_pi_e_nacional_exige_documento(self) -> None:
        self.assertTrue(PDF_RODOGARCIA_MARCO.exists(), f"PDF nao encontrado: {PDF_RODOGARCIA_MARCO}")
        pendencias_recebidas = []
        eventos = []

        def callback(etapa, detalhes):
            eventos.append((etapa, dict(detalhes)))

        def resolver_pendencias(pendencias):
            pendencias_recebidas.extend(pendencias)
            resposta = {"autorizadas": [], "documentos": []}
            for pendencia in pendencias:
                if pendencia["nf"] == "45861" and pendencia["campo"] == "destinatario_cnpj":
                    resposta["documentos"].append({
                        "nf": "45861",
                        "campo": "destinatario_cnpj",
                        "documento": "30064034000100",
                    })
                else:
                    self.fail(f"Pendencia inesperada no PDF Rodogarcia: {pendencia}")
            return resposta

        with tempfile.TemporaryDirectory() as tmp:
            caminho_saida = Path(tmp) / "rodogarcia_marco.txt"
            processar_pdf(
                str(PDF_RODOGARCIA_MARCO),
                "60960473000758",
                str(caminho_saida),
                mes=3,
                ano=2026,
                callback_progresso=callback,
                callback_resolver_pendencias=resolver_pendencias,
            )

            resultado = validar_txt_siproquim_arquivo(caminho_saida)
            self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])

            linhas = caminho_saida.read_text(encoding="utf-8").splitlines()
            linhas_tn_411574 = [linha for linha in linhas if linha.startswith("TN") and linha[86:96].strip() == "411574"]
            linhas_ti_411574 = [linha for linha in linhas if linha.startswith("TI") and linha[4:14].strip() == "411574"]
            idx_ti = linhas.index(linhas_ti_411574[0])

            self.assertEqual(linhas_tn_411574, [])
            self.assertEqual(len(linhas_ti_411574), 1)
            self.assertEqual(linhas[idx_ti + 1][:2], "PI")
            self.assertEqual(linhas[idx_ti + 1][72:75], "056")
            self.assertEqual(
                {(p["nf"], p["campo"]) for p in pendencias_recebidas},
                {("45861", "destinatario_cnpj")},
            )
            mensagens_411574 = [
                detalhes.get("mensagem", "")
                for etapa, detalhes in eventos
                if "411574" in detalhes.get("mensagem", "")
            ]
            self.assertTrue(any("TI/PI" in mensagem for mensagem in mensagens_411574))
            self.assertFalse(any("CNPJ Destinat" in mensagem and "VAZIO" in mensagem for mensagem in mensagens_411574))


if __name__ == "__main__":
    unittest.main()
