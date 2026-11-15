"""Register map, decoding and write validation for the Anern AN-SCI-ECO-4200.

Source of truth: docs/03-mapa-registradores.md, docs/04-programas-display.md and
docs/05-codigos-falha-aviso.md of this repository.

Modbus over the RWB1 dongle: slave 5, read FC03 on 4501-4564 (one block of 64
works), write only FC06 on (read register + 481). The dongle returns register
words little-endian; the two bitmask registers 4535 and 4553 come with the
bytes swapped relative to the PowMr map, so they are swapped back here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from tools.rwb1_ble_protocol import crc16_modbus

SLAVE = 5
BLOCK_START = 4501
BLOCK_COUNT = 64            # 4501..4564
WRITE_OFFSET = 481          # write register = read register + 481


# ---------------------------------------------------------------- frames

def read_request(start: int = BLOCK_START, count: int = BLOCK_COUNT) -> bytes:
    if not (BLOCK_START <= start and start + count <= BLOCK_START + BLOCK_COUNT and count >= 1):
        raise ValueError("read outside 4501-4564")
    body = bytes((SLAVE, 3)) + start.to_bytes(2, "big") + count.to_bytes(2, "big")
    return body + crc16_modbus(body).to_bytes(2, "little")


def decode_read(frame: bytes, count: int) -> List[int]:
    if len(frame) != 5 + 2 * count or frame[:3] != bytes((SLAVE, 3, 2 * count)):
        raise ValueError("unexpected Modbus response shape")
    if crc16_modbus(frame[:-2]) != int.from_bytes(frame[-2:], "little"):
        raise ValueError("invalid Modbus CRC")
    return [int.from_bytes(frame[i:i + 2], "little") for i in range(3, len(frame) - 2, 2)]


def write_request(register: int, value: int) -> bytes:
    if not 0 <= value <= 0xFFFF:
        raise ValueError("value out of 16-bit range")
    body = bytes((SLAVE, 6)) + register.to_bytes(2, "big") + value.to_bytes(2, "big")
    return body + crc16_modbus(body).to_bytes(2, "little")


def check_write_echo(request: bytes, response: bytes) -> None:
    """FC06 must echo the request exactly. Raise WriteRefused / ValueError otherwise."""
    if response == request:
        return
    if len(response) == 5 and response[:2] == bytes((SLAVE, 0x86)):
        raise WriteRefused(f"inversor recusou (código {response[2]:#04x})")
    raise ValueError(f"resposta inesperada: {response.hex(' ')}")


class WriteRefused(Exception):
    """The inverter answered with an exception frame: never retry."""


def swap16(value: int) -> int:
    return ((value & 0xFF) << 8) | (value >> 8)


# ---------------------------------------------------------------- texts

OPERATION_MODES = {
    0: "Ligando", 1: "Espera", 2: "Rede", 3: "Bateria",
    4: "Bypass (rede direto)", 5: "Carregando", 6: "Falha",
}

FAULTS = {
    1: "Ventilador travado (inversor desligado)", 2: "Sobretemperatura",
    3: "Tensão da bateria alta", 4: "Tensão da bateria baixa",
    5: "Curto na saída ou sobretemperatura interna", 6: "Tensão de saída alta",
    7: "Sobrecarga (tempo esgotado)", 8: "Tensão do barramento alta",
    9: "Falha na partida suave do barramento",
    21: "BMS: sobretensão de célula", 22: "BMS: subtensão de célula",
    23: "BMS: sobretensão do pack", 24: "BMS: subtensão do pack",
    25: "BMS: sobrecorrente de carga", 26: "BMS: sobrecorrente de descarga",
    27: "BMS: sobretemperatura de célula na carga", 28: "BMS: sobretemperatura de célula na descarga",
    29: "BMS: subtemperatura de célula na carga", 30: "BMS: subtemperatura de célula na descarga",
    31: "BMS: sobretemperatura ambiente", 32: "BMS: subtemperatura ambiente",
    33: "BMS: sobretemperatura do MOS", 35: "BMS: curto-circuito na bateria",
    36: "BMS: sobretensão de carga", 37: "BMS: falha do sistema",
    39: "BMS: falha do MOS de carga", 40: "BMS: falha do MOS de descarga",
    41: "BMS: falha no sensor de temperatura", 42: "BMS: falha de célula",
    43: "BMS: falha de comunicação de amostragem",
    51: "Sobrecorrente ou surto", 52: "Tensão do barramento baixa",
    53: "Falha na partida suave do inversor", 55: "Tensão CC na saída CA",
    57: "Falha no sensor de corrente", 58: "Tensão de saída baixa",
    59: "Tensão FV acima do limite",
    61: "Comunicação com o BMS perdida (o inversor pode cortar a saída)",
}

WARNINGS = {
    1: "Ventilador travado (inversor ligado)", 3: "Bateria sobrecarregada",
    4: "Bateria baixa", 7: "Sobrecarga", 10: "Redução de potência de saída",
    15: "Energia FV baixa",
    21: "BMS: sobretensão de célula", 22: "BMS: subtensão de célula",
    23: "BMS: sobretensão do pack", 24: "BMS: subtensão do pack",
    25: "BMS: sobrecorrente de carga", 26: "BMS: sobrecorrente de descarga",
    27: "BMS: temperatura de célula alta na carga", 28: "BMS: temperatura de célula alta na descarga",
    29: "BMS: temperatura de célula baixa na carga", 30: "BMS: temperatura de célula baixa na descarga",
    34: "BMS: capacidade muito baixa", 44: "BMS: desequilíbrio de tensão entre células",
    45: "BMS: desequilíbrio de temperatura entre células", 46: "BMS: alarme de comunicação interna",
}


def code_text(code: int, table: Dict[int, str]) -> str:
    if code == 0:
        return "Nenhum"
    return f"{code:02d} · {table.get(code, f'Código {code}')}"


# ---------------------------------------------------------------- telemetry
# key -> (register, scale, precision). Keys of the original 13/11 bridge are kept
# so Home Assistant keeps the entity history.
TELEMETRY: Dict[str, Tuple[int, float, int]] = {
    "status": (4501, 1, 0),
    "grid_voltage": (4502, 0.1, 1),
    "grid_frequency": (4503, 0.1, 1),
    "pv_voltage": (4504, 0.1, 1),
    "pv_power": (4505, 1, 0),
    "battery_voltage": (4506, 0.1, 1),
    "battery_soc": (4507, 1, 0),
    "battery_charge_current": (4508, 1, 0),
    "battery_discharge_current": (4509, 1, 0),
    "output_voltage": (4510, 0.1, 1),
    "output_frequency": (4511, 0.1, 1),
    "load_apparent_power": (4512, 1, 0),
    "load_active_power": (4513, 1, 0),
    "load_percent": (4514, 1, 0),
    "dual_cutoff_voltage": (4517, 0.1, 1),
    "rated_power": (4521, 1, 0),
    "rated_apparent_power": (4522, 1, 0),
    "rated_ac_voltage": (4523, 1, 0),
    "rated_ac_current": (4524, 1, 0),
    "rated_battery_voltage": (4525, 0.1, 1),
    "rated_output_voltage": (4526, 1, 0),
    "rated_frequency": (4527, 0.1, 1),
    "rated_output_current": (4528, 1, 0),
    "warning_code": (4529, 1, 0),
    "fault_code": (4530, 1, 0),
    "dual_cutoff_percent": (4534, 1, 0),
    "ntc_temperature": (4557, 1, 0),
    "led_state": (4561, 1, 0),
}

CONFIG_FLAGS_REG = 4535
STATUS_FLAGS_REG = 4553

# 4535 (after swap): bit -> (key, program, write register or None)
CONFIG_BITS = {
    0x0001: ("fault_record", 25, 5010),
    0x0002: ("equalization", 30, None),
    0x0004: ("equalization_now", 36, None),
    0x0100: ("alarm", 18, 5002),
    0x0400: ("backlight", 20, 5004),
    0x0800: ("restart_overload", 6, 5005),
    0x1000: ("restart_overtemp", 7, 5006),
    0x2000: ("beep_source_loss", 22, 5007),
    0x4000: ("default_screen", 19, 5008),
    0x8000: ("overload_bypass", 23, 5009),
}

# 4553 (after swap), provisional (docs/10)
STATUS_BITS = {
    "on_battery": 0x0100,
    "grid_active": 0x0200 | 0x2000,
    "charge_enabled": 0x4000,
}


def reg(words: List[int], register: int) -> int:
    return words[register - BLOCK_START]


def decode_block(words: List[int]) -> Dict[str, Any]:
    if len(words) != BLOCK_COUNT:
        raise ValueError(f"expected {BLOCK_COUNT} registers from {BLOCK_START}")
    values: Dict[str, Any] = {}
    for key, (register, scale, precision) in TELEMETRY.items():
        raw = reg(words, register)
        values[key] = round(raw * scale, precision) if precision else int(round(raw * scale))
    values["operation_mode"] = OPERATION_MODES.get(values["status"], f"Código {values['status']}")
    values["fault_text"] = code_text(values["fault_code"], FAULTS)
    values["warning_text"] = code_text(values["warning_code"], WARNINGS)
    cpu = reg(words, 4518)
    values["cpu_version"] = f"U1 {cpu // 100:02d} {cpu % 100:02d}"
    values["led_text"] = {0: "LOF (desligado)", 1: "LON (ligado)"}.get(values["led_state"], str(values["led_state"]))

    flags = swap16(reg(words, CONFIG_FLAGS_REG))
    values["config_flags"] = flags
    for bit, (key, _prog, _write) in CONFIG_BITS.items():
        values[key] = "ON" if flags & bit else "OFF"

    status = swap16(reg(words, STATUS_FLAGS_REG))
    values["status_flags"] = status
    for key, mask in STATUS_BITS.items():
        values[key] = "ON" if status & mask else "OFF"

    for control in CONTROLS.values():
        if control.read_register is not None:
            values[control.key] = control.decode(reg(words, control.read_register))
    return values


# ---------------------------------------------------------------- controls

@dataclass(frozen=True)
class Control:
    key: str
    name: str
    group: str                      # A, B, C, D
    program: int
    write_register: int
    read_register: Optional[int] = None   # None for bits of 4535
    options: Tuple[str, ...] = ()         # select: option index = raw value
    option_values: Tuple[int, ...] = ()   # select: explicit raw values (when not 0..n)
    minimum: float = 0
    maximum: float = 0
    step: float = 1
    scale: float = 1                      # raw = value / scale
    unit: Optional[str] = None
    allowed: Tuple[float, ...] = ()       # explicit set of valid values
    bit: int = 0
    icon: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def kind(self) -> str:
        if self.group == "D":
            return "switch"
        if self.options:
            return "select"
        return "number"

    def decode(self, raw: int) -> Any:
        if self.options:
            values = self.option_values or tuple(range(len(self.options)))
            return self.options[values.index(raw)] if raw in values else f"? ({raw})"
        value = raw * self.scale
        return round(value, 1) if self.scale != 1 else int(value)

    def encode(self, value: Any) -> int:
        """UI value -> raw register value, validating the range of this control."""
        if self.kind == "switch":
            if value not in ("ON", "OFF"):
                raise ValueError("use ON ou OFF")
            return 1 if value == "ON" else 0
        if self.options:
            if value not in self.options:
                raise ValueError(f"opção inválida: {value}")
            values = self.option_values or tuple(range(len(self.options)))
            return values[self.options.index(value)]
        number = float(value)
        if self.allowed and not any(abs(number - a) < 1e-6 for a in self.allowed):
            raise ValueError(f"{self.name}: valores aceitos {', '.join(f'{a:g}' for a in self.allowed)}")
        if not (self.minimum - 1e-6 <= number <= self.maximum + 1e-6):
            raise ValueError(f"{self.name}: faixa {self.minimum:g}–{self.maximum:g} {self.unit or ''}".strip())
        steps = (number - self.minimum) / self.step
        if not self.allowed and abs(steps - round(steps)) > 1e-6:
            raise ValueError(f"{self.name}: passo {self.step:g}")
        return int(round(number / self.scale))


def _c(**kw) -> Control:
    return Control(**kw)


_CONTROL_LIST = [
    # Grupo A · prioridades
    _c(key="charger_source", name="Fonte de carga (16)", group="A", program=16,
       read_register=4536, write_register=5017, options=("CSO", "SNU", "OSO"), icon="mdi:battery-charging"),
    _c(key="output_source", name="Fonte de saída (01)", group="A", program=1,
       read_register=4537, write_register=5018, options=("USB", "SUB", "SBU", "MKS"), icon="mdi:transmission-tower"),
    # Grupo B · parâmetros
    _c(key="total_charge_current", name="Corrente total (02)", group="B", program=2,
       read_register=4541, write_register=5022, minimum=10, maximum=100, step=10, unit="A"),
    _c(key="grid_charge_current", name="Corrente rede (11)", group="B", program=11,
       read_register=4543, write_register=5024, minimum=2, maximum=100, step=1, unit="A",
       allowed=(2, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)),
    _c(key="back_to_grid", name="Volta rede (12)", group="B", program=12,
       read_register=4544, write_register=5025, minimum=21.0, maximum=25.5, step=0.5, scale=0.1, unit="V"),
    _c(key="back_to_battery", name="Volta bateria (13)", group="B", program=13,
       read_register=4545, write_register=5026, minimum=24.0, maximum=29.0, step=0.5, scale=0.1, unit="V"),
    _c(key="bulk_voltage", name="Carga bulk (26)", group="B", program=26,
       read_register=4546, write_register=5027, minimum=26.0, maximum=28.8, step=0.1, scale=0.1, unit="V"),
    _c(key="float_voltage", name="Flutuação (27)", group="B", program=27,
       read_register=4547, write_register=5028, minimum=26.0, maximum=28.8, step=0.1, scale=0.1, unit="V"),
    _c(key="low_cutoff", name="Corte bateria (29)", group="B", program=29,
       read_register=4548, write_register=5029, minimum=24.0, maximum=25.0, step=0.1, scale=0.1, unit="V"),
    _c(key="equalization_voltage", name="Equalização (31)", group="B", program=31,
       read_register=4549, write_register=5030, minimum=26.0, maximum=28.8, step=0.1, scale=0.1, unit="V"),
    _c(key="equalization_time", name="Tempo equaliz. (33)", group="B", program=33,
       read_register=4550, write_register=5031, minimum=5, maximum=900, step=5, unit="min"),
    _c(key="equalization_timeout", name="Limite equaliz. (34)", group="B", program=34,
       read_register=4551, write_register=5032, minimum=5, maximum=900, step=5, unit="min"),
    _c(key="equalization_interval", name="Intervalo equaliz. (35)", group="B", program=35,
       read_register=4552, write_register=5033, minimum=0, maximum=90, step=1, unit="d"),
    # Grupo C · ajustes críticos (select prepara, botão aplica)
    _c(key="ac_input_range", name="Faixa CA (03)", group="C", program=3,
       read_register=4538, write_register=5019, options=("APL", "UPS")),
    _c(key="battery_type", name="Tipo de bateria (05)", group="C", program=5,
       read_register=4539, write_register=5020, options=("AGM", "FLD", "USE", "LIB", "LIC", "LIP", "LIL")),
    _c(key="output_frequency_setting", name="Frequência (09)", group="C", program=9,
       read_register=4540, write_register=5021, options=("50 Hz", "60 Hz")),
    _c(key="output_voltage_setting", name="Tensão de saída (10)", group="C", program=10,
       read_register=4542, write_register=5023, options=("220 V", "230 V", "240 V"), option_values=(220, 230, 240)),
]
# Grupo D · liga/desliga (estado no 4535)
for _bit, (_key, _prog, _write) in CONFIG_BITS.items():
    if _write is None:
        continue
    _CONTROL_LIST.append(_c(key=_key, name={
        "fault_record": "Registro de falhas (25)", "alarm": "Alarme (18)", "backlight": "Luz de fundo (20)",
        "restart_overload": "Reinício após sobrecarga (06)", "restart_overtemp": "Reinício após sobretemperatura (07)",
        "beep_source_loss": "Apito na falha da rede (22)", "default_screen": "Tela padrão (19)",
        "overload_bypass": "Bypass na sobrecarga (23)"}[_key],
        group="D", program=_prog, write_register=_write, bit=_bit))

CONTROLS: Dict[str, Control] = {c.key: c for c in _CONTROL_LIST}

for _c_ in CONTROLS.values():
    if _c_.read_register is not None and _c_.write_register != _c_.read_register + WRITE_OFFSET:
        raise AssertionError(f"{_c_.key}: write register must be read + {WRITE_OFFSET}")


# ---------------------------------------------------------------- rules

def validate_rules(current: Dict[str, Any], key: str, value: Any) -> None:
    """Cross-parameter rules of Grupo B, checked with the value being written."""
    v = dict(current)
    v[key] = float(value) if CONTROLS[key].kind == "number" else value

    def num(k: str) -> float:
        return float(v[k])

    if key in ("grid_charge_current", "total_charge_current") and num("grid_charge_current") > num("total_charge_current"):
        raise ValueError("corrente rede (11) deve ser ≤ corrente total (02)")
    if key in ("low_cutoff", "back_to_grid", "back_to_battery"):
        if not num("low_cutoff") < num("back_to_grid"):
            raise ValueError("corte (29) deve ser < volta rede (12)")
        if not num("back_to_grid") < num("back_to_battery"):
            raise ValueError("volta rede (12) deve ser < volta bateria (13)")
    if key in ("float_voltage", "bulk_voltage") and num("float_voltage") > num("bulk_voltage"):
        raise ValueError("flutuação (27) deve ser ≤ bulk (26)")


def required_locks(control: Control) -> Tuple[str, ...]:
    return ("edit", "critical") if control.group == "C" else ("edit",)
