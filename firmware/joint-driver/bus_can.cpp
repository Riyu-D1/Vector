/* bus_can.cpp — HAL-level FDCAN1 on the B-G431B-ESC1 (STM32G431CB).
 * Classic CAN frames, 1 Mbit/s, polling RX (no IRQ needed at our rates). */
#include "bus_can.h"

#if defined(ARDUINO) && defined(STM32G4xx)
#include <Arduino.h>
#include <stm32g4xx_hal.h>
#include <stm32g4xx_hal_fdcan.h>

static FDCAN_HandleTypeDef hfdcan;
static bool term_on = true;

#define CAN_TERM_PIN  PC14      /* HIGH = 120R inserted (UM2516 table 3) */

extern "C" void HAL_FDCAN_MspInit(FDCAN_HandleTypeDef *h) {
    if (h->Instance != FDCAN1) return;
    /* FDCAN kernel clock = PCLK1 (170 MHz on the default 170 MHz tree) */
    RCC_PeriphCLKInitTypeDef p = {0};
    p.PeriphClockSelection = RCC_PERIPHCLK_FDCAN;
    p.FdcanClockSelection  = RCC_FDCANCLKSOURCE_PCLK1;
    HAL_RCCEx_PeriphCLKConfig(&p);

    __HAL_RCC_FDCAN_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    GPIO_InitTypeDef g = {0};
    g.Mode      = GPIO_MODE_AF_PP;
    g.Pull      = GPIO_NOPULL;
    g.Speed     = GPIO_SPEED_FREQ_HIGH;
    g.Alternate = GPIO_AF9_FDCAN1;
    g.Pin = GPIO_PIN_11;            /* FDCAN1_RX */
    HAL_GPIO_Init(GPIOA, &g);
    g.Pin = GPIO_PIN_9;             /* FDCAN1_TX */
    HAL_GPIO_Init(GPIOB, &g);
}

static void fdcan_start(void) {
    hfdcan.Instance = FDCAN1;
    hfdcan.Init.ClockDivider       = FDCAN_CLOCK_DIV1;
    hfdcan.Init.FrameFormat        = FDCAN_FRAME_CLASSIC;
    hfdcan.Init.Mode               = FDCAN_MODE_NORMAL;
    hfdcan.Init.AutoRetransmission = ENABLE;
    hfdcan.Init.TransmitPause      = DISABLE;
    hfdcan.Init.ProtocolException  = DISABLE;
    hfdcan.Init.NominalPrescaler   = 10;
    hfdcan.Init.NominalSyncJumpWidth = 3;
    hfdcan.Init.NominalTimeSeg1    = 13;
    hfdcan.Init.NominalTimeSeg2    = 3;
    hfdcan.Init.DataPrescaler      = 1;
    hfdcan.Init.DataSyncJumpWidth  = 1;
    hfdcan.Init.DataTimeSeg1       = 1;
    hfdcan.Init.DataTimeSeg2       = 1;
    hfdcan.Init.StdFiltersNbr      = 1;
    hfdcan.Init.ExtFiltersNbr      = 0;
    hfdcan.Init.TxFifoQueueMode    = FDCAN_TX_FIFO_OPERATION;
    HAL_FDCAN_Init(&hfdcan);

    FDCAN_FilterTypeDef f = {0};
    f.IdType       = FDCAN_STANDARD_ID;
    f.FilterIndex  = 0;
    f.FilterType   = FDCAN_FILTER_MASK;
    f.FilterConfig = FDCAN_FILTER_TO_RXFIFO0;
    f.FilterID1    = 0x000;
    f.FilterID2    = 0x000;         /* mask 0 -> accept everything */
    HAL_FDCAN_ConfigFilter(&hfdcan, &f);
    HAL_FDCAN_ConfigGlobalFilter(&hfdcan,
        FDCAN_ACCEPT_IN_RX_FIFO0, FDCAN_ACCEPT_IN_RX_FIFO0,
        FDCAN_FILTER_REMOTE, FDCAN_FILTER_REMOTE);
    HAL_FDCAN_Start(&hfdcan);
}

void bus_can_init(bool can_term) {
    term_on = can_term;
    pinMode(CAN_TERM_PIN, OUTPUT);
    digitalWrite(CAN_TERM_PIN, term_on ? HIGH : LOW);
    fdcan_start();
}

bool bus_can_send(uint16_t id, const uint8_t *data, uint8_t dlc) {
    FDCAN_TxHeaderTypeDef th = {0};
    th.Identifier            = id;
    th.IdType                = FDCAN_STANDARD_ID;
    th.TxFrameType           = FDCAN_DATA_FRAME;
    th.DataLength            = dlc;   /* classic DLC == byte count <= 8 */
    th.ErrorStateIndicator   = FDCAN_ESI_ACTIVE;
    th.BitRateSwitch         = FDCAN_BRS_OFF;
    th.FDFormat              = FDCAN_CLASSIC_CAN;
    th.TxEventFifoControl    = FDCAN_NO_TX_EVENTS;
    return HAL_FDCAN_AddMessageToTxFifoQ(&hfdcan, &th,
                                         (uint8_t *)data) == HAL_OK;
}

bool bus_can_recv(uint16_t *id, uint8_t *data, uint8_t *dlc) {
    if (HAL_FDCAN_GetRxFifoFillLevel(&hfdcan, FDCAN_RX_FIFO0) == 0)
        return false;
    FDCAN_RxHeaderTypeDef rh = {0};
    if (HAL_FDCAN_GetRxMessage(&hfdcan, FDCAN_RX_FIFO0, &rh, data)
        != HAL_OK)
        return false;
    *id  = (uint16_t)rh.Identifier;
    *dlc = (uint8_t)rh.DataLength;    /* classic: already byte count   */
    return true;
}

void bus_can_recover(void) {
    if (hfdcan.State == HAL_FDCAN_STATE_BUSY ||
        HAL_FDCAN_GetError(&hfdcan) & FDCAN_FLAG_BUS_OFF) {
        /* simplest robust recovery: full re-init */
        HAL_FDCAN_DeInit(&hfdcan);
        fdcan_start();
    }
}

#else
/* host-build stub so the file compiles for review checks */
void bus_can_init(bool can_term) { (void)can_term; }
bool bus_can_send(uint16_t id, const uint8_t *d, uint8_t n) {
    (void)id; (void)d; (void)n; return false; }
bool bus_can_recv(uint16_t *id, uint8_t *d, uint8_t *n) {
    (void)id; (void)d; (void)n; return false; }
void bus_can_recover(void) {}
#endif
