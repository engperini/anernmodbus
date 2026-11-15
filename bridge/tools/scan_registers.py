"""Read-only Modbus register scan over the RWB1 dongle (FC03 only, never writes).

Reads every address of the given ranges in chunks; a chunk that the inverter refuses
(exception 05 83 ..) is retried register by register, so invalid addresses are mapped
too. Results go to a CSV: address, value, status.

Stop the bridge first (only one BLE connection at a time):
    systemctl --user stop rwb1-ble
    .venv/bin/python tools/scan_registers.py 4401-4500 4565-4700 --out scan.csv
    systemctl --user start rwb1-ble
"""
import argparse
import asyncio
import csv
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge import RWB1Session, load_env_file  # noqa: E402
from tools.rwb1_ble_protocol import crc16_modbus, derive_key  # noqa: E402


def request(start: int, count: int) -> bytes:
    body = bytes((5, 3)) + start.to_bytes(2, "big") + count.to_bytes(2, "big")
    return body + crc16_modbus(body).to_bytes(2, "little")


def parse(frame: bytes, count: int):
    if len(frame) == 5 + 2 * count and frame[:3] == bytes((5, 3, 2 * count)) \
            and crc16_modbus(frame[:-2]) == int.from_bytes(frame[-2:], "little"):
        return [int.from_bytes(frame[i:i + 2], "little") for i in range(3, len(frame) - 2, 2)]
    return None


async def ask(session, start, count):
    """Return (words or None, status). An address range may get no reply at all."""
    try:
        frame = await session.query(request(start, count))
    except asyncio.TimeoutError:
        await asyncio.sleep(2)          # let a late reply drain before the next request
        return None, "no reply"
    words = parse(frame, count)
    return words, "ok" if words is not None else "refused " + frame.hex(" ")


async def scan(ranges, chunk, out):
    """Scan the ranges; reconnects and resumes when the BLE link drops."""
    load_env_file()
    rows = []
    todo = [(first, last) for first, last in ranges]
    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("address", "value", "status"))
        retries = 0
        while todo and retries < 10:
            try:
                async with RWB1Session(os.environ["RWB1_BLE_ADDRESS"], derive_key(os.environ["RWB1_DTU_ID"]),
                                       timeout=4) as s:
                    while todo:
                        addr, last = todo[0]
                        n = min(chunk, last - addr + 1)
                        words, status = await ask(s, addr, n)
                        if words is not None:
                            new = [(addr + i, w, "ok") for i, w in enumerate(words)]
                        elif status == "no reply" and n > 1:
                            w1, st1 = await ask(s, addr, 1)
                            new = [(addr, w1[0] if w1 else "", st1)] + [
                                (a, "", "skipped (chunk silent)") for a in range(addr + 1, addr + n)]
                        else:
                            new = []
                            for a in range(addr, addr + n):
                                w, st = await ask(s, a, 1)
                                new.append((a, w[0] if w else "", st))
                                await asyncio.sleep(0.2)
                        writer.writerows(new)
                        f.flush()
                        rows += new
                        print(f"{addr}-{addr + n - 1}: {sum(1 for r in new if r[2] == 'ok')} ok", flush=True)
                        todo[0] = (addr + n, last)
                        if addr + n > last:
                            todo.pop(0)
                        await asyncio.sleep(0.3)
            except Exception as exc:  # noqa: BLE001
                retries += 1
                print(f"BLE dropped ({exc!r}); reconnecting ({retries})", flush=True)
                await asyncio.sleep(5)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ranges", nargs="+", help="e.g. 4401-4500")
    p.add_argument("--chunk", type=int, default=10)
    p.add_argument("--out", default=f"scan-{time.strftime('%Y%m%d-%H%M')}.csv")
    a = p.parse_args()
    ranges = [tuple(map(int, r.split("-"))) for r in a.ranges]
    rows = asyncio.run(scan(ranges, a.chunk, a.out))
    ok = [r for r in rows if r[2] == "ok"]
    print(f"{len(rows)} addresses, {len(ok)} readable -> {a.out}")


if __name__ == "__main__":
    main()
