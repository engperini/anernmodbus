# 05 — Códigos de falha e aviso

Fonte: manual impresso (fotos em `images/04-manual/manual-codigos-*.jpg`).

## 4530 — Falha (0 = sem falha)

### Inversor (manual 5.9)

| Código | Falha |
|---|---|
| 01 | Ventilador travado com o inversor desligado |
| 02 | Sobretemperatura |
| 03 | Tensão da bateria alta |
| 04 | Tensão da bateria baixa |
| 05 | Curto na saída ou sobretemperatura interna |
| 06 | Tensão de saída alta |
| 07 | Sobrecarga (tempo esgotado) |
| 08 | Tensão do barramento alta |
| 09 | Falha na partida suave do barramento |
| 51 | Sobrecorrente ou surto |
| 52 | Tensão do barramento baixa |
| 53 | Falha na partida suave do inversor |
| 55 | Tensão CC na saída CA |
| 57 | Falha no sensor de corrente |
| 58 | Tensão de saída baixa |
| 59 | Tensão FV acima do limite |

### Bateria / BMS ("Battery fault code")

| Código | Falha |
|---|---|
| 21 | Sobretensão de célula |
| 22 | Subtensão de célula |
| 23 | Sobretensão do pack |
| 24 | Subtensão do pack |
| 25 | Sobrecorrente de carga |
| 26 | Sobrecorrente de descarga |
| 27 | Sobretemperatura de célula na carga |
| 28 | Sobretemperatura de célula na descarga |
| 29 | Subtemperatura de célula na carga |
| 30 | Subtemperatura de célula na descarga |
| 31 | Sobretemperatura ambiente |
| 32 | Subtemperatura ambiente |
| 33 | Sobretemperatura do MOS |
| 35 | Curto-circuito na bateria |
| 36 | Sobretensão de carga |
| 37 | Falha do sistema |
| 39 | Falha do MOS de carga |
| 40 | Falha do MOS de descarga |
| 41 | Falha no sensor de temperatura |
| 42 | Falha de célula |
| 43 | Falha de comunicação de amostragem |
| **61** | **Falha de comunicação com o BMS** — com LIL/LIB-485 o inversor **corta a saída** |

## 4529 — Aviso (0 = sem aviso) 🟡

### Inversor (manual 5.10)

| Código | Aviso |
|---|---|
| 01 | Ventilador travado com o inversor ligado |
| 03 | Bateria sobrecarregada |
| 04 | Bateria baixa |
| 07 | Sobrecarga |
| 10 | Redução de potência de saída |
| 15 | Energia FV baixa |
| E9 | Equalização em andamento (código numérico desconhecido) |
| bP | Bateria não conectada (código numérico desconhecido) |

### Bateria / BMS ("Battery Alarm Code")

| Código | Aviso |
|---|---|
| 21–26 | Iguais às falhas 21–26 |
| 27–30 | Temperatura de célula fora da faixa (mesma ordem das falhas) |
| 34 | Capacidade da bateria muito baixa |
| 44 | Desequilíbrio de tensão entre células |
| 45 | Desequilíbrio de temperatura entre células |
| 46 | Alarme de comunicação interna |

Código desconhecido → mostrar "Código N".

## Alertas recomendados no Home Assistant

- Falha ≠ 0 → notificação imediata com o texto.
- Falha 61 → notificação **crítica**: "Comunicação com o BMS perdida — o inversor pode cortar a saída."
- Aviso ≠ 0 por mais de 2 min → notificação normal.
- Ponte sem dados por mais de 5 min → notificação.
