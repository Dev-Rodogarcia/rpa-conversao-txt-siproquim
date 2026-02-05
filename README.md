<!-- PORTFOLIO-FEATURED
title: SIPROQUIM Converter V6 (PDF -> TXT)
description: Conversor de PDF para TXT no layout SIPROQUIM/Rodogarcia para a Policia Federal. Extrai NFs e CTes, deduplica e valida formatos/checksums com detecao de mudanca de layout.
technologies: Python 3.8+, pdfplumber, CustomTkinter, PyInstaller, Pillow
demo: N/A (Desktop GUI + CLI)
highlight: true
image: public/foto1.png
-->

<p align="center">
  <img src="public/foto.png" alt="Capa do projeto" width="1200">
</p>

# SIPROQUIM Converter V6

Conversor de PDF para TXT no formato SIPROQUIM/Rodogarcia para a Polícia Federal. Extrai dados de Notas Fiscais e CTes de arquivos PDF e gera arquivos TXT formatados conforme o layout exigido pelo sistema SIPROQUIM.

## Sobre o Projeto

Este projeto foi desenvolvido para automatizar a conversão de documentos PDF contendo informações de transporte de produtos controlados em arquivos TXT no formato SIPROQUIM. O sistema processa PDFs com múltiplas páginas, extrai dados de NFs e CTes, realiza deduplicação automática e gera arquivos prontos para importação no sistema da Polícia Federal.

### Funcionalidades Principais

- **Extração Automática**: Processa PDFs com centenas de páginas, extraindo dados de emitentes, destinatários, contratantes, NFs e CTes
- **Deduplicação Inteligente**: Remove duplicatas automaticamente por número de NF
- **Validação Robusta (V6)**: Validação preventiva antes de gerar o TXT: checksum (Módulo 11) em CNPJs/CPFs, formato de NF/CTe/datas, estrutura do PDF (detecta mudança de layout da PF)
- **Validação de CNPJ/CPF**: Validação rigorosa usando algoritmo oficial (Módulo 11), com suporte para CPFs convertidos e detecção de pessoa física
- **Interface Gráfica Moderna**: Interface intuitiva construída com CustomTkinter, com logs em tempo real e barra de progresso
- **Seleção de Filiais**: Sistema de busca e seleção de filiais por CNPJ ou dropdown
- **Nomenclatura Única**: Gera nomes de arquivo únicos mesmo para o mesmo CNPJ, evitando sobrescrita
- **Validação de Formato**: Garante que o arquivo gerado está no formato exato exigido pelo SIPROQUIM

## Instalação

### Requisitos

- Python 3.8 ou superior
- Dependências listadas em `requirements.txt`

### Passos

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd script-conservao-txt
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como Usar

### Executável (.exe) - Recomendado para Usuários Finais

O executável permite usar o sistema sem instalar Python ou qualquer dependência. Basta fazer duplo clique no arquivo `Conversor_SIPROQUIM.exe` na pasta `dist/`.

**Passo a passo:**

1. Execute o arquivo `.exe`
2. Na Etapa 1, clique em "Buscar PDF" e selecione o arquivo
3. Na Etapa 2, digite o CNPJ (14 dígitos) e clique em "Buscar" ou selecione a filial no dropdown
4. Na Etapa 3, selecione o mês e ano de referência
5. Clique em "CONVERTER AGORA"
6. Aguarde o processamento (acompanhe pelos logs e barra de progresso)
7. O arquivo será salvo automaticamente na pasta Downloads

### Interface Gráfica (Python)

Execute o arquivo `gui.py`:

```bash
python gui.py
```

### Linha de Comando

```bash
python main.py <caminho_pdf> <cnpj_rodogarcia> [caminho_saida] [--mes MES] [--ano ANO]
```

**Exemplo:**
```bash
python main.py fretes.pdf 60960473000243 --mes 12 --ano 2025
```

### Gerar Executável

Para criar o executável a partir do código-fonte:

```bash
python build.py
```

O executável será gerado na pasta `dist/`.

## Estrutura do Projeto

