# Selects em preparação — NÃO habilitar sem confirmação no display

Nenhum MQTT `select`, command_topic, subscriber ou serviço de comando está instalado. Este documento é um plano de ligação, não uma configuração ativa do Home Assistant.

| Controle | Leitura (03) | Escrita (06) | Opções/enum |
| --- | ---: | ---: | --- |
| Prioridade da saída | 4537 | 5018 | PENDENTE: programa 01, texto e códigos confirmados no display |
| Prioridade do carregador | 4536 | 5017 | PENDENTE: programa 16, texto e códigos confirmados no display |

Evidência no dispositivo: pré-leitura 4537=1 (`05 03 02 01 00 48 14`); envio único `05 06 13 9A 00 01 6D 25`; resposta idêntica; pós-leitura 4537=1. Isso valida o eco de escrita sem mudança para 5018/valor 1, não prova ainda 5017/enum de 4536 nem o efeito de mudar prioridade.

Antes de ativar cada select: preencher somente as opções confirmadas pelo proprietário no display; validar enum por evidência correspondente, não inferir OSO/CSO de códigos relacionados; implementar comando estritamente allowlisted para 5018/5017, eco Modbus válido, releitura do respectivo 45xx e estado do HA derivado da leitura (nunca otimista). Não incluir outros registradores. Validar rollback/efeito físico antes de expor mudança efetiva. Correntes, tensões de bateria e LED continuam sem caminho de escrita.

Interpretações provisórias para os sensores existentes, **sem renomear a entidade/discovery antes do display**: 4542 = tensão de saída; 4544/4545 = retorno para rede/bateria (SBU); 4548 = corte por bateria baixa; 4549 = equalização. Nomes MQTT atuais desses cinco campos ainda estão incorretos: não usar para controle.
