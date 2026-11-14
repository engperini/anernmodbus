# 03 — Mapa de registradores

Escravo 5. Leitura FC03. Escrita FC06 em (leitura + 481). Valores do dump de 14/11/2026 11:27 (saída SBU, carregador OSO, carregando pelo sol).
Versão em CSV: [`data/registradores-4501-4564.csv`](../data/registradores-4501-4564.csv).

Status: ✅ confirmado (display, app ou teste) · 🟡 provável · ❓ desconhecido

## Telemetria e informações

| Reg. | Dump | Campo | Escala | Status |
|---|---|---|---|---|
| 4501 | 4 | Modo de operação (ver abaixo) | enum | 🟡 3 e 4 confirmados |
| 4502 | 2178 | Tensão da rede | ÷10 V | ✅ |
| 4503 | 600 | Frequência da rede | ÷10 Hz | ✅ |
| 4504 | 1617 | Tensão FV | ÷10 V | ✅ |
| 4505 | 253 | Potência FV | W | ✅ |
| 4506 | 267 | Tensão da bateria | ÷10 V | ✅ |
| 4507 | 34 | SOC da bateria (do BMS) | % | ✅ |
| 4508 | 7 | Corrente de carga da bateria | A | ✅ (= display) |
| 4509 | 0 | Corrente de descarga da bateria | A | ✅ |
| 4510 | 2178 | Tensão de saída | ÷10 V | ✅ |
| 4511 | 600 | Frequência de saída | ÷10 Hz | ✅ |
| 4512 | 348 | Potência aparente de saída | VA | ✅ |
| 4513 | 248 | Potência ativa de saída | W | ✅ |
| 4514 | 8 | Uso da capacidade | % | ✅ |
| 4515 | 8 | cópia do uso da capacidade? | % | 🟡 |
| 4516 | 0 | — | | ❓ |
| 4517 | 220 | Corte da saída dupla (prog 42), em V | ÷10 V | ✅ |
| 4518 | 7511 | Versão da CPU ("U1 75 11") | | ✅ |
| 4519 | 0 | — (candidato prog 37/41) | | ❓ |
| 4520 | 1 | — (candidato prog 44) | | ❓ |
| 4521 | 4200 | Potência nominal | W | ✅ |
| 4522 | 4200 | Potência nominal | VA | ✅ |
| 4523 | 230 | Tensão CA nominal | V | ✅ |
| 4524 | 18 | Corrente CA nominal | A | ✅ |
| 4525 | 240 | Tensão nominal da bateria | ÷10 V | ✅ |
| 4526 | 230 | Tensão de saída nominal | V | ✅ |
| 4527 | 500 | Frequência nominal | ÷10 Hz | ✅ |
| 4528 | 18 | Corrente de saída nominal | A | ✅ |
| 4529 | 0 | Código de aviso | enum | 🟡 |
| 4530 | 0 | Código de falha | enum | ✅ |
| 4531–4533 | 5535 | não usado (provável 65535) | | 🟡 |
| 4534 | 55 | Corte da saída dupla (prog 42), em % | % | ✅ |
| 4535 | 292 | Flags de configuração (bytes invertidos) | bitmask | ✅ |
| 4553 | 5478 | Flags de status (bytes invertidos) | bitmask | 🟡 |
| 4554 | 2 | prog 38 (2 A) **ou** estado da bateria (2 = carregando) | | ❓ |
| 4555 | 11 | — (10 em 13/11; não é corrente nem ciclos) | | ❓ |
| 4556 | 11 | — (igual ao 4555) | | ❓ |
| 4557 | 40 | Temperatura NTC máxima | °C | ✅ |
| 4558–4559 | 0 | — | | ❓ |
| 4560 | 1 | — (candidato prog 44) | | ❓ |
| 4561 | 0 | Estado do LED decorativo (prog 39): 0 LOF, 1 LON | | ✅ só leitura |
| 4562–4564 | 0 | — | | ❓ |

### 4501 — Modo de operação

