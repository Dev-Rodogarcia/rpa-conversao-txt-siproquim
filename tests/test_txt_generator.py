import tempfile
import unittest
from pathlib import Path

from src.gerador import GeradorTXT
from src.gerador.sanitizers import sanitizar_alfanumerico, sanitizar_documento
from src.gerador.txt_validator import validar_txt_siproquim_arquivo


class TestSanitizers(unittest.TestCase):
    def test_sanitizar_documento_preserva_cnpj_valido(self) -> None:
        self.assertEqual(sanitizar_documento("12538002000118", 14), "12538002000118")

    def test_sanitizar_documento_alinha_cpf_valido_sem_zerofill(self) -> None:
        self.assertEqual(sanitizar_documento("06748665922", 14), "   06748665922")

    def test_sanitizar_alfanumerico_remove_acentos_e_simbolos(self) -> None:
        self.assertEqual(sanitizar_alfanumerico("00ab-12/ç", 10), "AB12C     ")


class TestGeradorTXT(unittest.TestCase):
    def test_gerador_revalida_txt_apos_gravacao(self) -> None:
        eventos = []

        def callback(etapa, detalhes):
            eventos.append((etapa, detalhes))

        nf = {
            "contratante_cnpj": "12538002000118",
            "contratante_nome": "ERMEX",
            "nf_numero": "31967",
            "nf_data": "02/02/2026",
            "emitente_cnpj": "12538002000118",
            "emitente_nome": "ERMEX",
            "destinatario_cnpj": "07483401000350",
            "destinatario_nome": "TOTAL BIOTECNOLOGIA INDUSTRIA E COMERCIO S/A",
            "local_retirada": "p",
            "local_entrega": "p",
            "cte_numero": "4800503",
            "cte_data": "03/02/2026",
            "data_entrega": "10/02/2026",
            "recebedor": "TOTAL BIOTECNOLOGIA INDUSTRIA E COMERCIO S/A",
        }

        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        handle.close()
        caminho = Path(handle.name)
        self.addCleanup(caminho.unlink, missing_ok=True)

        gerador = GeradorTXT("60960473000677")
        caminho_gerado = gerador.gerar_arquivo([nf], 2, 2026, str(caminho), callback_progresso=callback)

        self.assertEqual(Path(caminho_gerado), caminho)

        resultado = validar_txt_siproquim_arquivo(caminho)
        self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])
        self.assertEqual(resultado.total_linhas, 3)

        logs_check = [
            detalhes["mensagem"]
            for etapa, detalhes in eventos
            if etapa == "processar_log" and detalhes.get("tipo") == "CHECK"
        ]
        self.assertTrue(any("TXT validado localmente apos gravacao" in msg for msg in logs_check))

    def test_nao_trata_associacao_como_assinatura_no_recebedor(self) -> None:
        eventos = []

        def callback(etapa, detalhes):
            eventos.append((etapa, detalhes))

        nf = {
            "contratante_cnpj": "44114040000130",
            "contratante_nome": "CARBON CIENTIFICA",
            "nf_numero": "18606",
            "nf_data": "10/02/2026",
            "emitente_cnpj": "44114040000130",
            "emitente_nome": "CARBON CIENTIFICA",
            "destinatario_cnpj": "33564881000122",
            "destinatario_nome": "ASSOCIACAO BRASILEIRA BENEFICENTE DE REABILITACAO",
            "local_retirada": "P",
            "local_entrega": "P",
            "cte_numero": "48855",
            "cte_data": "11/02/2026",
            "data_entrega": "19/02/2026",
            "recebedor": "ASSOCIACAO BRASILEIRA BENEFICENTE DE REABILITACAO",
        }

        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        handle.close()
        caminho = Path(handle.name)
        self.addCleanup(caminho.unlink, missing_ok=True)

        gerador = GeradorTXT("60960473000677")
        gerador.gerar_arquivo([nf], 2, 2026, str(caminho), callback_progresso=callback)

        alertas_recebedor = [
            detalhes["mensagem"]
            for etapa, detalhes in eventos
            if etapa == "processar_log" and "Recebedor suspeito" in detalhes.get("mensagem", "")
        ]
        self.assertEqual(alertas_recebedor, [])

    def test_gerar_linha_tn_posiciona_documento_nas_posicoes_3_a_16(self) -> None:
        gerador = GeradorTXT("60960473000677")
        nf = {
            "contratante_cnpj": "06748665922",
            "contratante_nome": "CARLOS VINICIUS DALTO DA ROSA",
            "nf_numero": "1373",
            "nf_data": "04/02/2026",
            "emitente_cnpj": "43422189000113",
            "emitente_nome": "RDBM COMERCIO",
            "destinatario_cnpj": "33724423000103",
            "destinatario_nome": "PREBMOL - PREFABRICADOS LTDA",
            "local_retirada": "P",
            "local_entrega": "P",
        }

        linha = gerador.gerar_linha_TN(nf)

        self.assertEqual(len(linha), 276)
        self.assertEqual(linha[:2], "TN")
        self.assertEqual(linha[2:16], "   06748665922")

    def test_gerar_linha_tn_exporta_cpf_destino_sem_zerofill(self) -> None:
        gerador = GeradorTXT("60960473000677")
        nf = {
            "contratante_cnpj": "12538002000118",
            "contratante_nome": "ERMEX",
            "nf_numero": "32005",
            "nf_data": "06/02/2026",
            "emitente_cnpj": "12538002000118",
            "emitente_nome": "ERMEX",
            "destinatario_cnpj": "14114817808",
            "destinatario_nome": "SANDRA REGINA MASETTO ANTUNES CNPQ PROC",
            "local_retirada": "P",
            "local_entrega": "P",
        }

        linha = gerador.gerar_linha_TN(nf)

        self.assertEqual(len(linha), 276)
        self.assertEqual(linha[190:204], "   14114817808")

    def test_gerar_linha_tn_bloqueia_destino_vazio_sem_autorizacao(self) -> None:
        gerador = GeradorTXT("60960473000677")
        nf = {
            "contratante_cnpj": "43996693000127",
            "contratante_nome": "PPG SUM",
            "nf_numero": "411574",
            "nf_data": "13/03/2026",
            "emitente_cnpj": "43996693000127",
            "emitente_nome": "PPG SUM",
            "destinatario_cnpj": "",
            "destinatario_nome": "PPG COATINGS BELGIUM BV/SRL",
            "local_retirada": "P",
            "local_entrega": "P",
        }

        with self.assertRaises(ValueError):
            gerador.gerar_linha_TN(nf)

    def test_gerar_arquivo_exterior_gera_ti_pi_sem_tn_cc(self) -> None:
        eventos = []

        def callback(etapa, detalhes):
            eventos.append((etapa, detalhes))

        nf = {
            "contratante_cnpj": "43996693000127",
            "contratante_nome": "PPG SUM",
            "nf_numero": "411574",
            "nf_data": "13/03/2026",
            "emitente_cnpj": "43996693000127",
            "emitente_nome": "PPG SUM",
            "destinatario_cnpj": "",
            "destinatario_exterior": True,
            "destinatario_nome": "PPG COATINGS BELGIUM BV/SRL",
            "destinatario_texto": (
                "DESTINATÁRIO\n"
                "PPG COATINGS BELGIUM BV/SRL\n"
                "CNPJ/CPF:\n"
                "END: CHAUSSEE DE HAECHT, 1465 - HAACHTSESTEENWEG - HAREN\n"
                "CEP: 99999-999 CIDADE: EXTERIOR - EX"
            ),
            "local_retirada": "P",
            "local_entrega": "P",
            "cte_numero": "38842",
            "cte_data": "13/03/2026",
            "data_entrega": "17/03/2026",
        }

        handle = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        handle.close()
        caminho = Path(handle.name)
        self.addCleanup(caminho.unlink, missing_ok=True)

        gerador = GeradorTXT("60960473000677")
        gerador.gerar_arquivo([nf], 3, 2026, str(caminho), callback_progresso=callback)

        resultado = validar_txt_siproquim_arquivo(caminho)
        self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])

        linhas = caminho.read_text(encoding="utf-8").splitlines()
        self.assertEqual([linha[:2] for linha in linhas], ["EM", "TI", "PI"])
        self.assertEqual(len(linhas[1]), 109)
        self.assertEqual(len(linhas[2]), 145)
        self.assertEqual(linhas[1][2], "E")
        self.assertEqual(linhas[1][3], "O")
        self.assertEqual(linhas[1][4:14].strip(), "411574")
        self.assertEqual(linhas[2][72:75], "056")


if __name__ == "__main__":
    unittest.main()
