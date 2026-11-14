# 07 — Especificação do painel no Home Assistant

Especificação da versão final (14/11/2026, prints em `images/06-dashboard-ha/v5-final-*`). Serve para reconstruir o painel do zero.

## Princípios

- Os controles **sempre mostram o valor lido** do inversor; as travas só bloqueiam a escrita.
- Nenhuma escrita automática: só quando o usuário muda um controle.
- Um ajuste por vez; validação antes de escrever; releitura depois.
- Nomes curtos, com o número do programa em todo item configurável; sem número de registrador nem "provável" no nome (status fica em docs).
- Mesma fonte e espaçamento em todos os cards; cards de entidades (sem tabela markdown, para manter o histórico ao tocar).
- Precisão: tensões e frequências com 1 casa; correntes e potências sem casas (`suggested_display_precision`). Os campos `number` em modo caixa podem mostrar "27V" em vez de "27.0 V" (limitação do HA, aceitável).

## Travas

| Entidade | Função |
|---|---|
| `input_boolean` "Modo edição do inversor" | Libera escrita dos Grupos A, B e D. Desliga sozinho em 10 min |
| `input_boolean` "Ajustes críticos" | Segunda trava, exigida pelo Grupo C |

## Grupos de controle

**Grupo A · prioridades** (select)
- Fonte de carga (16) → 5017: CSO / SNU / OSO
- Fonte de saída (01) → 5018: USB / SUB / SBU / MKS

**Grupo B · parâmetros** (number, modo caixa)

| Nome | Escrita | Faixa | Passo | Regra |
|---|---|---|---|---|
| Corrente total (02) | 5022 | 10–100 A | 10 | |
| Corrente rede (11) | 5024 | 2, 10…100 A | | ≤ corrente total |
| Volta rede (12) | 5025 | 21,0–25,5 V | 0,5 | |
| Volta bateria (13) | 5026 | 24,0–29,0 V | 0,5 | > volta rede |
| Carga bulk (26) | 5027 | 26,0–28,8 V | 0,1 | |
| Flutuação (27) | 5028 | 26,0–28,8 V | 0,1 | ≤ bulk |
| Corte bateria (29) | 5029 | 24,0–25,0 V | 0,1 | < volta rede |
| Equalização (31) | 5030 | 26,0–28,8 V | 0,1 | |
| Tempo equaliz. (33) | 5031 | 5–900 min | 5 | |
| Limite equaliz. (34) | 5032 | 5–900 min | 5 | |
| Intervalo equaliz. (35) | 5033 | 0–90 dias | 1 | |

Linha de ajuda: "Um ajuste por vez. Regras: corrente rede ≤ total; corte < volta rede < volta bateria; flutuação ≤ bulk."

**Grupo C · ajustes críticos** (duas travas + select que só prepara + botão compacto "Aplicar" com confirmação)
- Faixa CA (03) → 5019: APL / UPS
- Tipo de bateria (05) → 5020: AGM / FLD / USE / LIB / LIC / LIP / LIL
- Frequência (09) → 5021: 50 / 60 Hz
- Tensão de saída (10) → 5023: 220 / 230 / 240 V
- Avisos: "Lítio com BMS: manter LIL (05)." e "Rede local: 60 Hz / 220 V."

**Grupo D · liga/desliga** (switch, Modo edição; estado lido pelo bit do 4535)
Alarme (18) 5002 · Luz de fundo (20) 5004 · Reinício após sobrecarga (06) 5005 · Reinício após sobretemperatura (07) 5006 · Apito na falha da rede (22) 5007 · Tela padrão (19) 5008 · Bypass na sobrecarga (23) 5009 · Registro de falhas (25) 5010

**Sem controle:** programas 37 (grid-tie), 43 (=48, nunca alterar), 44, 45 e LED.

## Cards de leitura (ordem)

1. **Aviso:** "ATENÇÃO — confira o manual da bateria e os limites do BMS antes de alterar parâmetros de bateria. Rede: 60 Hz / 220 V. As travas desligam em 10 min. Ajustes críticos exigem as duas travas e confirmação."
2. Travas de edição
3. Grupo A · Grupo B · Grupo C · Grupo D
4. **Solar:** Tensão FV, Potência FV
5. **Bateria:** Tensão, SOC (BMS), Corrente de carga, Corrente de descarga
6. **Rede:** Tensão, Frequência
7. **Saída e consumo:** Tensão, Frequência, Potência ativa, Potência aparente, Uso da capacidade
8. **Equipamento:** Modo de operação (4501 em texto), Temperatura NTC, LED (leitura), Carga habilitada / Rede ativa / Na bateria (4553)
9. **Diagnóstico:** Falha (texto), Aviso (texto), Último resultado de ajuste, Dados recentes (<5 min), Equalização (30), Equalização imediata (36), Corte da saída dupla (42) V e %
10. **Pendências técnicas** (só itens em aberto — ver `10-pendencias.md`)
11. **Informações do equipamento:** Versão da CPU, potência nominal W/VA, tensão/corrente CA nominal, tensão nominal da bateria, tensão/frequência/corrente de saída nominais

Não repetir em cards de leitura os valores que os controles já mostram.

## MQTT e persistência

- Discovery MQTT com `retain` **e** reenvio quando o HA publicar `online` em `homeassistant/status` (senão as entidades somem a cada reinício do HA).
- Manter `unique_id`/`entity_id` estáveis ao renomear (mudar só o nome amigável) para não perder histórico.
- Dashboard em **YAML no caminho que o HA realmente carrega**, versionado em git e com cópia fora do Pi.
- Prova de persistência: **reboot real do Pi** (`sudo reboot`), não só reinício do HA.

## Painel em inglês (para pacote público futuro)

Nomes sugeridos: Charger source (16), Output source (01), Total charge current (02), Grid charge current (11), Back to grid (12), Back to battery (13), Bulk (26), Float (27), Low cutoff (29), Equalization (31/33/34/35), AC input range (03), Battery type (05), Output frequency (09), Output voltage (10), Alarm (18), Backlight (20), Restart on overload (06), Restart on over temperature (07), Beep on source loss (22), Return to default screen (19), Overload bypass (23), Fault record (25).
