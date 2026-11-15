/*
 * Hand-curated table for the SOMA Carrier v1.3 rebuild.
 *
 * block        — schematic group (column order on the sheet)
 * pinNames     — cosmetic pin-name labels for generated symbols;
 *                when omitted the pad's net name is used (NC pads -> "NC")
 * lcsc         — verified LCSC catalogue equivalent (BOM note only; the
 *                extension always generates KiCad-exact symbols and
 *                footprints, it never substitutes library parts)
 */

export type BlockId = 'PWR' | 'V5' | 'UI' | 'MCU' | 'CAN' | 'MOT' | 'PER';

export interface PartSpec {
	block: BlockId;
	pinNames?: Record<string, string>;
	lcsc?: string;
	note?: string;
}

export const BLOCKS: Array<{ id: BlockId; title: string }> = [
	{ id: 'PWR', title: 'POWER INPUT + REVERSE POLARITY' },
	{ id: 'V5', title: '5V / MCU SUPPLY (Mini360 buck)' },
	{ id: 'UI', title: 'STATUS LEDs + BUZZER' },
	{ id: 'MCU', title: 'ESP32-S3 SOCKETS (DevKitC)' },
	{ id: 'CAN', title: 'CAN TRANSCEIVER + BUS-A' },
	{ id: 'MOT', title: 'MOTOR RELAY + E-STOP LOOP' },
	{ id: 'PER', title: 'PERIPHERALS + SENSORS' },
];