```
script-conservao-txt/
├── main.py                    # Script principal (CLI)
├── gui.py                     # Ponto de entrada da GUI
├── build.py                   # Script para gerar executável
├── requirements.txt           # Dependências
├── README.md                  # Documentação
├── Conversor_SIPROQUIM.spec   # Configuração PyInstaller
├── src/
│   ├── extrator/              # Módulo de extração de PDF
│   │   ├── pdf_extractor.py
│   │   ├── tabela_parser.py
│   │   └── campo_extractor.py
│   ├── gerador/               # Módulo de geração de TXT
│   │   ├── txt_generator.py
│   │   ├── sanitizers.py
│   │   ├── validators.py
│   │   └── layout_constants.py
│   ├── config/                # Configurações
│   │   └── filiais.py
│   └── gui/                   # Interface gráfica
│       ├── app.py
│       ├── constants.py
│       ├── validators.py
│       ├── log_manager.py
│       ├── progress_manager.py
│       └── utils.py
└── public/                    # Recursos (ícones, imagens)
```

## Formato do Arquivo Gerado

O arquivo TXT gerado segue o layout SIPROQUIM com três tipos de linhas:

### Linha EM (Cabeçalho - 31 caracteres)
- Tipo: "EM" (2 chars)
- CNPJ Rodogarcia: 14 chars
- Mês: 3 chars (JAN, FEV, MAR, etc.)
- Ano: 4 chars
- Flags: 8 chars

### Linha TN (Transporte Nacional - 276 caracteres)
- Tipo: "TN" (2 chars)
- CNPJ Contratante: 14 chars
- Nome Contratante: 70 chars
- Número NF: 10 chars
- Data Emissão NF: 10 chars
- CNPJ Origem: 14 chars
- Razão Social Origem: 70 chars
- CNPJ Destino: 14 chars
- Razão Social Destino: 70 chars
- Local Retirada: 1 char
- Local Entrega: 1 char

### Linha CC (Conhecimento de Carga - 103 caracteres)
- Tipo: "CC" (2 chars)
- Número CTe: 9 chars
- Data CTe: 10 chars
- Data Recebimento: 10 chars
- Responsável Recebimento: 70 chars
- Modal: "RO" (2 chars)

## Validação Robusta e Logs (V6)

O sistema valida todos os campos **antes** de gerar o TXT e exibe logs detalhados na GUI e no terminal.

### O que é validado

- **Estrutura do PDF**: Presença dos labels obrigatórios (EMITENTE, DESTINATÁRIO, CONTRATANTE, CT-E, CNPJ/CPF). Se o layout da PF mudar, o script interrompe e registra o erro.
- **NF**: Número (4–6 dígitos), data (dd/mm/aaaa e data existente no calendário).
- **CTe**: Número (1–9 dígitos), data (formato e calendário).
- **CNPJs/CPFs**: Tamanho (11 ou 14 dígitos) e checksum (Módulo 11).
- **Nomes e recebedor**: Tamanho mínimo e campos obrigatórios.

### Tipos de log exibidos

| Tipo | Cor (GUI) | Significado |
|------|-----------|-------------|
| **INFO** | Azul | Andamento, totais, relatório final |
| **VALIDACAO** | Azul | Quantidade de erros por NF |
| **CRITICO** | Vermelho | Campo obrigatório inválido; SIPROQUIM tende a rejeitar |
| **ERRO** | Vermelho | Formato/tamanho inválido (ex.: data, nome curto) |
| **ATENCAO** / **ACAO_NECESSARIA** | Amarelo | CPF no lugar de CNPJ, nome vazio, CNPJ emitente inválido; ação manual sugerida |
| **ALERTA** | Amarelo | Resumo de registros com erros críticos |
| **SUCESSO** | Verde | Auto-correção aplicada (ex.: nome preenchido pela base) |

Nenhum registro é removido: todos seguem para o TXT; os problemas são apenas sinalizados nos logs para correção manual quando necessário.

## Validação de CNPJ/CPF

O sistema implementa validação inteligente de CNPJs:

