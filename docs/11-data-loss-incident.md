# 11 — Incident: data loss on the Raspberry Pi

## What happened

The work of 11/13 and 11/14 (dashboard, bridge, commits, backups and even the agent's history) vanished twice after Pi reboots (11/14 00:37 and ~13:20). Both times everything went back to the same point: 11/13 around 00:10.

## Evidence (collected on 11/14 14:37)

- Last entry in the agent's history: 11/13 00:06.
- Last files actually written to disk: 11/13 01:10–01:11 (the newer files are from `apt`, which records the server's date, not local time).
- `journalctl --list-boots`: only the boot ending at 11/13 01:09:49 and the current boot exist. The following days left no record.
- End of the previous journal: **"Undervoltage detected!" repeated** and, at 01:01, a corrupted journal.
- Commits `438a250` / `7872e68` and files with the reported SHA-256 hashes exist nowhere on the disk.

## Conclusion

After the undervoltage of 11/13 01:09, caused by the **frequent power outages**, the SD card stopped persisting writes. The system kept running with writes held in memory (cache), and everything was lost on reboot.

## Test to confirm without rebooting

```bash
dd if=/dev/urandom of=/home/pi/teste_sd.bin bs=1M count=20 oflag=direct status=none; sync
sha256sum /home/pi/teste_sd.bin
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
sha256sum /home/pi/teste_sd.bin        # if it changes or fails → card is not writing
rm /home/pi/teste_sd.bin
vcgencmd get_throttled                  # ≠ 0x0 → undervoltage occurred
sudo dmesg | grep -iE 'mmc|voltage|I/O error|read-only' | tail -20
```

Definitive test: create a file, `sync`, reboot and check whether it is still there.

## Prevention

1. **Official power supply** for the Raspberry Pi 5 (27 W, 5 V / 5 A).
2. **UPS** or a Pi 5 UPS module with automatic safe shutdown.
3. **New quality card or SSD** (NVMe/USB), much more robust.
4. Always shut down with `sudo shutdown -h now`, never by pulling the plug.
5. **Git with a remote** (private GitHub) for the HA configuration and the bridge; `git push` after every change.
6. Automatic HA backups stored off the Pi.
7. Validate persistence with a real reboot after important changes.
