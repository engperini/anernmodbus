# 10 — Pendências

| Item | Situação | Como resolver |
|---|---|---|
| 4501 códigos 0, 1, 2, 5, 6 | não observados | anotar o valor quando o inversor estiver em espera, ligando, em falha etc. |
| 4553 flags de status | provável | conferir com a casa na bateria: "na bateria" deve ligar, "rede ativa" desligar |
| 4554 | prog 38 ou estado da bateria | à noite, sem carga: se continuar 2 é o prog 38 |
| 4555 / 4556 | desconhecidos (10 → 11) | observar ao longo de dias; comparar com campos do app |
| Prog 37 e 41 (valor 0) | registrador não identificado | mudar um deles sem efeito e ver qual registrador muda (ex.: 41 com 37 desligado) |
| Prog 44 (valor 1) | 4520 ou 4560 | mudar 44 para dIS e reler |
| 4519, 4516, 4558, 4559, 4562–4564 | desconhecidos | idem |
| LED (prog 39) | estado em 4561; escrita desconhecida | capturar o Bluetooth do celular (HCI snoop) enquanto alterna o LED pelo app em modo local; ou chamar `gen/device/config/write` com o valor atual |
| 4529 aviso | provável | confirmar quando aparecer um aviso real |
| Tela 2 do BMS ("910") | desconhecida | anotar junto com corrente, potência FV e consumo em momentos diferentes |
| Dados detalhados do BMS | fora do bloco Modbus | ler o BMS da Felicity direto (RS485/CAN) |
| Duas baterias no BMS | a confirmar | verificar se SOC/limites refletem as duas (cabo de comunicação/DIP) |
| Escritas 5019–5021, 5023–5033 e Grupo D | não testadas | primeiro uso: escrever o valor atual (eco), depois mudança real conferida no display |
