# REGRAS

## Escopo fixo
Este arquivo e a referencia principal para revisao de layout SIPROQUIM nas secoes:
- `3.1.1` (`EM`)
- `3.1.9` (`TN`)
- `3.1.9.1` (`CC`)

Nao sair desse escopo sem atualizar este documento.

## Fontes oficiais
- `manual-tecnico-030125-1_SIPROQUIM (1).pdf` (versao 1.1), paginas 2 e 12.
- `informativo-tecnico-1_SIPROQUIM.pdf`, pagina 1.

## Regras gerais obrigatorias
- Arquivo TXT em `UTF-8`.
- Campos alfanumericos em `MAIUSCULO`.
- Nao usar acentos/caracteres especiais graficos (ex.: `Ç`, `Á`, `Ã`).
- CPF/CNPJ sem mascara (somente digitos).
- Datas sempre em `dd/mm/aaaa`.
- Arquivo posicional fixo: sem separador por `;`, `,` ou `|`.
- Cada secao/subsecao ocupa exatamente 1 linha.
- Uma quebra de linha apenas entre registros (nunca no meio do registro).

## 3.1.1 - Identificacao da Empresa/Mapa (EM)
- Tipo fixo: `EM`
- Tamanho da linha: `31`

| Campo | PI,TM | Tipo | Regra |
|---|---|---|---|
| Tipo | 1,2 | Alfanumerico | `EM` |
| CNPJ | 3,14 | Alfanumerico | 14 digitos sem mascara |
| Mes | 17,3 | Alfanumerico | `JAN` a `DEZ` |
| Ano | 20,4 | Alfanumerico | `2010` em diante |
| Comercializacao Nacional | 24,1 | Numerico | `1` ou `0` |
| Comercializacao Internacional | 25,1 | Numerico | `1` ou `0` |
| Producao | 26,1 | Numerico | `1` ou `0` |
| Transformacao | 27,1 | Numerico | `1` ou `0` |
| Consumo | 28,1 | Numerico | `1` ou `0` |
| Fabricacao | 29,1 | Numerico | `1` ou `0` |
| Transporte | 30,1 | Numerico | `1` ou `0` |
| Armazenamento | 31,1 | Numerico | `1` ou `0` |

## 3.1.9 - Transporte Nacional (TN)
- Tipo fixo: `TN`
- Tamanho da linha: `276`
- Uso: empresa com CNAE principal/secundario de transporte.
- Dependencia: produtos devem estar previamente no `DG`.

| Campo | PI,TM | Tipo | Regra |
|---|---|---|---|
| Tipo | 1,2 | Alfanumerico | `TN` |
| CPF/CNPJ Contratante | 3,14 | Numerico | Sem mascara |
| Nome Contratante | 17,70 | Alfanumerico | Maiusculo, sem acento |
| Numero NF | 87,10 | Alfanumerico | |
| Data Emissao NF | 97,10 | Data | `dd/mm/aaaa` |
| CPF/CNPJ Origem Carga | 107,14 | Numerico | Sem mascara |
| Razao Social Origem Carga | 121,70 | Alfanumerico | Maiusculo, sem acento |
| CPF/CNPJ Destino Carga | 191,14 | Numerico | Sem mascara |
| Razao Social Destino Carga | 205,70 | Alfanumerico | Maiusculo, sem acento |
| Local de Retirada | 275,1 | Alfanumerico | `P` ou `A` |
| Local de Entrega | 276,1 | Alfanumerico | `P` ou `A` |

## 3.1.9.1 - Conhecimento de Carga (CC)
- Tipo fixo: `CC`
- Obrigatorio quando transporte for intermunicipal ou interestadual.

| Campo | PI,TM | Tipo | Regra |
|---|---|---|---|
| Tipo | 1,2 | Alfanumerico | `CC` |
| Num. Conhecimento Carga | 3,9 | Numerico | Sem mascara |
| Data Conhecimento Carga | 12,10 | Data | `dd/mm/aaaa` |
| Data Recebimento Carga | 22,10 | Data | `dd/mm/aaaa` |
| Responsavel Recebimento | 32,70 | Alfanumerico | Maiusculo, sem acento |
| Modal de Transporte | 102,? | Alfanumerico | `RO`, `AQ`, `FE` ou `AE`; se mais de um modal, concatenar sem espaco/virgula |

## Regras extras importantes para revisar sempre
- Validar tamanho final de linha antes de salvar:
  - `EM = 31`
  - `TN = 276`
  - `CC = 103` (implementacao atual com modal de 2 caracteres)
- `TN.Local de Retirada` e `TN.Local de Entrega` devem ser somente `P` ou `A`.
- `CC.Responsavel Recebimento` nao pode ficar vazio.
- Se houver CPF em campos de documento no `TN`, registrar alerta operacional (pode haver rejeicao no validador externo).
- Quando existir `TN` intermunicipal/interestadual sem `CC`, tratar como erro de preenchimento.

## Padrao interno atual do projeto
- `EM`: flags padrao de transporte nacional (`transporte = 1`).
- `TN`: `local_retirada` e `local_entrega` com fallback para `P`.
- `CC`: modal preenchido como `RO` por padrao.
- Arquivo final salvo em `UTF-8`.

## Checklist de revisao rapida (uso diario)
- Existe 1 linha `EM` no inicio.
- Toda linha `TN` tem contratante, origem e destino com documento e nome.
- `TN` termina com `P/A` em retirada e entrega.
- Cada `TN` que exigir conhecimento possui linha `CC`.
- Datas em todos os pontos estao em `dd/mm/aaaa`.
- Sem acentos e sem texto minusculo em campos alfanumericos.
