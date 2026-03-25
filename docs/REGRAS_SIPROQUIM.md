# Regras SIPROQUIM

## Status
- Documento canonico de regras do projeto
- Escopo atual:
  - `2.2` Estrutura do arquivo texto
  - `3.1.1` `EM`
  - `3.1.9` `TN`
  - `3.1.9.1` `CC`
  - `3.1.9.2` `LR`
  - `3.1.9.3` `LE`

## Fontes oficiais
- `docs/manual-tecnico-030125-1_SIPROQUIM (1).pdf`
  - versao `1.1`
  - atualizado em `03/01/2025`
  - paginas usadas: `1`, `2`, `12`, `13`
- `docs/informativo-tecnico-1_SIPROQUIM.pdf`
  - paginas usadas: `1`, `2`

## Regras gerais obrigatorias
- Arquivo em `UTF-8`
- Nao usar `BOM`
- Dados alfanumericos em `MAIUSCULO`
- Nao usar acentos nem caracteres especiais graficos
- Layout posicional fixo
- Campo alfanumerico:
  - preencher com espacos a direita
- Campo numerico:
  - preencher com zeros a esquerda
- Datas em `dd/mm/aaaa`
- Cada linha do arquivo corresponde a um registro
- Nunca quebrar um registro em mais de uma linha fisica
- Nao usar separadores como `;`, `,` ou `|`

## 3.1.1 - EM
- Tipo fixo: `EM`
- Tamanho total: `31`

| Campo | PI,TM | Tipo | Regra |
|---|---|---|---|
| Tipo | 1,2 | Alfanumerico | `EM` |
| CNPJ | 3,14 | Alfanumerico | 14 digitos sem mascara |
| Mes | 17,3 | Alfanumerico | `JAN` a `DEZ` |
| Ano | 20,4 | Alfanumerico | `2010` em diante |
| Comercializacao Nacional | 24,1 | Numerico | `0` ou `1` |
| Comercializacao Internacional | 25,1 | Numerico | `0` ou `1` |
| Producao | 26,1 | Numerico | `0` ou `1` |
| Transformacao | 27,1 | Numerico | `0` ou `1` |
| Consumo | 28,1 | Numerico | `0` ou `1` |
| Fabricacao | 29,1 | Numerico | `0` ou `1` |
| Transporte | 30,1 | Numerico | `0` ou `1` |
| Armazenamento | 31,1 | Numerico | `0` ou `1` |

## 3.1.9 - TN
- Tipo fixo: `TN`
- Tamanho total: `276`
- Uso: empresa com CNAE principal ou secundario de transporte
- Dependencia: produtos devem existir previamente no `DG`

| Campo | PI,TM | Tipo | Regra |
|---|---|---|---|
| Tipo | 1,2 | Alfanumerico | `TN` |
| CPF/CNPJ Contratante | 3,14 | Numerico | sem mascara |
| Nome Contratante | 17,70 | Alfanumerico | maiusculo, sem acento |
| Numero NF | 87,10 | Alfanumerico | |
| Data Emissao NF | 97,10 | Data | `dd/mm/aaaa` |
| CPF/CNPJ Origem Carga | 107,14 | Numerico | sem mascara |
| Razao Social Origem Carga | 121,70 | Alfanumerico | maiusculo, sem acento |
| CPF/CNPJ Destino Carga | 191,14 | Numerico | sem mascara |
| Razao Social Destino Carga | 205,70 | Alfanumerico | maiusculo, sem acento |
| Local de Retirada | 275,1 | Alfanumerico | `P` ou `A` |
| Local de Entrega | 276,1 | Alfanumerico | `P` ou `A` |

## 3.1.9.1 - CC
- Obrigatorio quando o transporte for intermunicipal ou interestadual
- Tamanho minimo observado no layout: `103`
- Modal inicia na posicao `102`

| Campo | PI,TM | Tipo | Regra |
|---|---|---|---|
| Tipo | 1,2 | Alfanumerico | `CC` |
| Num. Conhecimento Carga | 3,9 | Numerico | sem mascara |
| Data Conhecimento Carga | 12,10 | Data | `dd/mm/aaaa` |
| Data Recebimento Carga | 22,10 | Data | `dd/mm/aaaa` |
| Responsavel Recebimento | 32,70 | Alfanumerico | maiusculo, sem acento |
| Modal de Transporte | 102,? | Alfanumerico | `RO`, `AQ`, `FE`, `AE` |

### Regra do modal
- O manual permite 1 ou mais modais concatenados
- Exemplos validos:
  - `RO`
  - `ROAE`
- Nao usar espaco, virgula ou separador

## 3.1.9.2 - LR
- Obrigatorio quando `TN.Local de Retirada = A`
- Tamanho total: `86`

| Campo | PI,TM | Tipo | Regra |
|---|---|---|---|
| Tipo | 1,2 | Alfanumerico | `LR` |
| CPF/CNPJ Terceirizada | 3,14 | Numerico | sem mascara |
| Nome Terceirizada | 17,70 | Alfanumerico | maiusculo, sem acento |

## 3.1.9.3 - LE
- Obrigatorio quando `TN.Local de Entrega = A`
- Tamanho total: `86`

| Campo | PI,TM | Tipo | Regra |
|---|---|---|---|
| Tipo | 1,2 | Alfanumerico | `LE` |
| CPF/CNPJ Terceirizada | 3,14 | Numerico | sem mascara |
| Nome Terceirizada | 17,70 | Alfanumerico | maiusculo, sem acento |

## Regras extras do fluxo interno
- Validar tamanho final da linha antes de salvar:
  - `EM = 31`
  - `TN = 276`
  - `CC >= 103`
  - `LR = 86`
  - `LE = 86`
- `TN.Local de Retirada` e `TN.Local de Entrega` aceitam apenas `P` ou `A`
- `CC.Responsavel Recebimento` nao pode ficar vazio
- Se houver CPF em campos de documento do `TN`, registrar alerta operacional
- Se uma linha `TN` for gravada curta, o erro oficial costuma aparecer como:
  - `begin 16, end 86, length X`
- Se `TN.Local de Retirada = A`, precisa existir `LR`
- Se `TN.Local de Entrega = A`, precisa existir `LE`

## Padrao atual do projeto
- `EM`: transporte nacional com flag de transporte ativo
- `TN`: fallback de local para `P`
- `CC`: modal default `RO`
- Arquivo final salvo em `UTF-8`
- O TXT gerado e revalidado no disco antes do upload

## Checklist rapido
- Existe exatamente 1 linha `EM`
- A primeira linha e `EM`
- Toda linha `TN` tem `276` caracteres
- Toda linha `CC` tem modal valido
- Nao ha linha em branco
- Nao ha minusculas
- Nao ha acento
- Nao ha `BOM`
- Se `TN` usar `A`, existe `LR` ou `LE`
