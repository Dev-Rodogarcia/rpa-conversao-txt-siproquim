"""Janela principal do painel operacional do RPA."""

from __future__ import annotations

from datetime import datetime
from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QIcon, QPalette, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from main import extrair_mes_ano_do_pdf
from src.config.filiais import FiliaisManager
from src.gerador.layout_constants import MESES_ALFANUMERICOS
from src.ui.componentes import PALETA_CORES, CartaoEstatistica, EtiquetaStatus
from src.ui.rpa_worker import TrabalhadorExecucaoRpa

LINHAS_LOGS_POR_PAGINA = 8
ALTURA_LINHA_LOG = 60
ALTURA_CABECALHO_TABELA_LOG = 44
LARGURA_COLUNA_LOG_LINHA = 92
LARGURA_COLUNA_LOG_CLIENTE = 240
LARGURA_COLUNA_LOG_STATUS = 156
LARGURA_COLUNA_LOG_HORARIO = 112
LARGURA_COLUNA_LOG_ACAO = 136


class JanelaPainelAutomacao(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.trabalhador_atual: TrabalhadorExecucaoRpa | None = None
        self.ultimo_contexto_execucao: dict | None = None
        self.registros_logs: list[dict] = []
        self.total_logs = 0
        self.total_logs_reprocessaveis = 0
        self.indice_pagina_logs = 0
        self.linhas_por_pagina_logs = LINHAS_LOGS_POR_PAGINA
        self.reprocessamento_habilitado = True
        self.filiais_manager = FiliaisManager()
        self.fonte_mono = QFont("Consolas", 10)
        self.fonte_mono.setStyleHint(QFont.Monospace)

        self.setWindowTitle("RPA REAJUSTE TABELAS VIGENCIA")
        self.resize(1450, 960)
        self.setMinimumSize(1240, 820)
        self._configurar_icone_janela()
        self._aplicar_estilo_global()
        self._montar_interface()
        self._atualizar_status_robo("Parado")
        self._atualizar_estatisticas(
            {"total_registros": 0, "processados": 0, "sucessos": 0, "falhas": 0}
        )
        self._atualizar_progresso({"atual": 0, "total": 0, "percentual": 0})
        self._atualizar_resumo_logs()
        self._renderizar_pagina_logs()

    def _montar_interface(self) -> None:
        scroll_area = QScrollArea()
        scroll_area.setObjectName("scrollPrincipal")
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(scroll_area)

        widget_central = QWidget()
        widget_central.setObjectName("widgetCentral")
        scroll_area.setWidget(widget_central)

        layout_principal = QVBoxLayout(widget_central)
        layout_principal.setContentsMargins(30, 26, 30, 26)
        layout_principal.setSpacing(20)

        layout_principal.addWidget(self._criar_cabecalho())
        layout_principal.addWidget(self._criar_secao_controles())
        layout_principal.addLayout(self._criar_grade_estatisticas())
        layout_principal.addWidget(self._criar_secao_progresso())
        layout_principal.addWidget(self._criar_secao_logs(), 1)
        layout_principal.addWidget(self._criar_rodape())

    def _criar_cabecalho(self) -> QFrame:
        cartao = QFrame()
        cartao.setObjectName("cabecalhoPainel")
        self._aplicar_sombra(cartao, blur=34, deslocamento_y=10)

        layout = QHBoxLayout(cartao)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)

        marca = QWidget()
        layout_marca = QHBoxLayout(marca)
        layout_marca.setContentsMargins(0, 0, 0, 0)
        layout_marca.setSpacing(18)

        rotulo_logo = QLabel()
        pixmap_logo = self._obter_logo_empresa()
        if pixmap_logo is not None:
            rotulo_logo.setPixmap(
                pixmap_logo.scaledToHeight(48, Qt.SmoothTransformation)
            )
        else:
            rotulo_logo.setObjectName("logoFallback")
            rotulo_logo.setText("Rodogarcia")
        layout_marca.addWidget(rotulo_logo, alignment=Qt.AlignVCenter)

        divisor = QFrame()
        divisor.setFixedWidth(1)
        self._definir_cor_fundo(divisor, PALETA_CORES["borda_forte"])
        layout_marca.addWidget(divisor)

        bloco_titulo = QVBoxLayout()
        bloco_titulo.setSpacing(6)

        selo = QLabel("PAINEL OPERACIONAL")
        selo.setObjectName("etiquetaTopo")
        titulo = self._criar_rotulo(
            "RPA REAJUSTE TABELAS VIGENCIA",
            28,
            800,
            PALETA_CORES["texto_padrao"],
        )
        subtitulo = self._criar_rotulo(
            "Painel operacional para copia, vigencia e reajuste em lote no ESL Cloud",
            13,
            400,
            PALETA_CORES["texto_mutado"],
        )
        subtitulo.setWordWrap(True)

        bloco_titulo.addWidget(selo, alignment=Qt.AlignLeft)
        bloco_titulo.addWidget(titulo)
        bloco_titulo.addWidget(subtitulo)
        layout_marca.addLayout(bloco_titulo, 1)
        layout.addWidget(marca, 1)

        painel_status = QFrame()
        painel_status.setObjectName("cabecalhoStatus")
        painel_status.setMinimumWidth(300)

        layout_status = QVBoxLayout(painel_status)
        layout_status.setContentsMargins(18, 18, 18, 18)
        layout_status.setSpacing(8)

        rotulo_status = self._criar_rotulo(
            "Status do robo",
            12,
            600,
            PALETA_CORES["texto_mutado"],
        )
        self.etiqueta_status = EtiquetaStatus("Parado")
        self.rotulo_status_detalhe = self._criar_rotulo(
            "Aguardando nova execucao.",
            13,
            600,
            PALETA_CORES["texto_padrao"],
        )
        self.rotulo_status_horario = self._criar_rotulo(
            "Ultima atualizacao: --:--:--",
            12,
            400,
            PALETA_CORES["texto_mutado"],
        )

        layout_status.addWidget(rotulo_status)
        layout_status.addWidget(self.etiqueta_status, alignment=Qt.AlignLeft)
        layout_status.addWidget(self.rotulo_status_detalhe)
        layout_status.addWidget(self.rotulo_status_horario)
        layout.addWidget(painel_status, alignment=Qt.AlignTop)
        return cartao

    @staticmethod
    def _criar_rotulo(texto: str, tamanho_pixel: int, peso: int, cor: str) -> QLabel:
        rotulo = QLabel(texto)
        JanelaPainelAutomacao._aplicar_fonte_e_cor(rotulo, tamanho_pixel, peso, cor)
        return rotulo

    @staticmethod
    def _aplicar_fonte_e_cor(
        rotulo: QLabel,
        tamanho_pixel: int,
        peso: int,
        cor: str,
    ) -> None:
        fonte = rotulo.font()
        fonte.setPixelSize(tamanho_pixel)
        fonte.setWeight(QFont.Weight(peso))
        rotulo.setFont(fonte)
        paleta = rotulo.palette()
        paleta.setColor(QPalette.WindowText, QColor(cor))
        rotulo.setPalette(paleta)

    @staticmethod
    def _definir_cor_fundo(widget: QWidget, cor: str) -> None:
        widget.setAutoFillBackground(True)
        paleta = widget.palette()
        paleta.setColor(QPalette.Window, QColor(cor))
        widget.setPalette(paleta)

    def _criar_secao_controles(self) -> QFrame:
        cartao = QFrame()
        cartao.setObjectName("cartaoPadrao")
        self._aplicar_sombra(cartao, blur=24, deslocamento_y=5)

        layout = QHBoxLayout(cartao)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(18)

        descricao = QVBoxLayout()
        descricao.setSpacing(6)
        titulo = self._criar_rotulo(
            "Controles de execucao",
            18,
            700,
            PALETA_CORES["texto_padrao"],
        )
        texto = self._criar_rotulo(
            "Inicie uma rodada completa, interrompa com seguranca e acompanhe o estado do robo sem bloquear a interface.",
            13,
            400,
            PALETA_CORES["texto_mutado"],
        )
        texto.setWordWrap(True)
        self.rotulo_contexto_operacao = self._criar_rotulo(
            "Pronto para iniciar uma nova rodada de processamento.",
            12,
            600,
            PALETA_CORES["primaria"],
        )
        descricao.addWidget(titulo)
        descricao.addWidget(texto)
        descricao.addWidget(self.rotulo_contexto_operacao)
        layout.addLayout(descricao, 1)

        bloco_botoes = QHBoxLayout()
        bloco_botoes.setSpacing(12)

        bloco_valor = QVBoxLayout()
        bloco_valor.setSpacing(4)
        rotulo_valor = self._criar_rotulo(
            "Valor do reajuste",
            12,
            600,
            PALETA_CORES["texto_mutado"],
        )
        self.input_valor_reajuste = QLineEdit("15")
        self.input_valor_reajuste.setFixedWidth(120)
        self.input_valor_reajuste.setFixedHeight(38)
        self.input_valor_reajuste.setPlaceholderText("Ex: 15")
        bloco_valor.addWidget(rotulo_valor)
        bloco_valor.addWidget(self.input_valor_reajuste)
        bloco_botoes.addLayout(bloco_valor)
        bloco_botoes.addSpacing(24)

        self.botao_iniciar = QPushButton("Iniciar execucao")
        self.botao_iniciar.setObjectName("botaoPrimario")
        self.botao_iniciar.setCursor(Qt.PointingHandCursor)
        self.botao_iniciar.clicked.connect(self.iniciar_automacao)

        self.botao_parar = QPushButton("Parar execucao")
        self.botao_parar.setObjectName("botaoPerigo")
        self.botao_parar.setCursor(Qt.PointingHandCursor)
        self.botao_parar.clicked.connect(self.parar_automacao)
        self.botao_parar.setEnabled(False)

        bloco_botoes.addWidget(self.botao_iniciar, alignment=Qt.AlignBottom)
        bloco_botoes.addWidget(self.botao_parar, alignment=Qt.AlignBottom)
        layout.addLayout(bloco_botoes)
        return cartao

    def _criar_grade_estatisticas(self) -> QGridLayout:
        grade = QGridLayout()
        grade.setSpacing(18)

        self.cartao_total = CartaoEstatistica(
            "Total de registros",
            PALETA_CORES["primaria"],
        )
        self.cartao_processados = CartaoEstatistica(
            "Processados",
            PALETA_CORES["secundaria"],
        )
        self.cartao_sucessos = CartaoEstatistica(
            "Sucessos",
            PALETA_CORES["sucesso"],
        )
        self.cartao_falhas = CartaoEstatistica(
            "Falhas",
            PALETA_CORES["perigo"],
        )

        grade.addWidget(self.cartao_total, 0, 0)
        grade.addWidget(self.cartao_processados, 0, 1)
        grade.addWidget(self.cartao_sucessos, 0, 2)
        grade.addWidget(self.cartao_falhas, 0, 3)
        for indice in range(4):
            grade.setColumnStretch(indice, 1)
        return grade

    def _criar_secao_progresso(self) -> QFrame:
        cartao = QFrame()
        cartao.setObjectName("cartaoPadrao")
        self._aplicar_sombra(cartao, blur=24, deslocamento_y=5)

        layout = QVBoxLayout(cartao)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        topo = QHBoxLayout()
        topo.setSpacing(18)
        bloco_texto = QVBoxLayout()
        bloco_texto.setSpacing(6)
        bloco_texto.addWidget(
            self._criar_rotulo(
                "Progresso da automacao",
                18,
                700,
                PALETA_CORES["texto_padrao"],
            )
        )
        self.rotulo_progresso = self._criar_rotulo(
            "Aguardando inicio da automacao",
            13,
            400,
            PALETA_CORES["texto_mutado"],
        )
        self.rotulo_progresso.setWordWrap(True)
        bloco_texto.addWidget(self.rotulo_progresso)
        topo.addLayout(bloco_texto)
        topo.addStretch(1)

        self.rotulo_percentual = QLabel("0%")
        self.rotulo_percentual.setObjectName("rotuloPercentual")
        topo.addWidget(self.rotulo_percentual)

        self.barra_progresso = QProgressBar()
        self.barra_progresso.setObjectName("barraProgresso")
        self.barra_progresso.setRange(0, 100)
        self.barra_progresso.setValue(0)
        self.barra_progresso.setTextVisible(False)
        self.barra_progresso.setFixedHeight(14)

        layout.addLayout(topo)
        layout.addWidget(self.barra_progresso)
        return cartao

    def _criar_secao_logs(self) -> QFrame:
        cartao = QFrame()
        cartao.setObjectName("cartaoPadrao")
        cartao.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._aplicar_sombra(cartao, blur=24, deslocamento_y=5)

        layout = QVBoxLayout(cartao)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)

        cabecalho = QHBoxLayout()
        cabecalho.setSpacing(18)
        bloco_titulos = QVBoxLayout()
        bloco_titulos.setSpacing(6)
        bloco_titulos.addWidget(
            self._criar_rotulo(
                "Historico de execucao",
                18,
                700,
                PALETA_CORES["texto_padrao"],
            )
        )
        subtitulo = self._criar_rotulo(
            "Eventos operacionais, erros e reprocessamentos organizados em uma grade de leitura continua.",
            13,
            400,
            PALETA_CORES["texto_mutado"],
        )
        subtitulo.setWordWrap(True)
        bloco_titulos.addWidget(subtitulo)
        cabecalho.addLayout(bloco_titulos, 1)
        layout.addLayout(cabecalho)

        resumo_logs = QHBoxLayout()
        resumo_logs.setSpacing(12)
        cartao_eventos, self.rotulo_total_logs, self.rotulo_total_logs_detalhe = (
            self._criar_cartao_resumo_log("Eventos", "0", "linhas registradas")
        )
        cartao_reprocessar, self.rotulo_reprocessaveis, self.rotulo_reprocessaveis_detalhe = (
            self._criar_cartao_resumo_log(
                "Reprocessaveis",
                "0",
                "falhas elegiveis para nova tentativa",
            )
        )
        cartao_ultimo_evento, self.rotulo_ultimo_evento, self.rotulo_ultimo_evento_detalhe = (
            self._criar_cartao_resumo_log("Ultimo evento", "Aguardando", "sem atividade")
        )
        resumo_logs.addWidget(cartao_eventos)
        resumo_logs.addWidget(cartao_reprocessar)
        resumo_logs.addWidget(cartao_ultimo_evento)
        layout.addLayout(resumo_logs)

        container_tabela = QFrame()
        container_tabela.setObjectName("containerTabelaLogs")
        container_tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.container_tabela_logs = container_tabela
        container_layout = QVBoxLayout(container_tabela)
        container_layout.setContentsMargins(8, 8, 8, 8)

        self.tabela_logs = QTableWidget(0, 6)
        self.tabela_logs.setObjectName("tabelaLogs")
        self.tabela_logs.setHorizontalHeaderLabels(
            ["Linha", "Cliente", "Status", "Detalhe", "Horario", "Acao"]
        )
        self.tabela_logs.setShowGrid(False)
        self.tabela_logs.setAlternatingRowColors(False)
        self.tabela_logs.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela_logs.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_logs.setFocusPolicy(Qt.NoFocus)
        self.tabela_logs.setWordWrap(False)
        self.tabela_logs.setTextElideMode(Qt.ElideRight)
        self.tabela_logs.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabela_logs.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tabela_logs.verticalHeader().setVisible(False)
        self.tabela_logs.verticalHeader().setDefaultSectionSize(ALTURA_LINHA_LOG)
        self.tabela_logs.verticalScrollBar().setSingleStep(24)
        self.tabela_logs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        cabecalho_tabela = self.tabela_logs.horizontalHeader()
        cabecalho_tabela.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cabecalho_tabela.setHighlightSections(False)
        cabecalho_tabela.setFixedHeight(44)
        cabecalho_tabela.setSectionResizeMode(0, QHeaderView.Fixed)
        cabecalho_tabela.setSectionResizeMode(1, QHeaderView.Fixed)
        cabecalho_tabela.setSectionResizeMode(2, QHeaderView.Fixed)
        cabecalho_tabela.setSectionResizeMode(3, QHeaderView.Stretch)
        cabecalho_tabela.setSectionResizeMode(4, QHeaderView.Fixed)
        cabecalho_tabela.setSectionResizeMode(5, QHeaderView.Fixed)
        self.tabela_logs.setColumnWidth(0, LARGURA_COLUNA_LOG_LINHA)
        self.tabela_logs.setColumnWidth(1, LARGURA_COLUNA_LOG_CLIENTE)
        self.tabela_logs.setColumnWidth(2, LARGURA_COLUNA_LOG_STATUS)
        self.tabela_logs.setColumnWidth(4, LARGURA_COLUNA_LOG_HORARIO)
        self.tabela_logs.setColumnWidth(5, LARGURA_COLUNA_LOG_ACAO)
        self._ajustar_altura_tabela_logs()
        container_layout.addWidget(self.tabela_logs)
        layout.addWidget(container_tabela)

        paginacao = QHBoxLayout()
        paginacao.setSpacing(10)
        self.rotulo_contagem_logs = QLabel("Mostrando 0-0 de 0 registros")
        self.rotulo_contagem_logs.setObjectName("rotuloPaginacaoLogs")
        paginacao.addWidget(self.rotulo_contagem_logs)
        paginacao.addStretch(1)

        self.botao_pagina_anterior_logs = QPushButton("<")
        self.botao_pagina_anterior_logs.setObjectName("botaoPaginacao")
        self.botao_pagina_anterior_logs.setCursor(Qt.PointingHandCursor)
        self.botao_pagina_anterior_logs.clicked.connect(
            self._ir_para_pagina_logs_anterior
        )
        paginacao.addWidget(self.botao_pagina_anterior_logs)

        self.rotulo_pagina_logs = QLabel("Pagina 1 de 1")
        self.rotulo_pagina_logs.setObjectName("rotuloPaginacaoLogs")
        paginacao.addWidget(self.rotulo_pagina_logs)

        self.botao_pagina_seguinte_logs = QPushButton(">")
        self.botao_pagina_seguinte_logs.setObjectName("botaoPaginacao")
        self.botao_pagina_seguinte_logs.setCursor(Qt.PointingHandCursor)
        self.botao_pagina_seguinte_logs.clicked.connect(
            self._ir_para_pagina_logs_seguinte
        )
        paginacao.addWidget(self.botao_pagina_seguinte_logs)

        layout.addLayout(paginacao)
        return cartao

    def _criar_rodape(self) -> QFrame:
        rodape = QFrame()
        rodape.setObjectName("rodapePainel")

        layout = QHBoxLayout(rodape)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(16)

        bloco_esquerdo = QVBoxLayout()
        bloco_esquerdo.setSpacing(4)
        bloco_esquerdo.addWidget(
            self._criar_rotulo(
                "RPA REAJUSTE TABELAS VIGENCIA",
                12,
                700,
                PALETA_CORES["texto_padrao"],
            )
        )
        bloco_esquerdo.addWidget(
            self._criar_rotulo(
                "Automacao desktop para copia, vigencia e reajuste de tabelas.",
                12,
                400,
                PALETA_CORES["texto_mutado"],
            )
        )
        layout.addLayout(bloco_esquerdo, 1)

        bloco_direito = QVBoxLayout()
        bloco_direito.setSpacing(4)
        autoria = QLabel(
            '<a href="https://www.linkedin.com/in/dev-lucasandrade/">Desenvolvido por @valentelucass</a>'
        )
        self._aplicar_fonte_e_cor(autoria, 12, 600, PALETA_CORES["primaria"])
        autoria.setOpenExternalLinks(True)
        autoria.setTextFormat(Qt.RichText)
        autoria.setTextInteractionFlags(Qt.TextBrowserInteraction)
        bloco_direito.addWidget(autoria, alignment=Qt.AlignRight)
        bloco_direito.addWidget(
            self._criar_rotulo(
                "Suporte: lucasmac.dev@gmail.com",
                12,
                400,
                PALETA_CORES["texto_mutado"],
            ),
            alignment=Qt.AlignRight,
        )
        layout.addLayout(bloco_direito)
        return rodape

    def _criar_cartao_resumo_log(
        self,
        titulo: str,
        valor: str,
        detalhe: str,
    ) -> tuple[QFrame, QLabel, QLabel]:
        cartao = QFrame()
        cartao.setObjectName("resumoLogCard")
        cartao.setMinimumWidth(180)
        cartao.setMinimumHeight(96)

        layout = QVBoxLayout(cartao)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        rotulo_titulo = self._criar_rotulo(
            titulo,
            11,
            700,
            PALETA_CORES["texto_mutado"],
        )
        rotulo_valor = self._criar_rotulo(
            valor,
            20,
            800,
            PALETA_CORES["texto_padrao"],
        )
        rotulo_valor.setMinimumHeight(30)
        rotulo_valor.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        rotulo_detalhe = self._criar_rotulo(
            detalhe,
            11,
            400,
            PALETA_CORES["texto_sutil"],
        )
        rotulo_detalhe.setWordWrap(True)

        layout.addWidget(rotulo_titulo)
        layout.addWidget(rotulo_valor)
        layout.addWidget(rotulo_detalhe)
        return cartao, rotulo_valor, rotulo_detalhe

    def iniciar_automacao(self) -> None:
        if self.trabalhador_atual and self.trabalhador_atual.isRunning():
            return

        try:
            valor_reajuste = float(
                self.input_valor_reajuste.text().strip().replace(",", ".")
            )
        except ValueError:
            QMessageBox.warning(
                self,
                "Valor invalido",
                "O valor do reajuste deve ser numerico. Exemplo: 15 ou 27.5",
            )
            return

        contexto_execucao = self._coletar_contexto_execucao()
        if not contexto_execucao:
            return

        self.ultimo_contexto_execucao = contexto_execucao
        self._iniciar_trabalhador(
            contexto_execucao=contexto_execucao,
            modo_execucao="completa",
            valor_reajuste=valor_reajuste,
        )

    def parar_automacao(self) -> None:
        if self.trabalhador_atual and self.trabalhador_atual.isRunning():
            self.trabalhador_atual.solicitar_parada()

    def reprocessar_registro(self, contexto_registro: dict) -> None:
        if self.trabalhador_atual and self.trabalhador_atual.isRunning():
            QMessageBox.warning(
                self,
                "Execucao em andamento",
                "Aguarde a execucao atual terminar antes de reprocessar um item.",
            )
            return

        if not self.ultimo_contexto_execucao:
            QMessageBox.warning(
                self,
                "Contexto indisponivel",
                "Nao existe uma execucao anterior registrada para reprocessar.",
            )
            return

        try:
            valor_reajuste = float(
                self.input_valor_reajuste.text().strip().replace(",", ".")
            )
        except ValueError:
            QMessageBox.warning(
                self,
                "Valor invalido",
                "O valor do reajuste deve ser numerico. Exemplo: 15 ou 27.5",
            )
            return

        self._iniciar_trabalhador(
            contexto_execucao=self.ultimo_contexto_execucao,
            modo_execucao="reprocessamento",
            contexto_reprocessamento=contexto_registro,
            valor_reajuste=valor_reajuste,
        )

    def _iniciar_trabalhador(
        self,
        *,
        contexto_execucao: dict,
        modo_execucao: str,
        valor_reajuste: float,
        contexto_reprocessamento: dict | None = None,
    ) -> None:
        self.trabalhador_atual = TrabalhadorExecucaoRpa(
            valor_reajuste=valor_reajuste,
            contexto_execucao=contexto_execucao,
            modo_execucao=modo_execucao,
            contexto_reprocessamento=contexto_reprocessamento,
            parent=self,
        )
        self.trabalhador_atual.painel_limpo.connect(self.limpar_painel)
        self.trabalhador_atual.status_alterado.connect(self._atualizar_status_robo)
        self.trabalhador_atual.estatisticas_atualizadas.connect(
            self._atualizar_estatisticas
        )
        self.trabalhador_atual.progresso_atualizado.connect(self._atualizar_progresso)
        self.trabalhador_atual.registro_log_adicionado.connect(
            self._adicionar_registro_log
        )
        self.trabalhador_atual.erro_fatal.connect(self._tratar_erro_fatal)
        self.trabalhador_atual.execucao_encerrada.connect(self._ao_encerrar_execucao)
        self.trabalhador_atual.finished.connect(self._ao_finalizar_thread)

        self.botao_iniciar.setEnabled(False)
        self.botao_parar.setEnabled(True)
        self._habilitar_botoes_reprocessar(False)
        self.trabalhador_atual.start()

    def limpar_painel(self) -> None:
        self.registros_logs.clear()
        self.total_logs = 0
        self.total_logs_reprocessaveis = 0
        self.indice_pagina_logs = 0
        self.tabela_logs.setRowCount(0)
        self._atualizar_estatisticas(
            {"total_registros": 0, "processados": 0, "sucessos": 0, "falhas": 0}
        )
        self._atualizar_progresso({"atual": 0, "total": 0, "percentual": 0})
        self._atualizar_resumo_logs()
        self._renderizar_pagina_logs()

    def _atualizar_status_robo(self, status: str) -> None:
        detalhes = {
            "Parado": (
                "Aguardando nova execucao.",
                "Pronto para iniciar uma nova rodada de processamento.",
            ),
            "Executando": (
                "Robo em atividade.",
                "Acompanhe os eventos na grade abaixo e interrompa se necessario.",
            ),
            "Sucesso": (
                "Execucao concluida com sucesso.",
                "Revise o historico ou inicie uma nova rodada quando necessario.",
            ),
            "Erro": (
                "Execucao encerrada com erro.",
                "Revise o historico antes de iniciar uma nova tentativa.",
            ),
            "Processando": (
                "Processamento em andamento.",
                "O painel esta sincronizando os eventos da execucao atual.",
            ),
        }
        detalhe_status, detalhe_controle = detalhes.get(
            status,
            ("Estado atualizado.", "Painel sincronizado com o andamento atual do robo."),
        )

        self.etiqueta_status.atualizar(status)
        self.rotulo_status_detalhe.setText(detalhe_status)
        self.rotulo_status_horario.setText(
            f"Ultima atualizacao: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.rotulo_contexto_operacao.setText(detalhe_controle)

    def _atualizar_estatisticas(self, dados: dict) -> None:
        self.cartao_total.atualizar_valor(int(dados.get("total_registros", 0) or 0))
        self.cartao_processados.atualizar_valor(int(dados.get("processados", 0) or 0))
        self.cartao_sucessos.atualizar_valor(int(dados.get("sucessos", 0) or 0))
        self.cartao_falhas.atualizar_valor(int(dados.get("falhas", 0) or 0))

    def _atualizar_progresso(self, dados: dict) -> None:
        atual = int(dados.get("atual", 0) or 0)
        total = int(dados.get("total", 0) or 0)
        percentual = int(dados.get("percentual", 0) or 0)
        descricao = str(dados.get("descricao", "")).strip()

        if descricao:
            self.rotulo_progresso.setText(descricao)
        elif total <= 0:
            self.rotulo_progresso.setText("Aguardando inicio da automacao")
        else:
            self.rotulo_progresso.setText(f"{atual} de {total} registros acompanhados")

        self.rotulo_percentual.setText(f"{percentual}%")
        self.barra_progresso.setValue(max(0, min(100, percentual)))

    def _adicionar_registro_log(self, dados: dict) -> None:
        estava_na_ultima_pagina = (
            not self.registros_logs
            or self.indice_pagina_logs >= self._obter_ultima_pagina_logs()
        )
        cliente = str(dados.get("cliente", "-")).strip() or "-"
        status = str(dados.get("status", "")).strip() or "Parado"
        horario = str(dados.get("horario", "")).strip()
        mensagem_original = str(dados.get("mensagem", "")).strip()
        mensagem = self._normalizar_mensagem_log(mensagem_original) or "Evento registrado."

        registro = {
            "id_linha": str(dados.get("id_linha", "-")).strip() or "-",
            "cliente": cliente,
            "status": status,
            "horario": horario,
            "mensagem": mensagem,
            "mensagem_original": mensagem_original or mensagem,
            "pode_reprocessar": bool(dados.get("pode_reprocessar")),
            "contexto": dict(dados),
            "numero_pagina": int(dados.get("numero_pagina", 0) or 0),
            "numero_linha": int(dados.get("numero_linha", 0) or 0),
            "identificador": str(dados.get("identificador", "")).strip(),
            "chave_consolidacao": self._obter_chave_consolidacao_registro(dados),
        }

        indice_existente = self._localizar_indice_registro_existente(
            registro["chave_consolidacao"]
        )
        if indice_existente is None:
            self.registros_logs.append(registro)
            if estava_na_ultima_pagina:
                self.indice_pagina_logs = self._obter_ultima_pagina_logs()
        else:
            self.registros_logs[indice_existente].update(registro)

        self._sincronizar_totais_logs()
        self.indice_pagina_logs = min(
            self.indice_pagina_logs,
            self._obter_ultima_pagina_logs(),
        )
        self._renderizar_pagina_logs()
        self._atualizar_resumo_logs(status=status, horario=horario, mensagem=mensagem)

    def _atualizar_resumo_logs(
        self,
        status: str | None = None,
        horario: str = "",
        mensagem: str = "",
    ) -> None:
        self.rotulo_total_logs.setText(self._formatar_inteiro(self.total_logs))
        self.rotulo_total_logs_detalhe.setText("linhas registradas")
        self.rotulo_reprocessaveis.setText(
            self._formatar_inteiro(self.total_logs_reprocessaveis)
        )
        self.rotulo_reprocessaveis_detalhe.setText(
            "falhas elegiveis para nova tentativa"
        )

        if status is None:
            self.rotulo_ultimo_evento.setText("Aguardando")
            self.rotulo_ultimo_evento_detalhe.setText("sem atividade")
            return

        self.rotulo_ultimo_evento.setText(status)
        if horario or mensagem:
            resumo = self._resumir_texto(mensagem, 52)
            partes = [parte for parte in (horario, resumo) if parte]
            self.rotulo_ultimo_evento_detalhe.setText(" | ".join(partes))
        else:
            self.rotulo_ultimo_evento_detalhe.setText("evento sincronizado")

    def _habilitar_botoes_reprocessar(self, habilitado: bool) -> None:
        self.reprocessamento_habilitado = habilitado
        self._renderizar_pagina_logs()

    def _ao_encerrar_execucao(self, _dados: dict) -> None:
        self.botao_iniciar.setEnabled(True)
        self.botao_parar.setEnabled(False)
        self._habilitar_botoes_reprocessar(True)

    def _ao_finalizar_thread(self) -> None:
        self.trabalhador_atual = None

    def _tratar_erro_fatal(self, mensagem: str) -> None:
        QMessageBox.critical(self, "Erro na automacao", mensagem)

    def _setar_item_texto(
        self,
        linha: int,
        coluna: int,
        texto: str,
        alinhamento: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter,
        cor: str | None = None,
        fonte: QFont | None = None,
        destaque: bool = False,
        dica: str | None = None,
    ) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alinhamento)
        item.setToolTip(dica or texto)
        if cor:
            item.setForeground(QBrush(QColor(cor)))
        if fonte is not None:
            item.setFont(fonte)
        if destaque:
            fonte_item = item.font()
            fonte_item.setBold(True)
            item.setFont(fonte_item)
        if coluna == 3:
            metricas = QFontMetrics(item.font())
            item.setText(metricas.elidedText(texto, Qt.ElideRight, 360))
        self.tabela_logs.setItem(linha, coluna, item)

    def _criar_widget_status_tabela(self, status: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cor_fundo, cor_texto, cor_borda = EtiquetaStatus.MAPA_CORES_STATUS.get(
            status,
            ("#F8FAFC", PALETA_CORES["texto_padrao"], PALETA_CORES["borda"]),
        )

        badge = QFrame()
        badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        badge.setMinimumWidth(LARGURA_COLUNA_LOG_STATUS - 18)
        badge.setStyleSheet(
            f"""
            QFrame {{
                background-color: {cor_fundo};
                border: 1px solid {cor_borda};
                border-radius: 11px;
            }}
            """
        )
        layout_badge = QHBoxLayout(badge)
        layout_badge.setContentsMargins(12, 6, 12, 6)
        layout_badge.setSpacing(7)

        marcador = QFrame()
        marcador.setFixedSize(8, 8)
        marcador.setStyleSheet(
            f"background-color: {cor_texto}; border: none; border-radius: 4px;"
        )
        rotulo = QLabel(status)
        self._aplicar_fonte_e_cor(rotulo, 11, 700, cor_texto)

        layout_badge.addWidget(marcador, alignment=Qt.AlignVCenter)
        layout_badge.addWidget(rotulo, alignment=Qt.AlignVCenter)
        layout.addWidget(badge)
        return container

    def _criar_widget_acao_tabela(self, botao: QPushButton) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(botao)
        return container

    def _renderizar_pagina_logs(self) -> None:
        self.tabela_logs.setRowCount(0)
        for linha, registro in enumerate(self._obter_registros_pagina_logs()):
            self.tabela_logs.insertRow(linha)
            self._setar_item_texto(
                linha,
                0,
                registro["id_linha"],
                cor=PALETA_CORES["texto_mutado"],
                fonte=self.fonte_mono,
            )
            self._setar_item_texto(
                linha,
                1,
                registro["cliente"],
                cor=(
                    PALETA_CORES["primaria"]
                    if registro["cliente"].lower() == "sistema"
                    else PALETA_CORES["texto_padrao"]
                ),
                destaque=registro["cliente"].lower() == "sistema",
            )
            self.tabela_logs.setCellWidget(
                linha,
                2,
                self._criar_widget_status_tabela(registro["status"]),
            )
            self._setar_item_texto(
                linha,
                3,
                registro["mensagem"],
                cor=PALETA_CORES["texto_padrao"],
                dica=registro["mensagem_original"],
            )
            self._setar_item_texto(
                linha,
                4,
                registro["horario"],
                cor=PALETA_CORES["texto_mutado"],
                fonte=self.fonte_mono,
            )

            if registro["pode_reprocessar"]:
                botao = QPushButton("Reprocessar")
                botao.setObjectName("botaoTabela")
                botao.setCursor(Qt.PointingHandCursor)
                botao.setMinimumHeight(34)
                botao.setMinimumWidth(LARGURA_COLUNA_LOG_ACAO - 22)
                botao.setEnabled(self.reprocessamento_habilitado)
                botao.clicked.connect(
                    partial(self.reprocessar_registro, registro["contexto"])
                )
                self.tabela_logs.setCellWidget(
                    linha,
                    5,
                    self._criar_widget_acao_tabela(botao),
                )
            else:
                self._setar_item_texto(
                    linha,
                    5,
                    "",
                    alinhamento=Qt.AlignRight | Qt.AlignVCenter,
                    cor=PALETA_CORES["texto_sutil"],
                )

            self.tabela_logs.setRowHeight(linha, ALTURA_LINHA_LOG)
        self._atualizar_controles_paginacao_logs()

    def _obter_registros_pagina_logs(self) -> list[dict]:
        if not self.registros_logs:
            return []
        inicio = self.indice_pagina_logs * self.linhas_por_pagina_logs
        fim = inicio + self.linhas_por_pagina_logs
        return self.registros_logs[inicio:fim]

    def _obter_total_paginas_logs(self) -> int:
        if not self.registros_logs:
            return 1
        return (
            len(self.registros_logs) + self.linhas_por_pagina_logs - 1
        ) // self.linhas_por_pagina_logs

    def _obter_ultima_pagina_logs(self) -> int:
        return self._obter_total_paginas_logs() - 1

    def _obter_chave_consolidacao_registro(
        self,
        dados: dict,
    ) -> tuple[str, str, int, int] | None:
        cliente = str(dados.get("cliente", "-")).strip().lower()
        identificador = str(dados.get("identificador", "")).strip()
        if not identificador or cliente == "sistema" or identificador.lower() == "sistema":
            return None
        return (
            str(dados.get("id_linha", "-")).strip() or "-",
            identificador,
            int(dados.get("numero_pagina", 0) or 0),
            int(dados.get("numero_linha", 0) or 0),
        )

    def _localizar_indice_registro_existente(
        self,
        chave_consolidacao: tuple[str, str, int, int] | None,
    ) -> int | None:
        if chave_consolidacao is None:
            return None
        for indice, registro in enumerate(self.registros_logs):
            if registro.get("chave_consolidacao") == chave_consolidacao:
                return indice
        return None

    def _sincronizar_totais_logs(self) -> None:
        self.total_logs = len(self.registros_logs)
        self.total_logs_reprocessaveis = sum(
            1 for registro in self.registros_logs if registro["pode_reprocessar"]
        )

    def _atualizar_controles_paginacao_logs(self) -> None:
        total_registros = len(self.registros_logs)
        total_paginas = self._obter_total_paginas_logs()
        self.indice_pagina_logs = min(
            self.indice_pagina_logs,
            self._obter_ultima_pagina_logs(),
        )

        if total_registros == 0:
            self.rotulo_contagem_logs.setText("Mostrando 0-0 de 0 registros")
        else:
            inicio = (self.indice_pagina_logs * self.linhas_por_pagina_logs) + 1
            fim = min(inicio + self.linhas_por_pagina_logs - 1, total_registros)
            self.rotulo_contagem_logs.setText(
                f"Mostrando {inicio}-{fim} de {total_registros} registros"
            )

        self.rotulo_pagina_logs.setText(
            f"Pagina {self.indice_pagina_logs + 1} de {total_paginas}"
        )
        mostrar_navegacao = total_paginas > 1
        self.botao_pagina_anterior_logs.setVisible(mostrar_navegacao)
        self.botao_pagina_seguinte_logs.setVisible(mostrar_navegacao)
        self.rotulo_pagina_logs.setVisible(mostrar_navegacao)
        self.botao_pagina_anterior_logs.setEnabled(self.indice_pagina_logs > 0)
        self.botao_pagina_seguinte_logs.setEnabled(
            self.indice_pagina_logs < self._obter_ultima_pagina_logs()
        )

    def _ir_para_pagina_logs_anterior(self) -> None:
        if self.indice_pagina_logs <= 0:
            return
        self.indice_pagina_logs -= 1
        self._renderizar_pagina_logs()

    def _ir_para_pagina_logs_seguinte(self) -> None:
        if self.indice_pagina_logs >= self._obter_ultima_pagina_logs():
            return
        self.indice_pagina_logs += 1
        self._renderizar_pagina_logs()

    def _ajustar_altura_tabela_logs(self) -> None:
        altura_tabela = (
            ALTURA_CABECALHO_TABELA_LOG
            + (self.linhas_por_pagina_logs * ALTURA_LINHA_LOG)
            + 4
        )
        self.tabela_logs.setFixedHeight(altura_tabela)
        self.container_tabela_logs.setMinimumHeight(altura_tabela + 16)
        self.container_tabela_logs.setMaximumHeight(altura_tabela + 16)

    def _coletar_contexto_execucao(self) -> dict | None:
        caminho_pdf, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo PDF",
            str(Path.home() / "Downloads"),
            "Arquivos PDF (*.pdf)",
        )
        if not caminho_pdf:
            return None

        try:
            mes_padrao, ano_padrao = extrair_mes_ano_do_pdf(caminho_pdf)
        except Exception:
            agora = datetime.now()
            mes_padrao = agora.month
            ano_padrao = agora.year

        valor_filial, confirmado = QInputDialog.getItem(
            self,
            "Filial ou CNPJ",
            "Selecione a filial cadastrada ou digite o CNPJ:",
            self.filiais_manager.obter_opcoes_combo(),
            0,
            True,
        )
        if not confirmado:
            return None

        cnpj = self._resolver_cnpj_execucao(valor_filial)
        if not cnpj:
            QMessageBox.warning(
                self,
                "CNPJ invalido",
                "Informe um CNPJ com 14 digitos ou selecione uma filial valida.",
            )
            return None

        opcoes_mes = [
            f"{indice:02d} - {sigla}" for indice, sigla in MESES_ALFANUMERICOS.items()
        ]
        valor_mes, confirmado = QInputDialog.getItem(
            self,
            "Mes de referencia",
            "Selecione o mes de referencia:",
            opcoes_mes,
            max(0, mes_padrao - 1),
            False,
        )
        if not confirmado:
            return None

        ano, confirmado = QInputDialog.getInt(
            self,
            "Ano de referencia",
            "Informe o ano de referencia:",
            int(ano_padrao),
            2000,
            2100,
        )
        if not confirmado:
            return None

        return {
            "pdf": caminho_pdf,
            "cnpj": cnpj,
            "mes": int(valor_mes.split(" - ", 1)[0]),
            "ano": int(ano),
        }

    def _resolver_cnpj_execucao(self, valor: str) -> str | None:
        texto = str(valor or "").strip()
        if not texto:
            return None
        if " - " in texto:
            cnpj = texto.rsplit(" - ", 1)[-1]
        else:
            digitos = "".join(ch for ch in texto if ch.isdigit())
            if len(digitos) == 14:
                cnpj = digitos
            else:
                encontrados = self.filiais_manager.buscar_por_nome(texto)
                if len(encontrados) != 1:
                    return None
                cnpj = encontrados[0][0]
        cnpj_limpo = "".join(ch for ch in cnpj if ch.isdigit())
        return cnpj_limpo if len(cnpj_limpo) == 14 else None

    def _aplicar_estilo_global(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow,
            QWidget#widgetCentral {{
                background: {PALETA_CORES['fundo']};
            }}
            QScrollArea#scrollPrincipal {{
                background: {PALETA_CORES['fundo']};
                border: none;
            }}
            QScrollArea#scrollPrincipal > QWidget > QWidget {{
                background: {PALETA_CORES['fundo']};
            }}
            QFrame#cabecalhoPainel {{
                background: {PALETA_CORES['branco']};
                border: 1px solid {PALETA_CORES['borda']};
                border-radius: 24px;
            }}
            QFrame#cabecalhoStatus {{
                background: {PALETA_CORES['superficie_secundaria']};
                border: 1px solid {PALETA_CORES['borda_forte']};
                border-radius: 20px;
            }}
            QLabel#etiquetaTopo {{
                background: #EAF2FC;
                color: {PALETA_CORES['primaria']};
                border-radius: 11px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.4px;
            }}
            QLabel#logoFallback {{
                color: {PALETA_CORES['primaria']};
                font-size: 24px;
                font-weight: 800;
            }}
            QLabel#rotuloPercentual {{
                color: {PALETA_CORES['primaria']};
                font-size: 28px;
                font-weight: 800;
            }}
            QFrame#cartaoPadrao,
            QFrame#cartaoEstatistica,
            QFrame#resumoLogCard,
            QFrame#containerTabelaLogs {{
                background: {PALETA_CORES['branco']};
                border: 1px solid {PALETA_CORES['borda']};
                border-radius: 20px;
            }}
            QFrame#rodapePainel {{
                background: transparent;
                border: none;
            }}
            QPushButton#botaoPrimario {{
                background: {PALETA_CORES['primaria']};
                color: white;
                border: none;
                border-radius: 14px;
                padding: 13px 20px;
                font-weight: 700;
                min-width: 168px;
            }}
            QPushButton#botaoPrimario:hover {{ background: #1A3970; }}
            QPushButton#botaoPrimario:pressed {{ background: #15315E; }}
            QPushButton#botaoPerigo {{
                background: white;
                color: {PALETA_CORES['perigo']};
                border: 1px solid #E4BDB8;
                border-radius: 14px;
                padding: 13px 20px;
                font-weight: 700;
                min-width: 168px;
            }}
            QPushButton#botaoPerigo:hover {{ background: #FFF7F5; }}
            QPushButton#botaoSecundario {{
                background: white;
                color: {PALETA_CORES['primaria']};
                border: 1px solid {PALETA_CORES['borda_forte']};
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 700;
                min-width: 148px;
            }}
            QPushButton#botaoSecundario:hover {{ background: #F8FBFF; }}
            QPushButton#botaoPaginacao {{
                background: white;
                color: {PALETA_CORES['primaria']};
                border: 1px solid {PALETA_CORES['borda_forte']};
                border-radius: 10px;
                min-width: 38px;
                max-width: 38px;
                min-height: 34px;
                max-height: 34px;
                font-weight: 800;
            }}
            QPushButton#botaoPaginacao:hover {{ background: #F8FBFF; }}
            QPushButton#botaoTabela {{
                background: #EFF5FD;
                color: {PALETA_CORES['primaria']};
                border: 1px solid {PALETA_CORES['borda_forte']};
                border-radius: 10px;
                padding: 8px 12px;
                font-weight: 700;
            }}
            QPushButton#botaoTabela:hover {{ background: #E4EEFA; }}
            QPushButton#botaoTabela:disabled {{
                background: #F1F5F9;
                color: #94A3B8;
                border-color: #E2E8F0;
            }}
            QPushButton:disabled {{
                background: #E2E8F0;
                color: #94A3B8;
                border-color: #E2E8F0;
            }}
            QLineEdit {{
                background-color: {PALETA_CORES['branco']};
                border: 1px solid {PALETA_CORES['borda']};
                border-radius: 8px;
                padding: 0 12px;
                font-size: 14px;
                font-weight: 600;
                color: {PALETA_CORES['texto_padrao']};
            }}
            QLineEdit:focus {{ border-color: {PALETA_CORES['primaria']}; }}
            QLabel#rotuloPaginacaoLogs {{
                color: {PALETA_CORES['texto_mutado']};
                font-size: 12px;
                font-weight: 600;
            }}
            QTableWidget#tabelaLogs {{
                background: white;
                border: none;
                outline: none;
                gridline-color: transparent;
                color: {PALETA_CORES['texto_padrao']};
            }}
            QTableWidget#tabelaLogs::item {{
                border-bottom: 1px solid #E6EDF5;
                padding: 6px 8px;
            }}
            QTableWidget#tabelaLogs::item:selected {{
                background: #EEF4FB;
                color: {PALETA_CORES['texto_padrao']};
            }}
            QHeaderView::section {{
                background: #F6F9FC;
                color: #52627A;
                border: none;
                border-bottom: 1px solid {PALETA_CORES['borda']};
                padding: 12px 14px;
                font-size: 12px;
                font-weight: 700;
            }}
            QProgressBar#barraProgresso {{
                border: none;
                border-radius: 7px;
                background: #E2E8F0;
            }}
            QProgressBar#barraProgresso::chunk {{
                border-radius: 7px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PALETA_CORES['primaria']},
                    stop:1 {PALETA_CORES['secundaria']}
                );
            }}
            QScrollBar:vertical {{
                background: #EEF3F8;
                width: 14px;
                margin: 6px 2px 6px 2px;
                border: 1px solid #D9E4EF;
                border-radius: 7px;
            }}
            QScrollBar::handle:vertical {{
                background: #8FA6BE;
                border: 1px solid #7D95AE;
                border-radius: 6px;
                min-height: 42px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #6F87A2;
                border-color: #617996;
            }}
            QScrollBar::handle:vertical:pressed {{
                background: #5E7690;
                border-color: #516880;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
                border: none;
                height: 0px;
            }}
            """
        )

    def _aplicar_sombra(
        self,
        widget: QWidget,
        blur: int = 32,
        deslocamento_y: int = 8,
    ) -> None:
        sombra = QGraphicsDropShadowEffect(self)
        sombra.setBlurRadius(blur)
        sombra.setOffset(0, deslocamento_y)
        sombra.setColor(QColor(15, 23, 42, 24))
        widget.setGraphicsEffect(sombra)

    def _configurar_icone_janela(self) -> None:
        caminho_icone = Path(__file__).resolve().parents[2] / "public" / "icon.ico"
        if caminho_icone.exists():
            self.setWindowIcon(QIcon(str(caminho_icone)))

    def _obter_logo_empresa(self) -> QPixmap | None:
        caminho_logo = Path(__file__).resolve().parents[2] / "public" / "logo.png"
        if not caminho_logo.exists():
            return None
        pixmap = QPixmap(str(caminho_logo))
        if pixmap.isNull():
            return None
        return pixmap

    @staticmethod
    def _normalizar_mensagem_log(mensagem: str) -> str:
        return " ".join(mensagem.split())

    @staticmethod
    def _resumir_texto(texto: str, limite: int) -> str:
        if len(texto) <= limite:
            return texto
        return f"{texto[: limite - 3].rstrip()}..."

    @staticmethod
    def _formatar_inteiro(valor: int) -> str:
        return f"{valor:,}".replace(",", ".")
