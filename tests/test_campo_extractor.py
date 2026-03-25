import unittest

from src.extrator.campo_extractor import extrair_recebedor


class TestCampoExtractor(unittest.TestCase):
    def test_extrair_recebedor_descarta_placeholders_operacionais(self) -> None:
        self.assertIsNone(extrair_recebedor("RECEBEDOR: - DATA ENTREGA: 10/02/2026 18:10"))
        self.assertIsNone(extrair_recebedor("RECEBEDOR: ASSINATURA DATA ENTREGA: 10/02/2026 18:10"))
        self.assertIsNone(extrair_recebedor("RECEBEDOR: RUBRICA DATA ENTREGA: 10/02/2026 18:10"))

    def test_extrair_recebedor_preserva_nome_valido(self) -> None:
        self.assertEqual(
            extrair_recebedor("RECEBEDOR: JOSE DA SILVA DATA ENTREGA: 10/02/2026 18:10"),
            "JOSE DA SILVA",
        )


if __name__ == "__main__":
    unittest.main()
