# Implementação: Tema Claro/Escuro com PySide6

Este documento descreve o padrão adotado neste projeto para alternar entre tema claro e escuro em interfaces PySide6 (Qt). Qualquer RPA Python que use PySide6 pode seguir estes passos.

---

## 1. Estrutura geral da solução

A solução é composta por quatro partes independentes:

1. **Dicionários de paleta** — dois dicts Python definem todas as cores dos dois temas
2. **QSS gerado dinamicamente** — a string de stylesheet é montada a partir do dicionário ativo
3. **Persistência via QSettings** — a preferência do usuário sobrevive ao fechar o app
4. **Botão de alternância na interface** — um botão no cabeçalho troca o tema; o texto do botão indica o tema para o qual vai alternar ("Escuro" / "Claro")

---

## 2. Dicionários de paleta

### Princípio

Cada paleta é um `dict[str, str]` onde cada chave é um token semântico (ex: `"fundo"`, `"texto_padrao"`, `"borda"`) e o valor é um hex de cor. O código de layout nunca usa valores de cor fixos — ele sempre referencia as chaves do dicionário ativo.

### Exemplo de declaração

```python
PALETA_CLARA: dict[str, str] = {
    "primaria":              "#21478A",
    "fundo":                 "#F3F7FB",
    "branco":                "#FFFFFF",
    "texto_padrao":          "#0F172A",
    "texto_mutado":          "#64748B",
    "texto_sutil":           "#94A3B8",
    "borda":                 "#D0E2EF",
    "borda_forte":           "#9BBDD4",
    "superficie_secundaria": "#F7FAFD",
    "btn_pri_bg":            "#21478A",
    "btn_pri_hover":         "#1A3970",
    "btn_pri_text":          "#FFFFFF",
    "input_bg":              "#FFFFFF",
    "input_border":          "#7AADC9",
}

PALETA_ESCURA: dict[str, str] = {
    "primaria":              "#3B82F6",
    "fundo":                 "#0B1120",
    "branco":                "#111827",
    "texto_padrao":          "#E5E7EB",
    "texto_mutado":          "#9CA3AF",
    "texto_sutil":           "#94A3B8",   # não use #6B7280 — muito escuro
    "borda":                 "#1F2937",
    "borda_forte":           "#374151",
    "superficie_secundaria": "#1A2236",
    "btn_pri_bg":            "#3B82F6",
    "btn_pri_hover":         "#2563EB",
    "btn_pri_text":          "#FFFFFF",
    "input_bg":              "#1F2937",
    "input_border":          "#374151",
}
```

### Tokens obrigatórios vs opcionais

Inclua no mínimo: `fundo`, `branco`, `texto_padrao`, `borda`. Os demais tokens são acrescentados conforme os componentes da interface precisarem.

---

## 3. QSS gerado dinamicamente

### Princípio

Em vez de um arquivo `.qss` fixo, a stylesheet é uma f-string Python que interpola os valores da paleta. Chamar `app_ou_janela.setStyleSheet(qss)` novamente com outra paleta já troca o tema inteiro da janela.

### Estrutura

```python
def _gerar_qss(p: dict[str, str]) -> str:
    return f"""
        QMainWindow, QWidget#conteudoCentral {{
            background-color: {p['fundo']};
        }}
        QFrame#cartaoPadrao {{
            background-color: {p['branco']};
            border: 1px solid {p['borda']};
            border-radius: 12px;
        }}
        QLabel {{
            color: {p['texto_padrao']};
            background: transparent;
        }}
        QLabel#labelMutado {{
            color: {p['texto_mutado']};
        }}
        QPushButton#botaoPrimario {{
            background-color: {p['btn_pri_bg']};
            color: {p['btn_pri_text']};
            border: none;
            border-radius: 8px;
            padding: 8px 20px;
            font-weight: 700;
        }}
        QPushButton#botaoPrimario:hover {{
            background-color: {p['btn_pri_hover']};
        }}
        QLineEdit, QComboBox {{
            background-color: {p['input_bg']};
            color: {p['texto_padrao']};
            border: 1px solid {p['input_border']};
            border-radius: 6px;
            padding: 6px 10px;
        }}
    """

def _aplicar_estilo_global(self, paleta: dict[str, str]) -> None:
    self.setStyleSheet(_gerar_qss(paleta))
```

### Por que usar objectName nos seletores

`QLabel { ... }` afeta todos os QLabel da janela. `QLabel#meuLabel { ... }` afeta apenas o widget com `setObjectName("meuLabel")` e tem maior especificidade. Use objectName em widgets que precisam de estilo específico (badges, títulos, rodapés).

