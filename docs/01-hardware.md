# 01 — Hardware

## Inversor: Anern AN-SCI-ECO-4200

Dados da etiqueta (foto: `images/01-hardware/etiqueta-inversor-an-sci-eco-4200.jpg`):

| Grupo | Parâmetro | Valor |
|---|---|---|
| Geral | Modelo | AN-SCI-ECO-4200 |
| | Temperatura de operação | −10 a 50 °C |
| Entrada FV | Tensão nominal | 240 Vcc |
| | Vmax FV | 500 Vcc |
| | Faixa de entrada FV | 60–450 Vcc |
| | Faixa MPPT a plena carga | 240–450 Vcc |
| | Corrente máx. FV | 18 A |
| | Potência FV máx. | 6200 W |
| | Corrente máx. de carga solar | 120 A |
| Saída CA | Tensão nominal | 220/230/240 Vca |
| | Corrente nominal | 18,2 A |
| | Eficiência máx. | 97% |
| | Frequência | 50/60 Hz |
| Duas saídas | Carga total / principal | 4200 W / 4200 W |
| | Segunda saída máx. | 1400 W (prog 45 = 33%) |
| | Corte / retorno da carga principal | 26 / 27 Vcc |
| Entrada CA | Tensão nominal | 230 Vca |
| | Corrente máx. de entrada | 30 A |
| | Surto | 8400 VA |
| | Corrente máx. de carga CA | 100 A |
| Bateria | Tensão | 24 Vcc |
| | **Corrente máx. da bateria** | **175 A** |

Firmware da CPU principal: **U1 75 11** (registrador 4518 = 7511).

Observações:
- O manual se contradiz sobre o limite MPPT (450 V na pág. 8, 500 V na pág. 39). Use a etiqueta.
- A tabela técnica do manual fala em 50 Hz; o equipamento opera em 60 Hz sem problema (prog 09).
- Testado: o inversor parte e alimenta cargas só com FV, **sem bateria** conectada.

## Baterias

- **Felicity FLA24100** — LiFePO4 25,6 V / 100 Ah, BMS com RS485/CAN, disjuntor e fusível internos.
- Recomendado: 100 A contínuos por bateria, 150 A por 15 s. Carga máx. 28,8 V, corte 24 V.
- Configuração atual: **duas baterias em paralelo**.
- Comunicação BMS ↔ inversor **funciona** com prog 05 = LIL e prog 43 = 48 (ver `06-bms.md`).

## Ligação do banco (decisão final)

Banco a 1 m do inversor, baterias lado a lado:

- Paralelo entre as baterias com os cabos originais da Felicity (35 mm²): + com +, − com −.
- Até o inversor: **2 cabos de 50 mm² (ou 70 mm²), 1 m, em diagonal**: positivo de uma bateria e negativo da outra, para dividir a corrente por igual.
- Terminais de 50 mm² com o **mesmo furo** do terminal da Felicity (provável M8), prensados com prensa hidráulica. Dois terminais empilhados no borne, metal com metal; arruela só por cima.
- Proteção: os disjuntores internos das baterias servem de seccionamento. (Uma alternativa mais robusta, com barramento de 300 A, fusível NH1 200 A gG e base NH1, foi avaliada e documentada, mas não era necessária com o banco a 1 m.)
- Antes de juntar uma bateria nova: desligar tudo e igualar as tensões (carregar as duas a 100%).

Corrente de projeto: 4200 W ÷ (24 V × 0,93) ≈ 188 A no pior caso; o inversor limita a 175 A.

## Dongle: Solar Plug RWB1

- Datalogger Wi-Fi/BLE da Siseli, app **Sun house** (`com.ssli.next.solar`, v1.1.5).
- Firmware: **V1.44.5_SolarV70**, Type NO 04.
- Ligado na porta de comunicação do inversor; manda dados para a nuvem do app e aceita conexão BLE local.
- **Aceita uma conexão BLE por vez**: o app em modo Bluetooth e a ponte não funcionam ao mesmo tempo.
- Fotos: `images/01-hardware/dongle-rwb1-*.jpg`.

## Servidor: Raspberry Pi 5

- Roda Home Assistant (config em `/home/pi/.homeassistant`), Mosquitto e a ponte BLE (`/home/pi/solar-rwb1-ble`).
- Adaptador Bluetooth interno.
- **Precisa de fonte oficial de 27 W (5 V / 5 A)** e, por causa das quedas de energia frequentes, de um **nobreak/UPS**. Ver `11-incidente-perda-dados.md`.
