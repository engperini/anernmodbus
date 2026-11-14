"""Conservative read-only decoding of observed Anern register blocks.

The neighboring-model PowMr map is a hint, not proof of each semantic on this
inverter. Raw codes are retained when their enums have not been verified.
"""
from tools.rwb1_ble_protocol import crc16_modbus

# Key, Portuguese name, unit, device class, state class, factor, precision
SETTINGS_FIELDS = [
    ('charger_priority_code', 'Código de prioridade da carga', None, None, None, 1, 0), # 4536
    ('output_priority_code', 'Código de prioridade da saída', None, None, None, 1, 0), # 4537
    ('input_range_code', 'Código de faixa de entrada', None, None, None, 1, 0), # 4538
    ('battery_type_code', 'Código do tipo de bateria', None, None, None, 1, 0), # 4539
    ('frequency_mode_code', 'Código de frequência configurada', None, None, None, 1, 0), # 4540
    ('max_charge_current', 'Corrente máxima de carga configurada', 'A', 'current', 'measurement', 1, 0), #4541
    ('max_grid_charge_current', 'Corrente máxima de carga pela rede', 'A', 'current', 'measurement', 1, 0), #4542
    ('low_battery_warning', 'Limite de aviso de bateria fraca', 'V', 'voltage', 'measurement', .1, 1), #4544
    ('low_battery_shutdown', 'Limite de desligamento da bateria', 'V', 'voltage', 'measurement', .1, 1), #4545
    ('bulk_charge_voltage', 'Tensão de carga principal configurada', 'V', 'voltage', 'measurement', .1, 1), #4546
    ('float_charge_voltage', 'Tensão de flutuação configurada', 'V', 'voltage', 'measurement', .1, 1), #4547
    ('back_to_grid_voltage', 'Tensão configurada de retorno à rede', 'V', 'voltage', 'measurement', .1, 1), #4548
    ('back_to_battery_voltage', 'Tensão configurada de retorno à bateria', 'V', 'voltage', 'measurement', .1, 1), #4549
    ('led_state', 'Estado LED (registro 4561)', None, None, None, 1, 0), #4561; observed physical ON/OFF
    ('error_code', 'Código de falha (registro 4530)', None, None, None, 1, 0),
    ('config_flags_raw', 'Configurações brutas (registro 4535)', None, None, None, 1, 0),
    ('config_bits_set', 'Bits ativos (registro 4535)', None, None, None, 1, 0),
]
# Provisional Anern interpretation pending display programs 01/02/05/10/12/13/16/26/27/29:
# 4542 = output voltage (220 V, NOT grid charge current);
# 4544/4545 = back-to-grid/back-to-battery SBU thresholds (24.5/27.0 V);
# 4548 = low-battery cutoff (24.0 V); 4549 = equalization (27.0 V).
# Existing MQTT keys, discovery names and HA entity IDs are intentionally unchanged
# until display text/values confirm semantics. Do not use current mislabels for controls.
# Explicit register mapping: skips unverified fields and avoids accidental offsets.
REGISTERS = {
    'charger_priority_code':4536, 'output_priority_code':4537,
    'input_range_code':4538, 'battery_type_code':4539,
    'frequency_mode_code':4540, 'max_charge_current':4541,
    'max_grid_charge_current':4542, 'low_battery_warning':4544,
    'low_battery_shutdown':4545, 'bulk_charge_voltage':4546,
    'float_charge_voltage':4547, 'back_to_grid_voltage':4548,
    'back_to_battery_voltage':4549, 'led_state':4561,
}
# Bit positions are exposed without importing unvalidated meanings from the
# related-model register map.
def flag_values(raw):
    return {bit: True for bit in range(16) if raw & (1 << bit)}

def read_request(start, count):
    if (start,count) not in {(4530,1),(4535,1),(4536,29)}:
        raise ValueError('read outside allowlist')
    body = bytes((5,3)) + start.to_bytes(2,'big') + count.to_bytes(2,'big')
    return body + crc16_modbus(body).to_bytes(2,'little')

def decode_read_block(frame, count):
    if not (1 <= count <= 29) or len(frame) != 5+count*2 or frame[:3] != bytes((5,3,count*2)):
        raise ValueError('unexpected Modbus response shape')
    if crc16_modbus(frame[:-2]) != int.from_bytes(frame[-2:],'little'):
        raise ValueError('invalid Modbus CRC')
    return [int.from_bytes(frame[i:i+2],'little') for i in range(3,len(frame)-2,2)]

def map_settings(words, flags_raw, error_code):
    if len(words) != 29:
        raise ValueError('expected 29 registers from 4536')
    values={key: round(words[reg-4536]*factor,precision)
            for key, _name, _unit, _dc, _sc, factor,precision in SETTINGS_FIELDS
            if (reg:=REGISTERS.get(key)) is not None}
    values['config_flags_raw']=flags_raw
    values['config_bits_set']=','.join(map(str,flag_values(flags_raw))) or 'nenhum'
    values['error_code']=error_code
    return values
