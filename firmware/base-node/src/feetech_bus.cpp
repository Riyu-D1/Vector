#include <Arduino.h>
#include "pins.h"
#include "config.h"
#include "feetech_bus.h"

/* UART1 = bus A — the only servo bus on carrier v1.3 */
static HardwareSerial BusA(1);

static HardwareSerial *bus = &BusA;

void ft_bus_init(void) {
    BusA.begin(FT_BAUD, SERIAL_8N1, PIN_BUSA_RX, PIN_BUSA_TX);
    BusA.setTimeout(FT_READ_TIMEOUT_MS);
}

/* send packet, eat the echo, return number of echo bytes consumed */
static void ft_send(const uint8_t *pkt, uint8_t n) {
    bus->write(pkt, n);
    bus->flush();                        /* wait for last stop bit */
    /* echo lands in RX as it is sent — drop it */
    uint32_t t0 = millis();
    uint8_t got = 0;
    while (got < n && (millis() - t0) < FT_READ_TIMEOUT_MS) {
        if (bus->available()) {
            bus->read();
            got++;
        }
    }
}

static int ft_recv(uint8_t *buf, int want, uint32_t timeout_ms) {
    uint32_t t0 = millis();
    int got = 0;
    while (got < want && (millis() - t0) < timeout_ms) {
        if (bus->available()) {
            buf[got++] = (uint8_t)bus->read();
            /* length known once header is in — stop early */
            if (got == 4 && buf[3] + 4 < want)
                want = buf[3] + 4;
        }
    }
    return got;
}

bool ft_ping(uint8_t id) {
    uint8_t pkt[FT_MAX_PACKET];
    uint8_t n = ft_build_ping(pkt, id);
    ft_send(pkt, n);
    uint8_t resp[FT_MAX_PACKET];
    int r = ft_recv(resp, sizeof(resp), FT_READ_TIMEOUT_MS);
    uint8_t rid, err; const uint8_t *p; uint8_t pn;
    return r >= 6 && ft_parse_response(resp, r, &rid, &err, &p, &pn) == 0
           && rid == id;
}

bool ft_write_reg(uint8_t id, uint8_t addr, const uint8_t *data, uint8_t n) {
    uint8_t pkt[FT_MAX_PACKET];
    uint8_t len = ft_build_write(pkt, id, addr, data, n);
    if (!len) return false;
    ft_send(pkt, len);
    /* writes still get a status response unless broadcast */
    if (id == FT_ID_BROADCAST) return true;
    uint8_t resp[FT_MAX_PACKET];
    int r = ft_recv(resp, sizeof(resp), FT_READ_TIMEOUT_MS);
    uint8_t rid, err; const uint8_t *p; uint8_t pn;
    return r >= 6 && ft_parse_response(resp, r, &rid, &err, &p, &pn) == 0
           && rid == id && err == 0;
}

bool ft_write_u8(uint8_t id, uint8_t addr, uint8_t v) {
    return ft_write_reg(id, addr, &v, 1);
}

bool ft_write_u16(uint8_t id, uint8_t addr, uint16_t v) {
    uint8_t d[2] = { (uint8_t)(v & 0xFF), (uint8_t)(v >> 8) };
    return ft_write_reg(id, addr, d, 2);
}

bool ft_read(uint8_t id, uint8_t addr, uint8_t nbytes,
             uint8_t *out_params, uint8_t *err) {
    uint8_t pkt[FT_MAX_PACKET];
    uint8_t n = ft_build_read(pkt, id, addr, nbytes);
    ft_send(pkt, n);
    uint8_t resp[FT_MAX_PACKET];
    int r = ft_recv(resp, sizeof(resp), FT_READ_TIMEOUT_MS);
    uint8_t rid, e; const uint8_t *p; uint8_t pn;
    if (r < 6 || ft_parse_response(resp, r, &rid, &e, &p, &pn) != 0
        || rid != id) return false;
    if (err) *err = e;
    if (out_params && pn) memcpy(out_params, p, pn);
    return true;
}

bool ft_goal(uint8_t id, uint16_t pos_counts, uint16_t speed_counts) {
    uint8_t pkt[FT_MAX_PACKET];
    uint8_t n = ft_build_goal(pkt, id, pos_counts, speed_counts);
    ft_send(pkt, n);
    /* every addressed write gets a 6-byte status response; consume it so
     * it can't corrupt the next read's response parse */
    uint8_t resp[FT_MAX_PACKET];
    int r = ft_recv(resp, sizeof(resp), FT_READ_TIMEOUT_MS);
    uint8_t rid, err; const uint8_t *p; uint8_t pn;
    return r >= 6 && ft_parse_response(resp, r, &rid, &err, &p, &pn) == 0
           && rid == id && err == 0;
}

bool ft_torque_enable(uint8_t id, bool on) {
    return ft_write_u8(id, FT_REG_TORQUE_EN, on ? 1 : 0);
}

bool ft_read_telemetry(uint8_t id, ft_servo_state_t *st) {
    /* one burst read of regs 56..66 (present pos..moving) */
    uint8_t p[16] = {0}, err = 0;
    if (!ft_read(id, FT_REG_PRESENT_POS, 11, p, &err)) {
        st->online = 0;
        return false;
    }
    st->pos   = p[0] | (p[1] << 8);
    st->speed = p[2] | (p[3] << 8);
    st->load  = p[4] | (p[5] << 8);
    st->volt  = p[6];
    st->temp  = p[7];
    st->err   = err;
    st->online = 1;
    st->last_rx_ms = millis();
    return true;
}
