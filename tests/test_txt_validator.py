import tempfile
import unittest
from pathlib import Path

from src.gerador.txt_validator import validar_txt_siproquim_arquivo


EM_FIXA = "EM60960473000677FEV202600000010"


def formatar_documento(doc: str) -> str:
    digitos = "".join(ch for ch in str(doc) if ch.isdigit())
    if len(digitos) == 11:
        return digitos.rjust(14)
    return digitos[:14].rjust(14)


def montar_tn(
    contratante_doc: str = "12538002000118",
    contratante_nome: str = "EMPRESA CONTRATANTE",
    nf_numero: str = "12345",
    nf_data: str = "01/02/2026",
    origem_doc: str = "12538002000118",
    origem_nome: str = "ORIGEM DA CARGA",
    destino_doc: str = "07483401000350",
    destino_nome: str = "DESTINO DA CARGA",
    local_retirada: str = "P",
    local_entrega: str = "P",
) -> str:
    return (
        "TN"
        + formatar_documento(contratante_doc)
        + contratante_nome[:70].ljust(70)
        + nf_numero[:10].ljust(10)
        + nf_data[:10].ljust(10)
        + formatar_documento(origem_doc)
        + origem_nome[:70].ljust(70)
        + formatar_documento(destino_doc)
        + destino_nome[:70].ljust(70)
        + local_retirada[:1]
        + local_entrega[:1]
    )


def montar_cc(modal: str = "RO") -> str:
    return (
        "CC"
        + "123456789"
        + "01/02/2026"
        + "02/02/2026"
        + "RESPONSAVEL RECEBIMENTO".ljust(70)
        + modal
    )


def montar_lr() -> str:
    return "LR" + "42345678000199" + "ARMAZEM RETIRADA".ljust(70)


def montar_ti(
    operacao: str = "E",
    contratante: str = "O",
    nf_numero: str = "411574",
    nf_data: str = "13/03/2026",
    empresa_doc: str = "43996693000127",
    empresa_nome: str = "PPG SUM",
    local_armazenamento: str = "P",
) -> str:
    return (
        "TI"
        + operacao[:1]
        + contratante[:1]
        + nf_numero[:10].ljust(10)
        + nf_data[:10].ljust(10)
        + formatar_documento(empresa_doc)
        + empresa_nome[:70].ljust(70)
        + local_armazenamento[:1]
    )


def montar_pi(
    nome: str = "PPG COATINGS BELGIUM BV SRL",
    pais_id: str = "056",
    endereco: str = "CHAUSSEE DE HAECHT 1465 HAACHTSESTEENWEG HAREN",
) -> str:
    return "PI" + nome[:70].ljust(70) + pais_id[:3].rjust(3, "0") + endereco[:70].ljust(70)


def escrever_temporario(*linhas: str) -> Path:
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    handle.close()
    caminho = Path(handle.name)
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


class TestTXTValidator(unittest.TestCase):
    def test_detecta_linha_tn_curta_com_mensagem_estilo_siproquim(self) -> None:
        linha_curta = "TN" + "12345678000199" + "NOME CURTO".ljust(35)
        self.assertEqual(len(linha_curta), 51)

        caminho = escrever_temporario(EM_FIXA, linha_curta)
        self.addCleanup(caminho.unlink, missing_ok=True)
        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertFalse(resultado.valido)
        mensagens = [erro.formatar() for erro in resultado.erros]
        self.assertTrue(any("begin 16, end 86, length 51" in msg for msg in mensagens))

    def test_aceita_cc_com_modal_concatenado(self) -> None:
        caminho = escrever_temporario(EM_FIXA, montar_tn(), montar_cc("ROAE"))
        self.addCleanup(caminho.unlink, missing_ok=True)
        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])

    def test_exige_lr_quando_tn_indica_retirada_terceirizada(self) -> None:
        caminho = escrever_temporario(EM_FIXA, montar_tn(local_retirada="A", local_entrega="P"), montar_cc())
        self.addCleanup(caminho.unlink, missing_ok=True)
        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertFalse(resultado.valido)
        mensagens = [erro.formatar() for erro in resultado.erros]
        self.assertTrue(any("subsecao LR" in msg for msg in mensagens))

    def test_aceita_lr_quando_tn_indica_retirada_terceirizada(self) -> None:
        caminho = escrever_temporario(EM_FIXA, montar_tn(local_retirada="A", local_entrega="P"), montar_cc(), montar_lr())
        self.addCleanup(caminho.unlink, missing_ok=True)
        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])

    def test_rejeita_cpf_com_zerofill_no_campo_destino_tn(self) -> None:
        caminho = escrever_temporario(
            EM_FIXA,
            montar_tn(destino_doc="00006748665922", destino_nome="CARLOS VINICIUS DALTO DA ROSA"),
            montar_cc(),
        )
        self.addCleanup(caminho.unlink, missing_ok=True)

        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertFalse(resultado.valido)
        mensagens = [erro.formatar() for erro in resultado.erros]
        self.assertTrue(any("CPF preenchido com zeros a esquerda" in msg for msg in mensagens))

    def test_aceita_cpf_com_padding_em_branco_no_campo_destino_tn(self) -> None:
        caminho = escrever_temporario(
            EM_FIXA,
            montar_tn(destino_doc="06748665922", destino_nome="CARLOS VINICIUS DALTO DA ROSA"),
            montar_cc(),
        )
        self.addCleanup(caminho.unlink, missing_ok=True)

        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])

    def test_destino_vazio_tn_nao_pode_ser_autorizado(self) -> None:
        caminho = escrever_temporario(
            EM_FIXA,
            montar_tn(nf_numero="411574", destino_doc="", destino_nome="PPG COATINGS BELGIUM BV SRL"),
            montar_cc(),
        )
        self.addCleanup(caminho.unlink, missing_ok=True)

        resultado_sem_autorizacao = validar_txt_siproquim_arquivo(caminho)
        self.assertFalse(resultado_sem_autorizacao.valido)

        resultado_autorizado = validar_txt_siproquim_arquivo(
            caminho,
            documentos_destino_vazios_autorizados={"411574"},
        )
        self.assertFalse(resultado_autorizado.valido)
        mensagens = [erro.formatar() for erro in resultado_autorizado.erros]
        self.assertTrue(any("CPF/CNPJ Destino Carga vazio" in msg for msg in mensagens))

    def test_aceita_transporte_internacional_com_pessoa_internacional(self) -> None:
        caminho = escrever_temporario(EM_FIXA, montar_ti(), montar_pi())
        self.addCleanup(caminho.unlink, missing_ok=True)

        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertTrue(resultado.valido, [erro.formatar() for erro in resultado.erros])

    def test_ti_exige_subsecao_pi(self) -> None:
        caminho = escrever_temporario(EM_FIXA, montar_ti())
        self.addCleanup(caminho.unlink, missing_ok=True)

        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertFalse(resultado.valido)
        mensagens = [erro.formatar() for erro in resultado.erros]
        self.assertTrue(any("subsecao PI" in msg for msg in mensagens))

    def test_pi_exige_pais_com_tres_digitos(self) -> None:
        caminho = escrever_temporario(EM_FIXA, montar_ti(), montar_pi(pais_id=""))
        self.addCleanup(caminho.unlink, missing_ok=True)

        resultado = validar_txt_siproquim_arquivo(caminho)

        self.assertFalse(resultado.valido)
        mensagens = [erro.formatar() for erro in resultado.erros]
        self.assertTrue(any("Id do pais" in msg for msg in mensagens))


if __name__ == "__main__":
    unittest.main()
