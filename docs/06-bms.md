# 06 — BMS e baterias

## Comunicação inversor ↔ BMS

- Funciona com **prog 05 = LIL** e **prog 43 = 48**. O manual fala em PYL/PAC para o prog 43, mas este firmware mostra um número; **48 é o valor que funciona — não alterar**.
- Evidências: SOC vem do BMS (4507), limites de carga reconhecidos, display mostra as telas do BMS.
- Relatos externos de outros Anern com 43 = 49 para BMS JK; não se aplica aqui.
- Com duas baterias em paralelo, conferir se a bateria ligada ao inversor agrega os dados das duas (cabo de comunicação entre elas e endereço/DIP conforme o manual da Felicity).

## Telas do BMS no display

Acesso: tela principal, avançando com DOWN (o manual diz segurar ESC; neste aparelho basta navegar). Fotos em `images/05-display-inversor/bms-*.jpg` e manual em `images/04-manual/manual-telas-bms-p12.jpg`.

| Tela | Manual (esq. / dir.) | Display em 14/11 | Observação |
|---|---|---|---|
| 1 | Tensão total / SOC | 26,6 V / 39% | igual ao manual |
| 2 | Corrente de carga / de descarga | 0 A / **910** | **diferente**: 910 varia muito, sem unidade; não é a corrente de carga (conferido). Significado desconhecido |
| 3 | Capacidade nominal (Ah) / ciclos | **24,0 V** / 6 | **diferente**: mostra tensão nominal; ciclos = 6 |
| 4 | MOS mín. / máx. | 25,2 / 29,2 °C | igual |
| 5 | Célula máx. / mín. | 3,33 / 3,31 V | igual |
| 6 | Temp. célula máx. / mín. | 26,2 / 26,2 °C | igual |

Diferenças nas telas 2 e 3 → firmware diferente do manual.

**Nenhum desses dados aparece no bloco Modbus 4501–4564** (nenhum valor como 333, 262, 292, 910 no dump). Para tê-los no HA seria preciso ler o BMS diretamente (RS485/CAN da Felicity).

## Saúde em 14/11/2026

- Células entre 3,31 e 3,33 V (diferença de 20 mV): bem equilibradas.
- Temperaturas 25–29 °C: normais.
- 6 ciclos: bateria praticamente nova.

## Ajustes de bateria recomendados (LiFePO4 24 V, 8S)

| Ajuste | Valor em uso | Faixa segura |
|---|---|---|
| Bulk (26) | 28,4 V | 26,0–28,8 V |
| Flutuação (27) | 27,4 V | 26,0–28,8 V, ≤ bulk |
| Corte (29) | 24,0 V | 24,0–25,0 V, < volta rede |
| Volta rede (12) | 24,5 V | 21,0–25,5 V |
| Volta bateria (13) | 27,0 V | 24,0–29,0 V, > volta rede |
| Corrente total (02) | 70 A (2 baterias) | ≤ 100 A por bateria |