---

## 4. Persistência via QSettings

```python
from PySide6.QtCore import QSettings

CFG_ORG  = "sua_empresa"
CFG_APP  = "NomeDoApp"
CFG_CHAVE = "theme"

def _carregar_tema_salvo(self) -> None:
    cfg = QSettings(CFG_ORG, CFG_APP)
    tema = cfg.value(CFG_CHAVE, "claro")   # padrão: claro
    if tema == "escuro":
        self._aplicar_tema("escuro")

def _alternar_tema(self) -> None:
    novo = "escuro" if self._tema_atual == "claro" else "claro"
    self._aplicar_tema(novo)
    cfg = QSettings(CFG_ORG, CFG_APP)
    cfg.setValue(CFG_CHAVE, novo)
```

`QSettings` salva no registro do Windows (em produção) ou em arquivo INI. Não requer nenhuma dependência extra.

---

## 5. Método central de troca de tema

```python
def _aplicar_tema(self, tema: str) -> None:
    self._tema_atual = tema
    paleta = PALETA_ESCURA if tema == "escuro" else PALETA_CLARA

    # 1. Re-aplica o QSS inteiro da janela
    self._aplicar_estilo_global(paleta)

    # 2. Atualiza o texto do botão de alternância
    self.btn_tema.setText("Claro" if tema == "escuro" else "Escuro")

    # 3. Atualiza elementos com estilo inline (divisores, badges, etc.)
    self._header_divisor.setStyleSheet(
        f"background: {paleta['borda_forte']}; border: none;"
    )

    # 4. Atualiza o logo (ver seção 7)
    self._atualizar_logo_tema(tema)

    # 5. Atualiza cores dos logs (ver seção 8)
    if self._log_mgr:
        self._log_mgr.atualizar_cores_tema(tema)
```

Chamar `_aplicar_tema` uma única vez atualiza toda a interface.

---

## 6. Botão de alternância

```python
self.btn_tema = QPushButton("☀")
self.btn_tema.setObjectName("botaoTema")
self.btn_tema.setFixedSize(36, 36)   # quadrado para garantir círculo perfeito
self.btn_tema.setCursor(Qt.PointingHandCursor)
self.btn_tema.setToolTip("Alternar tema claro/escuro")
self.btn_tema.clicked.connect(self._alternar_tema)
```

O ícone do botão indica o tema atual:
- Tema claro ativo → botão mostra **☀**
- Tema escuro ativo → botão mostra **☀** (mesmo ícone, estilo muda pelo tema)

O botão é um círculo perfeito: `setFixedSize(36, 36)` + `border-radius: 18px` no QSS. Use apenas o caractere ☀ (U+2600) — ele renderiza como texto em todos os sistemas, sem dependência de emoji colorido.

---

## 7. Logo com inversão no tema escuro

Logos escuros ficam invisíveis sobre fundo escuro. A solução é criar uma silhueta branca preservando o canal alpha — equivalente ao filtro CSS `brightness(0) invert(1)`.

```python
def _atualizar_logo_tema(self, tema: str) -> None:
    if self._logo_pixmap_original is None or self._logo_pixmap_original.isNull():
        return

    from PySide6.QtGui import QPainter

    px = self._logo_pixmap_original
    if tema == "escuro":
        # Converte para silhueta branca mantendo transparência original
        orig = px.toImage().convertToFormat(QImage.Format_ARGB32)
        branco = QImage(orig.size(), QImage.Format_ARGB32)
        branco.fill(0)                           # começa transparente
        p = QPainter(branco)
        p.fillRect(branco.rect(), QColor(255, 255, 255))          # pinta branco
        p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        p.drawImage(0, 0, orig)                  # recorta pelo alpha do original
        p.end()
        px = QPixmap.fromImage(branco)

    self._logo_lbl.setPixmap(px.scaledToHeight(40, Qt.SmoothTransformation))
```

Guarde o pixmap original em `self._logo_pixmap_original` ao criar o cabeçalho — nunca sobrescreva com a versão branca.

---

## 8. Cores dos logs (QTextEdit) por tema

`QTextEdit` com texto colorido não herda o QSS da janela — cada fragmento de texto tem `QTextCharFormat` próprio. Dois problemas surgem:

1. **Novas entradas**: precisam usar a cor correta para o tema ativo
2. **Entradas já renderizadas**: ao trocar o tema, ficam com a cor antiga se não forem re-renderizadas

