# 04 — Programas do display

Programas do menu do inversor, com os valores conferidos no display em 13–14/11/2026. Onde o manual e o equipamento divergem, vale o equipamento.

| Prog | Função | Opções (display) | Valor atual | Registrador |
|---|---|---|---|---|
| 01 | Prioridade de saída | USB (rede primeiro), SUB (solar primeiro), SBU (solar → bateria → rede), MKS | SBU / USB (testes) | 4537 / 5018 |
| 02 | Corrente máx. de carga total | 10–120 A | 40 → 70 A | 4541 / 5022 |
| 03 | Faixa de entrada CA | APL 90–280 V, UPS 170–280 V | UPS | 4538 / 5019 |
| 05 | Tipo de bateria | AGM, FLd, USE, LIB, LIC, LIP, LIL | LIL | 4539 / 5020 |
| 06 | Reinício após sobrecarga | liga/desliga | desligado | bit 0x0800 / 5005 |
| 07 | Reinício após sobretemperatura | liga/desliga | desligado | bit 0x1000 / 5006 |
| 09 | Frequência de saída | 50 / 60 Hz | 60 Hz | 4540 / 5021 |
| 10 | Tensão de saída | 220 / 230 / 240 V | 220 V | 4542 / 5023 |
| 11 | Corrente máx. de carga pela rede | 2, 10 … 100 A | 2 A | 4543 / 5024 |
| 12 | Volta para a rede (SBU) | V (ou % com LIB-485) | 24,5 V | 4544 / 5025 |
| 13 | Volta para a bateria (SBU) | V, FUL | 27,0 V | 4545 / 5026 |
| 16 | Prioridade do carregador | CSO, SNU, OSO | OSO | 4536 / 5017 |
| 18 | Alarme | liga/desliga | desligado | bit 0x0100 / 5002 |
| 19 | Volta à tela padrão | liga/desliga | desligado | bit 0x4000 / 5008 |
| 20 | Luz de fundo | liga/desliga | ligado | bit 0x0400 / 5004 |
| 22 | Apito na falha da fonte principal | liga/desliga | ligado | bit 0x2000 / 5007 |
| 23 | Bypass na sobrecarga | liga/desliga | desligado | bit 0x8000 / 5009 |
| 25 | Registro de falhas | liga/desliga | ligado | bit 0x0001 / 5010 |
| 26 | Tensão bulk | V | 28,4 V | 4546 / 5027 |
| 27 | Tensão de flutuação | V | 27,4 V | 4547 / 5028 |
| 29 | Corte por bateria baixa | V (ou % com LIB-485) | 24,0 V | 4548 / 5029 |
| 30 | Equalização | liga/desliga | desligado | bit 0x0002 |
| 31 | Tensão de equalização | V | 27,0 V (fábrica 29,2) | 4549 / 5030 |
| 33 | Tempo de equalização | min | 60 | 4550 / 5031 |
| 34 | Timeout de equalização | min | 120 | 4551 / 5032 |
| 35 | Intervalo de equalização | dias | 30 | 4552 / 5033 |
| 36 | Equalização imediata | liga/desliga | desligado | bit 0x0004 |
| 37 | Grid-tie (injeção na rede) | OFF / HYd | **OFF** (não ligar) | não identificado |
| 38 | Corrente de injeção na rede | A | 2 A | 4554? |
| 39 | LED decorativo (RGB) | LON / LOF | varia | 4561 (só leitura) |
| 41 | Saída dupla | L2F = desligada | L2F | não identificado |
| 42 | Corte da saída dupla | V / % | 55% (22,0 V) | 4534 / 4517 |
| 43 | Protocolo do lítio | manual: PYL / PAC; **display: 48** | **48 — nunca alterar** | — |
| 44 | Acesso à rede com atraso | dIS / EnA | EnA | 4520 ou 4560? |
| 45 | Carga máx. da segunda saída | 20–70% | 33% (≈ 1400 W) | — |

## Significados úteis

- **USB** (código 0): rede alimenta a casa primeiro.
- **SUB** (1): solar primeiro, depois rede, bateria por último.
- **SBU** (2): solar → bateria → rede. Com a bateria abaixo do prog 12, passa para a rede (bypass) até a bateria subir ao prog 13.
- **MKS** (3): solar alimenta a carga e a rede completa; bateria como reserva. Nos testes se comportou igual ao SUB.
- **CSO** (0): solar primeiro, rede como reserva para carregar.
- **SNU** (1): solar e rede carregam juntos.
- **OSO** (2): só solar carrega a bateria.
- **LIL** (6): lítio com comunicação BMS (o manual chama de LIB-485). Com LIB-485 o manual diz que 12/13/29 aparecem em %; aqui aparecem em V.
- **bP** no display = **bateria não conectada** (não é bypass).
- **E9** = equalização em andamento.