export const PARTS: Record<string, PartSpec> = {
	// ---- power input + reverse polarity protection
	J16: { block: 'PWR', pinNames: { 1: 'GND', 2: '+12V_IN' }, note: 'XT60 input' },
	J1: { block: 'PWR', note: '12V input terminal' },
	JP1: { block: 'PWR', pinNames: { 1: '+12V_IN', 2: '+12V_SW' }, note: 'PWR-ON jumper' },
	Q2: { block: 'PWR', pinNames: { 1: 'G', 2: 'D', 3: 'S' }, lcsc: 'C2564', note: 'IRF4905PBF reverse-polarity PMOS' },
	R10: { block: 'PWR', note: 'gate pull-down' },
	F1: { block: 'PWR', note: '10A blade fuse' },
	D4: { block: 'PWR', pinNames: { 1: 'A', 2: 'K' }, note: 'TVS 15V' },
	C1: { block: 'PWR' },
	C2: { block: 'PWR' },
	TP2: { block: 'PWR', pinNames: { 1: '+12V' } },
	TP1: { block: 'PWR', pinNames: { 1: 'GND' } },
	R7: { block: 'PWR', note: 'VSNS divider top' },
	R8: { block: 'PWR', note: 'VSNS divider bottom' },
	// ---- 5V supply
	J2: { block: 'V5', note: '5V input terminal' },
	J3: { block: 'V5', pinNames: { 1: 'VIN', 2: 'GND', 3: 'VOUT', 4: 'GND' }, note: 'Mini360 buck module socket' },
	D1: { block: 'V5', pinNames: { 1: 'K', 2: 'A' }, lcsc: undefined, note: '1N5820 +5V->+5V_MCU isolation' },
	C3: { block: 'V5' },
	C4: { block: 'V5' },
	C5: { block: 'V5' },
	C6: { block: 'V5' },
	// ---- status LEDs + buzzer
	D2: { block: 'UI', pinNames: { 1: 'K', 2: 'A' }, note: 'PWR LED' },
	R3: { block: 'UI' },
	D3: { block: 'UI', pinNames: { 1: 'K', 2: 'A' }, note: 'STAT LED' },
	R4: { block: 'UI' },
	BZ1: { block: 'UI', pinNames: { 1: '+', 2: '-' }, note: '5V buzzer' },
	Q1: { block: 'UI', pinNames: { 1: 'E', 2: 'B', 3: 'C' }, lcsc: 'C118536', note: '2N2222A buzzer driver' },
	R5: { block: 'UI', note: 'Q1 base resistor' },
	// ---- ESP32 sockets
	U1A: { block: 'MCU', note: 'DevKitC J3 socket 1x22' },
	U1B: { block: 'MCU', note: 'DevKitC J1 socket 1x22' },
	// ---- CAN + BUS-A
	U2: { block: 'CAN', pinNames: { 1: 'TXD', 2: 'GND', 3: 'VCC', 4: 'RXD', 5: 'VIO', 6: 'CANL', 7: 'CANH', 8: 'S' }, note: 'TJA1051T/3 SOIC-8' },
	R9: { block: 'CAN', note: '120R termination' },
	JP2: { block: 'CAN', pinNames: { 1: 'CAN_TERM', 2: 'CANL' }, note: 'CAN-TERM jumper' },
	J17: { block: 'CAN', note: 'CAN connector' },
	R1: { block: 'CAN', note: 'BUS-A isolation 1k' },
	J4: { block: 'CAN', note: 'BUS-A conn 1' },
	J5: { block: 'CAN', note: 'BUS-A conn 2' },
	// ---- motor relay + e-stop
	K1: { block: 'MOT', pinNames: { 1: 'COIL+', 2: 'COIL-', 3: 'NO', 5: 'COM' }, lcsc: 'C93716', note: 'SRD-12VDC-SL-A (Form A)' },
	Q3: { block: 'MOT', pinNames: { 1: 'E', 2: 'B', 3: 'C' }, lcsc: 'C118536', note: 'relay coil driver' },
	D5: { block: 'MOT', pinNames: { 1: 'K', 2: 'A' }, lcsc: 'C2457', note: '1N4007 flyback' },
	R11: { block: 'MOT', note: 'Q3 base resistor' },
	R12: { block: 'MOT', note: 'Q3 base pull-down' },
	J9: { block: 'MOT', note: 'ESTOP sense input' },
	J19: { block: 'MOT', pinNames: { 1: 'RLY_LOW', 2: 'RLY_SW' }, note: 'NC e-stop in coil loop' },
	J18: { block: 'MOT', note: 'switched motor out 1' },
	J20: { block: 'MOT', note: 'switched motor out 2' },
	// ---- peripherals + sensors
	J11: { block: 'PER', pinNames: { 1: 'GND', 2: '+3V3', 3: 'SCL1', 4: 'SDA1' }, note: 'OLED' },
	J12: { block: 'PER', pinNames: { 1: '+5V', 2: 'GND', 3: 'SCL1', 4: 'SDA1', 7: 'GND' }, note: 'IMU socket' },
	J13: { block: 'PER', pinNames: { 1: '+3V3', 2: 'GND', 3: 'ENC_B', 4: 'ENC_A', 5: 'ENC_SW' }, note: 'jog encoder' },
	J14: { block: 'PER', pinNames: { 1: 'GND', 2: 'NEO', 3: '+5V' }, note: 'NeoPixel' },
	J15: { block: 'PER', note: 'spare' },
	IR1: { block: 'PER', pinNames: { 1: 'OUT', 2: 'GND', 3: 'VCC' }, note: 'VS1838B IR receiver' },
	R6: { block: 'PER', note: 'DS18B20 pull-up 4.7k' },
	DSV: { block: 'PER', pinNames: { 1: 'V' }, note: 'DS18B20 VCC pad' },
	DST: { block: 'PER', pinNames: { 1: 'DQ' }, note: 'DS18B20 data pad' },
	DSG: { block: 'PER', pinNames: { 1: 'G' }, note: 'DS18B20 GND pad' },
};

/** Nets that get power/ground net flags instead of net ports. */
export const POWER_NETS = new Set([
	'+12V_IN', '+12V_SW', '+12V_RP', '+12V', '+12V_MOT',
	'+5V', '+5V_MCU', '+3V3',
]);
export const GROUND_NETS = new Set(['GND']);