A solução: guardar todas as entradas em memória e re-inserir tudo ao trocar as cores.

```python
# Cores claras para leitura sobre fundo escuro
LOG_CORES_ESCURO: dict[str, str] = {
    "INFO":    "#93C5FD",
    "SUCESSO": "#6EE7B7",
    "ERRO":    "#FCA5A5",
    "AVISO":   "#FCD34D",
    "DEBUG":   "#C4B5FD",
}

class LogManagerQt:
    def __init__(self, ...):
        self._cores_override: dict[str, str] = {}
        # Cada entrada: (texto_linha, tipo, é_primeira_linha_da_mensagem)
        self._entradas: list[tuple[str, str, bool]] = []

    def definir_cores_override(self, mapa: dict[str, str]) -> None:
        self._cores_override = mapa or {}
        self._re_renderizar()          # re-aplica cores em TODO o texto existente

    def _re_renderizar(self) -> None:
        if not self._entradas:
            return
        self.textbox.clear()
        for entry, tipo, primeira_linha in self._entradas:
            cor = self._resolver_cor(tipo)
            self._inserir_texto(entry, cor, tipo, primeira_linha)

    def _resolver_cor(self, tipo: str) -> str:
        cor = self._cores_override.get(tipo)
        if not cor:
            cor = CORES_PADRAO.get(tipo, COR_FALLBACK)
        return cor

    def adicionar(self, mensagem: str, tipo: str = "INFO") -> None:
        cor = self._resolver_cor(tipo)
        # ... gera `entry` e `primeira`
        self._entradas.append((entry, tipo, primeira))
        self._inserir_texto(entry, cor, tipo, primeira)

    def limpar(self) -> None:
        self._entradas.clear()    # não esquecer de limpar junto com o textbox
        self.textbox.clear()
```

No adaptador que chama `definir_cores_override`:

```python
def atualizar_cores_tema(self, tema: str) -> None:
    mapa = LOG_CORES_ESCURO if tema == "escuro" else {}
    self._inner.definir_cores_override(mapa)
```

Chame `atualizar_cores_tema(tema)` dentro de `_aplicar_tema`. O re-render é instantâneo para logs típicos de RPA (até alguns milhares de linhas).

### Armadilha comum

Usar `definir_cores_override({})` para tema claro funciona, mas se os valores padrão em `CORES_PADRAO` forem cores escuras (ex: `#21478A` azul marinho para INFO), elas serão ilegíveis em fundo escuro. Mantenha sempre dois conjuntos de cores e escolha o correto pelo tema.

---

## 9. Badges com borda arredondada

Badges (status, etiquetas) precisam de `border-radius` no QSS. O problema é que a regra `QLabel { background: transparent; }` do QSS global tem a mesma especificidade que `QLabel { border-radius: 12px; }` no stylesheet do próprio widget, e a ordem de aplicação pode fazer o global ganhar.

Solução: usar `setObjectName` no badge e referenciar pelo ID no seletor, que tem especificidade maior.

```python
self.badge_status = QLabel("Parado")
self.badge_status.setObjectName("etiquetaStatus")

def _aplicar_estilo_badge(self, label: QLabel, texto: str) -> None:
    fundo, cor, borda = MAPA_CORES_STATUS.get(texto, ("#F8FAFC", "#0F172A", "#D9E4F0"))
    name = label.objectName()
    sel = f"QLabel#{name}" if name else "QLabel"
    label.setStyleSheet(f"""
        {sel} {{
            background-color: {fundo};
            color: {cor};
            border: 1px solid {borda};
            border-radius: 17px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 700;
        }}
    """)
    label.setText(texto)
```

Também chame `_aplicar_estilo_badge` novamente dentro de `_aplicar_tema`, pois o `setStyleSheet` global re-aplicado na janela pode sobrescrever o estilo do badge.

---

## 10. Painel de logs em tela cheia (pop-out)

Maximizar a janela inteira só para ver logs é uma má experiência. A solução correta é mover o `QTextEdit` para um `QDialog` maximizado via reparenting nativo do Qt — sem copiar conteúdo, sem sincronização extra.

