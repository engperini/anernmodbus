# 11 — Incidente: perda de dados no Raspberry Pi

## O que aconteceu

O trabalho de 13 e 14/11 (painel, ponte, commits, backups e até o histórico do agente) sumiu duas vezes depois de reboots do Pi (14/11 00:37 e ~13:20). Nas duas vezes tudo voltou para o mesmo ponto: 13/11 por volta de 00:10.

## Evidências (coletadas em 14/11 14:37)

- Último registro do histórico do agente: 13/11 00:06.
- Últimos arquivos realmente gravados no disco: 13/11 01:10–01:11 (os arquivos mais novos são do `apt`, que grava a data do servidor, não a hora local).
- `journalctl --list-boots`: só existem o boot que termina em 13/11 01:09:49 e o boot atual. Os dias seguintes não deixaram registro.
- Final do journal anterior: **"Undervoltage detected!" repetido** e, às 01:01, journal corrompido.
- Commits `438a250` / `7872e68` e arquivos com os SHA-256 informados não existem em lugar nenhum do disco.

## Conclusão

Após a queda de tensão de 13/11 01:09, causada pelas **quedas de energia frequentes**, o cartão SD passou a não gravar de forma permanente. O sistema seguia funcionando com as gravações na memória (cache), e tudo era perdido no reboot.

## Teste para confirmar sem reboot

```bash
dd if=/dev/urandom of=/home/pi/teste_sd.bin bs=1M count=20 oflag=direct status=none; sync
sha256sum /home/pi/teste_sd.bin
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sha256sum /home/pi/teste_sd.bin        # se mudar ou falhar → cartão não grava
rm /home/pi/teste_sd.bin
vcgencmd get_throttled                  # ≠ 0x0 → houve subtensão
sudo dmesg | grep -iE 'mmc|voltage|I/O error|read-only' | tail -20
```

Teste definitivo: criar um arquivo, `sync`, reiniciar e ver se ele continua lá.

## Prevenção

1. **Fonte oficial** do Raspberry Pi 5 (27 W, 5 V / 5 A).
2. **Nobreak** ou módulo UPS para Pi 5 com desligamento automático seguro.
3. **Cartão novo de qualidade ou SSD** (NVMe/USB), muito mais resistente.
4. Desligar sempre com `sudo shutdown -h now`, nunca tirando da tomada.
5. **Git com remoto** (GitHub privado) para a configuração do HA e a ponte; `git push` a cada mudança.
6. Backups automáticos do HA guardados fora do Pi.
7. Validar persistência com reboot real depois de mudanças importantes.