| Código | Modo | Status |
|---|---|---|
| 0 | Ligando | família |
| 1 | Espera | família |
| 2 | Rede | família |
| 3 | Bateria (casa alimentada pela bateria) | ✅ observado |
| 4 | Bypass (rede direto; ex.: SBU com bateria baixa, ou USB) | ✅ observado |
| 5 | Carregando | família |
| 6 | Falha | família |

"Família" = tabela dos inversores irmãos ISolar SMG/Anenji (Solar2MQTT).

### 4535 — Flags de configuração (trocar os bytes antes)

| Bit (após troca) | Configuração | Prog | Escrita | Em 14/11 |
|---|---|---|---|---|
| 0x0001 | Registro de falhas | 25 | 5010 | ligado |
| 0x0002 | Equalização da bateria | 30 | — | desligado |
| 0x0004 | Equalização imediata | 36 | — | desligado |
| 0x0100 | Alarme | 18 | 5002 | desligado |
| 0x0400 | Luz de fundo | 20 | 5004 | ligado |
| 0x0800 | Reinício após sobrecarga | 06 | 5005 | desligado |
| 0x1000 | Reinício após sobretemperatura | 07 | 5006 | desligado |
| 0x2000 | Apito na falha da fonte principal | 22 | 5007 | ligado |
| 0x4000 | Volta à tela padrão | 19 | 5008 | desligado |
| 0x8000 | Bypass na sobrecarga | 23 | 5009 | desligado |

Validação: bate 8/8 com 5002–5010 lidos diretamente, e o app mostra "Battery equalization: off" e "Start balancing immediately: disable".

### 4553 — Flags de status (trocar os bytes antes) 🟡

| Bit (após troca) | Significado |
|---|---|
| 0x0100 | Na bateria |
| 0x0200 | Rede ativa |
| 0x1000 | Carga desligada |
| 0x2000 | Rede ativa |
| 0x4000 | Carga habilitada |

Leitura de 14/11 (0x6615): carga habilitada + rede ativa, "na bateria" desligado, coerente com bypass. Confirmar com a casa na bateria.

## Configurações (leitura → escrita)

| Leitura | Escrita | Programa | Valores | Status da escrita |
|---|---|---|---|---|
| 4536 | 5017 | 16 Prioridade do carregador | CSO=0 SNU=1 OSO=2 | ✅ 0, 1, 2 testados |
| 4537 | 5018 | 01 Prioridade de saída | USB=0 SUB=1 SBU=2 MKS=3 | ✅ 0, 1, 2 testados |
| 4538 | 5019 | 03 Faixa de entrada CA | APL=0 (90–280 V) UPS=1 (170–280 V) | não testada |
| 4539 | 5020 | 05 Tipo de bateria | AGM=0 FLD=1 USE=2 LIB=3 LIC=4 LIP=5 LIL=6 | não testada |
| 4540 | 5021 | 09 Frequência de saída | 50 Hz=0 60 Hz=1 | não testada |
| 4541 | 5022 | 02 Corrente máx. de carga total | A | ✅ testada |
| 4542 | 5023 | 10 Tensão de saída | 220/230/240 V | não testada |
| 4543 | 5024 | 11 Corrente máx. de carga pela rede | A | não testada |
| 4544 | 5025 | 12 Volta para a rede (SBU) | ÷10 V | não testada |
| 4545 | 5026 | 13 Volta para a bateria (SBU) | ÷10 V | não testada |
| 4546 | 5027 | 26 Tensão bulk | ÷10 V | não testada |
| 4547 | 5028 | 27 Tensão de flutuação | ÷10 V | não testada |
| 4548 | 5029 | 29 Corte por bateria baixa | ÷10 V | não testada |
| 4549 | 5030 | 31 Tensão de equalização | ÷10 V | não testada |
| 4550 | 5031 | 33 Tempo de equalização | min | não testada |
| 4551 | 5032 | 34 Timeout de equalização | min | não testada |
| 4552 | 5033 | 35 Intervalo de equalização | dias | não testada |
| bit 4535 | 5002, 5004–5010 | 18, 20, 06, 07, 22, 19, 23, 25 | 0/1 | estado conferido |

Endereços **recusados** para escrita: 4561, 5042 (LED). 5003 nunca foi identificado.