```python
class JanelaPrincipal(QMainWindow):
    def __init__(self):
        ...
        self._dialog_logs: Optional[QDialog] = None
        self._layout_logs_card: Optional[QVBoxLayout] = None

    def _criar_secao_logs(self) -> QFrame:
        card = QFrame()
        layout = QVBoxLayout(card)
        # ... botões A-, A+, Tela cheia, Exportar ...
        self.txt_logs = QTextEdit()
        layout.addWidget(self.txt_logs, 1)
        self._layout_logs_card = layout  # guarda referência para devolver o widget
        return card

    def _abrir_logs_fullscreen(self) -> None:
        from PySide6.QtWidgets import QDialog
        dlg = QDialog(self, Qt.Window)
        dlg.setWindowTitle("Logs — Tela Cheia")
        dlg.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        dlg.setStyleSheet(self.styleSheet())  # herda o tema atual

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(12, 10, 12, 10)

        btn_voltar = QPushButton("← Voltar")
        btn_voltar.clicked.connect(self._fechar_logs_fullscreen)
        outer.addWidget(btn_voltar, alignment=Qt.AlignLeft)

        outer.addWidget(self.txt_logs, 1)  # reparent: move o widget para o diálogo

        dlg.finished.connect(lambda _: self._fechar_logs_fullscreen())
        self._dialog_logs = dlg
        self.btn_tela_cheia.setText("Restaurar")
        dlg.showMaximized()

    def _fechar_logs_fullscreen(self) -> None:
        if self._dialog_logs is None:
            return
        dlg = self._dialog_logs
        self._dialog_logs = None
        if self._layout_logs_card is not None:
            self._layout_logs_card.addWidget(self.txt_logs, 1)  # devolve ao layout original
        dlg.hide()
        dlg.deleteLater()
        self.btn_tela_cheia.setText("Tela cheia")

    def _toggle_tela_cheia(self) -> None:
        if self._dialog_logs is not None:
            self._fechar_logs_fullscreen()
        else:
            self._abrir_logs_fullscreen()
```

**Por que funciona**: Qt permite que um `QWidget` tenha apenas um pai por vez. Chamar `layout.addWidget(widget)` em outro layout automaticamente remove o widget do layout anterior. Logs continuam sendo escritos em `self.txt_logs` normalmente — o diálogo simplesmente exibe o mesmo widget em outro lugar.

**Cuidado com `finished`**: conecte `finished` ao método de fechamento para lidar com o X do diálogo e o ESC. Mas como `_fechar_logs_fullscreen` zera `self._dialog_logs` primeiro, a reconexão do `finished` não causará loop.

---

## 11. Anti-serrilhamento de fonte global

Fontes ficam serrilhadas no Windows se o `QFont.StyleStrategy` não estiver configurado. Defina ao inicializar a fonte global:

```python
from PySide6.QtGui import QFont, QFontDatabase

def _configurar_fonte(app: QApplication) -> None:
    ids = QFontDatabase.addApplicationFont("caminho/para/fonte.ttf")
    familias = QFontDatabase.applicationFontFamilies(ids)
    if familias:
        f = QFont(familias[0], 10)
        f.setStyleStrategy(QFont.PreferAntialias)  # essencial no Windows
        app.setFont(f)
```

---

## 11. Resumo do fluxo completo

```
App inicializa
  └─ QSettings.value("theme", "claro")
       ├─ "escuro" → _aplicar_tema("escuro")
       └─ outro   → mantém tema claro (padrão)

Usuário clica no botão
  └─ _alternar_tema()
       ├─ inverte self._tema_atual
       ├─ _aplicar_tema(novo_tema)
       └─ QSettings.setValue("theme", novo_tema)

_aplicar_tema(tema)
  ├─ setStyleSheet(_gerar_qss(paleta))   ← troca 95% da UI automaticamente
  ├─ btn_tema.setText(...)
  ├─ elementos com estilo inline → update manual
  ├─ logo → _atualizar_logo_tema(tema)
  ├─ logs → log_mgr.atualizar_cores_tema(tema)
  └─ badges → _aplicar_estilo_badge(...) novamente
```

---

## 12. O que este padrão NÃO faz (decisões explícitas)

| Funcionalidade                         | Decisão          | Motivo                                               |
|----------------------------------------|------------------|------------------------------------------------------|
| Detecção automática de tema do sistema | Desativada       | Controle total pelo usuário, comportamento previsível |
| Arquivo .qss externo                   | Não usado        | QSS inline com f-string é mais fácil de manter       |
| Emojis coloridos no botão de tema      | Não usado        | Renderização inconsistente no Windows; usa ☀ (U+2600) como caractere de texto |
| Animação de transição ao trocar tema   | Não implementada | Preferência de simplicidade                          |
| Temas adicionais (alto contraste)      | Não implementado | Não era requisito                                    |
