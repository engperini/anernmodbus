# 09 — Histórico da investigação

## 11/11 — Banco de baterias e primeiros passos
- Dimensionamento do banco: duas Felicity FLA24100 em paralelo, 1 m até o inversor. Etiqueta confirmou corrente máx. da bateria de 175 A.
- Decisão: paralelo com os cabos originais + 2 cabos de 50/70 mm² em diagonal até o inversor; proteção pelos disjuntores internos.
- Dongle Solar Plug RWB1 identificado no app Sun house. Objetivo: levar os dados ao Home Assistant sem a nuvem.

## 12/11 — Engenharia reversa
- Captura de tráfego do celular (PCAPdroid): só TLS celular → nuvem (`solar.siseli.com`); o comando nuvem → dongle não passa pelo celular.
- Ponte BLE local criada pelo agente (Hermes) no Raspberry Pi: leitura Modbus escravo 5 com CRC válido.
- Busca do LED (prog 39): comparação ON/OFF em 5001–5038 e 4522–4541 sem resultado. 5036 (LED em outro modelo) não variou.
- Análise do APK: rotas `/near/dtu/...`; com login, o protocolo do aparelho foi baixado: 6 quadros FC03, nenhum de escrita; atributo `rgbOnAndOffControlSetting` sem endereço.
- Descoberto que **4561 é o estado do LED** (1 ligado, 0 desligado).
- Escrita em 4561 e 5042 com FC06 → `05 86 82` (recusada). FC10 → `05 90 81` (não suportada).
- Alinhamento das sequências 4541–4553 ↔ 5022–5034: **deslocamento de +481** descoberto pelo agente.
- Mapa público PowMr encontrado: confirma +481 e FC06. **Lição: procurar primeiro o que já está documentado para o padrão de protocolo (escravo 5, registrador 4501), só depois testar.**

## 13/11 — Validação e painel
- 00:10 — escrita sem efeito em 5018 (valor atual) → eco idêntico: caminho de escrita validado.
- Rótulos corrigidos com o mapa (4542 = tensão de saída, 4544/4545 = volta rede/bateria, 4548 = corte, 4549 = equalização).
- Programas 01 e 16 conferidos no display: a numeração do PowMr **não** vale para os textos do Anern. Mapeamento real medido: 16 → CSO 0, SNU 1, OSO 2 (testado pelo HA).
- Manual original fotografado: programas, códigos de falha/aviso, telas do BMS.
- Histórico de outro agente: prog 43 = 48 com BMS funcionando; bP = bateria não conectada (o agente tinha chamado de bypass).
- Painel com travas, Grupos A/B/C, códigos de falha/aviso em texto.
- 01:09 — **queda de tensão (undervoltage) e journal corrompido no Pi**. A partir daí, nada mais foi gravado de forma permanente (descoberto só em 14/11).

## 14/11 — Perdas e refinamento
- 00:37 — reboot do Pi: painel voltou para a versão de 13/11 00:10. Reconstrução feita a partir da especificação.
- 4501 = modo de operação (3 bateria, 4 bypass). 4535 e 4553 decodificados com bytes invertidos. 4512/4513 confirmados pelo app e pelo Solar2MQTT.
- Comparação do dump com o app Sun house (Data details): versão da CPU, nominais, corte da saída dupla em V e %, NTC.
- Telas do BMS no display: firmware difere do manual nas telas 2 e 3; dados do BMS fora do bloco Modbus.
- USB = 0 confirmado; corrente total 70 A escrita pelo HA.
- Segunda bateria instalada.
- ~13:20 — nova queda de energia e reboot: tudo voltou de novo para 13/11. Commits `438a250` e `7872e68` não existem mais no disco.
- Diagnóstico: o cartão SD parou de gravar após a queda de tensão de 13/11 01:09 (ver `11-incidente-perda-dados.md`).
- Este dossiê foi montado a partir da conversa para preservar todo o conhecimento.

## Lições
1. Procurar mapas públicos da família antes de testar escrita.
2. Testar escrita sempre com o valor atual primeiro (sem efeito).
3. Conferir textos de enum no display: a numeração de um irmão de família pode diferir.
4. Persistência só vale depois de um reboot real do Pi.
5. Guardar cópia fora do Pi (git remoto) a cada etapa.
6. Pi com quedas de energia precisa de nobreak; sem isso, o cartão SD se corrompe.