- **CNPJ Origem (Emitente)**: Validação rigorosa - deve ser empresa válida
- **CNPJ Contratante**: Validação flexível - aceita CPFs convertidos e detecta pessoa física pelo nome
- **CNPJ Destino**: Validação flexível - aceita CPFs convertidos e detecta pessoa física pelo nome

A detecção de pessoa física verifica se o nome contém indicadores de empresa (LTDA, SA, EIRELI, etc.) como palavras completas, evitando falsos positivos (ex: "ME" em "ALMEIDA").

## Nomenclatura dos Arquivos

Os arquivos gerados seguem o padrão:

```
M{ANO}{MÊS}{CNPJ}_{NOME_PDF_SANITIZADO}.txt
```

**Exemplo:**
```
M2025DEZ60960473000243_FRETE_PRODUTOS_CONTROLADOS_202.txt
```

Mesmo com o mesmo CNPJ, mês e ano, PDFs diferentes geram arquivos diferentes, evitando sobrescrita.

## Observações Importantes

1. **Encoding**: Arquivos são gerados em UTF-8 conforme Manual Técnico SIPROQUIM
2. **Deduplicação**: NFs duplicadas são automaticamente removidas
3. **Campo Recebedor**: Sistema robusto de fallback garante que o campo sempre tenha valor válido
4. **Validação de Formato**: Cada linha é validada antes de ser escrita no arquivo
5. **Avisos**: O sistema exibe avisos quando CNPJs válidos podem não estar cadastrados no SIPROQUIM

## Troubleshooting

### Erro: "CNPJ inválido"
- Verifique se o CNPJ foi extraído corretamente do PDF
- Para pessoa física, o sistema aceita CPFs convertidos ou CNPJs inválidos quando o nome não contém indicadores de empresa
- Verifique se o CNPJ está cadastrado no sistema SIPROQUIM

### Erro: "ConstraintViolationException" no SIPROQUIM
- O CNPJ é válido, mas pode não estar cadastrado no sistema
- Verifique se todos os CNPJs estão cadastrados no SIPROQUIM
- O sistema exibe avisos sobre CNPJs que podem não estar cadastrados

### Dados não extraídos corretamente
- Verifique se o PDF tem o formato esperado
- Verifique os logs na GUI para mais detalhes
- Pode ser necessário ajustar as expressões regulares em `src/extrator/pdf_extractor.py`

### GUI não abre
- Verifique se todas as dependências estão instaladas: `pip install -r requirements.txt`
- Tente executar via linha de comando para ver erros detalhados

## Changelog

### Versão 6.0
- Validação robusta antes de gerar o TXT (checksum, formato, integridade)
- Validação de estrutura do PDF (detecta mudança de layout da PF)
- Validação de NF/CTe (número e data) e de todos os CNPJs/CPFs (Módulo 11)
- Logs estruturados: INFO, VALIDACAO, CRITICO, ERRO, ATENCAO, ACAO_NECESSARIA, ALERTA, SUCESSO
- Relatório final com totais de registros processados, corrigidos e com erros

### Versão 5.0
- Validação inteligente de CNPJ para pessoa física
- Detecção automática de pessoa física pelo nome
- Correção de falsos positivos na detecção de pessoa física
- Nomenclatura única de arquivos (inclui nome do PDF)
- Mensagens de aviso formatadas em múltiplas linhas
- Garantia de quebra de linha no final do arquivo
- Validação de CTe antes de gerar linha CC
- Tratamento de erros melhorado (não interrompe processamento em caso de erro em CC)
- Validação de recebedor (garante mínimo de 3 caracteres)
- Aviso quando CNPJ contratante é igual ao destino

## Autor

**Lucas Andrade**

Desenvolvido para uso interno na Rodogarcia. Sistema validado com arquivos reais aceitos pelo sistema SIPROQUIM.

- Email: lucasmac.dev@gmail.com
- GitHub: [@valentelucass](https://github.com/valentelucass)

## Licença

Este projeto foi desenvolvido para uso interno.

## Referências

- Manual Técnico SIPROQUIM (seções 3.1.1, 3.1.9, 3.1.9.1)
- Layout Rodogarcia para arquivos TXT
- Algoritmo de validação de CNPJ/CPF (Módulo 11)
