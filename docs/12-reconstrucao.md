# 12 — Reconstrução

## Ordem

1. **Energia:** fonte oficial 27 W + nobreak/UPS.
2. **Armazenamento:** cartão novo ou SSD; instalar Raspberry Pi OS 64-bit.
3. **Copiar do cartão antigo** (somente leitura, em outro computador ou leitor USB): `/home/pi/solar-rwb1-ble/` (ponte de 13/11, com os detalhes BLE) e `/home/pi/.homeassistant/` (configuração).
4. Instalar Home Assistant, Mosquitto e a ponte; serviço systemd.
5. Criar repositório git privado para HA + ponte, com remoto (`git push`).
6. Teste de persistência: arquivo de teste + reboot real.
7. Reconstruir o painel com a instrução abaixo (ou manualmente com `07-home-assistant.md`).
8. Primeiro uso de cada escrita: valor atual (eco) → mudança real → conferir no display.

## Instrução pronta para um agente (Hermes ou outro)

```
Reconstrua a integração do inversor Anern AN-SCI-ECO-4200 no Home Assistant usando o dossiê deste repositório como fonte única (docs/02, 03, 05, 07, 08). Não escreva nada no inversor; eu testo as escritas.

1) Ponte BLE → MQTT: parta da ponte de 13/11 (BLE e CRC funcionando). Implemente o mapa de docs/03 (bytes invertidos em 4535 e 4553), o discovery com retain + reenvio no homeassistant/status=online, availability, reconexão com backoff, reset do Bluetooth após falhas repetidas e o fluxo seguro de escrita FC06 (ler → validar → escrever → eco → reler; recusa = não repetir; log no sensor "Último resultado de ajuste"). Só escreve com as travas do HA ligadas.
2) Painel: exatamente como docs/07 (travas, Grupos A–D, cards de leitura na ordem indicada, códigos de falha/aviso em texto de docs/05, alertas, pendências de docs/10, precisão, nomes com número do programa).
3) Persistência: dashboard em YAML no caminho que o HA carrega; tudo em git com push para o remoto a cada etapa; sync; prova com reboot REAL do Pi (sudo reboot) conferindo SHA-256 antes e depois.
4) Me mande prints de cada card e a lista de entidades.
```
