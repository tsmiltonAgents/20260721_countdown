/* Keyring countdown to 2026-10-10 12:00 — STM32L031G6U6.
 *
 * Behaviour: RTC keeps local time on the 32.768 kHz LSE crystal, MCU sleeps
 * in Stop mode (~1 uA). A button press wakes it; it multiplexes the hours
 * (or, under 100 h, minutes with decimal point lit) remaining until the
 * target onto a 4-digit common-cathode 7-segment display for a few seconds,
 * then returns to Stop. Timekeeping survives everything except battery
 * removal; on first power-up the RTC is seeded with the firmware build
 * timestamp (so flash it right after building).
 */
#include <stdint.h>

#include "stm32l031xx.h"
#include "config.h"

#ifndef BUILD_UNIX_LOCAL
#error "BUILD_UNIX_LOCAL must be passed by the Makefile (local-time epoch)"
#endif

/* ---- tiny civil-calendar helpers (Howard Hinnant's algorithms) ---- */
static int32_t days_from_civil(int32_t y, uint32_t m, uint32_t d)
{
    y -= m <= 2;
    const int32_t era = (y >= 0 ? y : y - 399) / 400;
    const uint32_t yoe = (uint32_t)(y - era * 400);
    const uint32_t doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const uint32_t doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + (int32_t)doe - 719468;
}

static void civil_from_days(int32_t z, int32_t *y, uint32_t *m, uint32_t *d)
{
    z += 719468;
    const int32_t era = (z >= 0 ? z : z - 146096) / 146097;
    const uint32_t doe = (uint32_t)(z - era * 146097);
    const uint32_t yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    int32_t yy = (int32_t)yoe + era * 400;
    const uint32_t doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    const uint32_t mp = (5 * doy + 2) / 153;
    *d = doy - (153 * mp + 2) / 5 + 1;
    *m = mp + (mp < 10 ? 3 : -9);
    *y = yy + (*m <= 2);
}

/* ---- display tables ---- */
static const uint8_t FONT[10] = {
    /* gfedcba */
    0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F
};
static const uint8_t SEG_PINS[8] = {
    SEGA_PIN, SEGB_PIN, SEGC_PIN, SEGD_PIN,
    SEGE_PIN, SEGF_PIN, SEGG_PIN, SEGDP_PIN
};
static GPIO_TypeDef *const DIG_PORT[4] = {DIG1_PORT, DIG2_PORT, DIG3_PORT, DIG4_PORT};
static const uint8_t DIG_PIN[4] = {DIG1_PIN, DIG2_PIN, DIG3_PIN, DIG4_PIN};

/* show_frame() writes the segment byte straight to GPIOA pins 0-7 */
_Static_assert(SEGA_PIN == 0 && SEGB_PIN == 1 && SEGC_PIN == 2 &&
               SEGD_PIN == 3 && SEGE_PIN == 4 && SEGF_PIN == 5 &&
               SEGG_PIN == 6 && SEGDP_PIN == 7,
               "show_frame assumes identity segment mapping on PA0-7");

static volatile uint32_t g_ms;

void SysTick_Handler(void) { g_ms++; }

static void delay_ms(uint32_t ms)
{
    uint32_t start = g_ms;
    while ((g_ms - start) < ms)
        __WFI();
}

/* ---- GPIO helpers ---- */
static void gpio_mode(GPIO_TypeDef *g, uint32_t pin, uint32_t mode)
{
    g->MODER = (g->MODER & ~(3u << (pin * 2))) | (mode << (pin * 2));
}

static void display_pins_active(int active)
{
    /* active: segments/digits push-pull outputs; else: analog (Hi-Z, 0 uA) */
    for (int i = 0; i < 8; i++) {
        if (active) {
            GPIOA->BSRR = (1u << (SEG_PINS[i] + 16)); /* low = seg off */
            gpio_mode(GPIOA, SEG_PINS[i], 1);
        } else {
            gpio_mode(GPIOA, SEG_PINS[i], 3);
        }
    }
    for (int i = 0; i < 4; i++) {
        if (active) {
            DIG_PORT[i]->BSRR = (1u << DIG_PIN[i]); /* high = digit off (CC) */
            gpio_mode(DIG_PORT[i], DIG_PIN[i], 1);
        } else {
            gpio_mode(DIG_PORT[i], DIG_PIN[i], 3);
        }
    }
}

/* ---- RTC ---- */
static uint32_t bcd(uint32_t v) { return ((v / 10) << 4) | (v % 10); }
static uint32_t unbcd(uint32_t v) { return (v >> 4) * 10 + (v & 0xF); }

static void rtc_unlock(void)
{
    RTC->WPR = 0xCA;
    RTC->WPR = 0x53;
}

static void error_blink(void)
{
    /* LSE failed: blink segment G of every digit forever (distinct from a
     * flat battery, which shows nothing at all) */
    display_pins_active(1);
    for (;;) {
        for (int d = 0; d < 4; d++)
            DIG_PORT[d]->BSRR = 1u << (DIG_PIN[d] + 16);
        GPIOA->BSRR = 1u << SEGG_PIN;
        delay_ms(300);
        GPIOA->BSRR = 1u << (SEGG_PIN + 16);
        delay_ms(300);
    }
}

static int rtc_did_seed;

static void rtc_init_if_needed(void)
{
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC->APB1ENR; /* errata: settle clock enable before next access */
    PWR->CR |= PWR_CR_DBP;

    if ((RTC->ISR & RTC_ISR_INITS) != 0) {
        /* RTC already running (reflash without power loss); still make sure
         * calendar reads bypass the shadow registers (see rtc_now_epoch) */
        rtc_unlock();
        RTC->CR |= RTC_CR_BYPSHAD;
        RTC->WPR = 0xFF;
        return;
    }
    rtc_did_seed = 1;

    /* LSEDRV must be programmed while LSE is off (RM0377), then enable */
    RCC->CSR = (RCC->CSR & ~RCC_CSR_LSEDRV) | RCC_CSR_LSEDRV_1;
    RCC->CSR |= RCC_CSR_LSEON;
    for (uint32_t t = g_ms; !(RCC->CSR & RCC_CSR_LSERDY);)
        if ((g_ms - t) > 4000u)
            error_blink(); /* dead crystal: never returns */
    RCC->CSR = (RCC->CSR & ~RCC_CSR_RTCSEL) | RCC_CSR_RTCSEL_LSE | RCC_CSR_RTCEN;

    rtc_unlock();
    RTC->ISR |= RTC_ISR_INIT;
    while (!(RTC->ISR & RTC_ISR_INITF))
        ;
    /* calendar reads via BYPSHAD + double-read loop (Stop-mode safe) */
    RTC->CR |= RTC_CR_BYPSHAD;
    /* prescalers: reset default 127/255 already gives 1 Hz from 32768 Hz;
     * written anyway, sync then async per RM0377 double-write rule */
    RTC->PRER = 255u;
    RTC->PRER = (127u << 16) | 255u;

    /* seed calendar from build-time local epoch */
    int64_t t = (int64_t)BUILD_UNIX_LOCAL;
    int32_t days = (int32_t)(t / 86400);
    uint32_t sod = (uint32_t)(t % 86400);
    int32_t y;
    uint32_t mo, d;
    civil_from_days(days, &y, &mo, &d);
    /* weekday: epoch day 0 was a Thursday; ((days+3) mod 7)+1 gives Mon=1 */
    uint32_t wd = (uint32_t)(((days + 3) % 7) + 1);
    RTC->TR = (bcd(sod / 3600) << 16) | (bcd((sod / 60) % 60) << 8) | bcd(sod % 60);
    RTC->DR = (bcd((uint32_t)(y - 2000)) << 16) | (wd << 13) |
              (bcd(mo) << 8) | bcd(d);
    RTC->ISR &= ~RTC_ISR_INIT;
    RTC->WPR = 0xFF;
}

static int64_t rtc_now_epoch(void)
{
    /* BYPSHAD=1: read direct calendar registers twice until stable
     * (RM0377-prescribed pattern; immune to Stop-mode shadow staleness) */
    uint32_t ssr, tr, dr;
    do {
        ssr = RTC->SSR;
        tr = RTC->TR;
        dr = RTC->DR;
    } while (RTC->SSR != ssr || RTC->TR != tr);
    (void)ssr;
    int32_t y = 2000 + (int32_t)unbcd((dr >> 16) & 0xFF);
    uint32_t mo = unbcd((dr >> 8) & 0x1F);
    uint32_t d = unbcd(dr & 0x3F);
    uint32_t h = unbcd((tr >> 16) & 0x3F);
    uint32_t mi = unbcd((tr >> 8) & 0x7F);
    uint32_t s = unbcd(tr & 0x7F);
    return (int64_t)days_from_civil(y, mo, d) * 86400 + h * 3600 + mi * 60 + s;
}

/* ---- display one frame (all 4 digits once) ---- */
static void show_frame(const uint8_t segs[4])
{
    for (int d = 0; d < 4; d++) {
        /* set segments for this digit */
        GPIOA->BSRR = (uint32_t)(~segs[d] & 0xFF) << 16 | segs[d];
        /* enable digit (sink low) */
        DIG_PORT[d]->BSRR = 1u << (DIG_PIN[d] + 16);
        delay_ms(DIGIT_DWELL_MS);
        /* digit off, segments off (avoid ghosting) */
        DIG_PORT[d]->BSRR = 1u << DIG_PIN[d];
        GPIOA->BSRR = 0xFFu << 16;
    }
}

static void render_value(uint32_t v, int dp_digit, uint8_t out[4])
{
    for (int i = 3; i >= 0; i--) {
        out[i] = FONT[v % 10];
        v /= 10;
    }
    /* blank leading zeros (keep the last digit) */
    for (int i = 0; i < 3; i++) {
        if (out[i] != FONT[0])
            break;
        out[i] = 0;
    }
    if (dp_digit >= 0)
        out[dp_digit] |= 0x80;
}

static void display_countdown(void)
{
    display_pins_active(1);
    uint32_t start = g_ms;
    while ((g_ms - start) < DISPLAY_ON_MS) {
        int64_t now = rtc_now_epoch();
        int64_t target = (int64_t)days_from_civil(TARGET_Y, TARGET_MO, TARGET_D) * 86400
                         + TARGET_H * 3600 + TARGET_MIN * 60;
        int64_t rem = target - now;
        uint8_t segs[4];
        if (rem <= 0) {
            /* arrived: show 0.0.0.0 solid */
            segs[0] = segs[1] = segs[2] = segs[3] = FONT[0] | 0x80;
        } else {
            int64_t hours = rem / 3600;
            if (hours >= 100) {
                if (hours > 9999)
                    hours = 9999;
                render_value((uint32_t)hours, -1, segs);
            } else {
                /* under 100 h: minutes remaining, DP on digit 1 as marker */
                int64_t mins = rem / 60;
                render_value((uint32_t)mins, 0, segs);
            }
        }
        /* ~30 frames between recomputes */
        for (int f = 0; f < 30; f++)
            show_frame(segs);
    }
    display_pins_active(0);
}

/* ---- button EXTI ---- */
void EXTI2_3_IRQHandler(void)
{
    EXTI->PR = (1u << BTN_PIN); /* clear */
}

static void enter_stop(void)
{
    PWR->CR |= PWR_CR_ULP | PWR_CR_LPSDSR; /* ultra-low-power, regulator LP */
    PWR->CR &= ~PWR_CR_PDDS;               /* Stop, not Standby */
    SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
    SysTick->CTRL &= ~SysTick_CTRL_ENABLE_Msk; /* no systick wakes in stop */
    __WFI();
    SysTick->CTRL |= SysTick_CTRL_ENABLE_Msk;
    SCB->SCR &= ~SCB_SCR_SLEEPDEEP_Msk;
}

int main(void)
{
    /* clocks: stay on MSI 2.097 MHz. Enable GPIO + SYSCFG */
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN | RCC_IOPENR_GPIOCEN;
    (void)RCC->IOPENR;
    RCC->APB2ENR |= RCC_APB2ENR_SYSCFGEN;
    (void)RCC->APB2ENR;

    SysTick_Config(2097000 / 1000); /* 1 ms tick */

    /* all unused pins analog to minimise leakage (default after reset is
     * analog on L0 anyway, but be explicit for display pins) */
    display_pins_active(0);

    /* button: input, pull-up, EXTI falling */
    gpio_mode(BTN_PORT, BTN_PIN, 0);
    BTN_PORT->PUPDR = (BTN_PORT->PUPDR & ~(3u << (BTN_PIN * 2))) | (1u << (BTN_PIN * 2));
    SYSCFG->EXTICR[BTN_PIN / 4] &= ~(0xFu << ((BTN_PIN % 4) * 4));
    SYSCFG->EXTICR[BTN_PIN / 4] |= (0x1u << ((BTN_PIN % 4) * 4)); /* port B */
    EXTI->FTSR |= (1u << BTN_PIN);
    EXTI->IMR |= (1u << BTN_PIN);
    NVIC_EnableIRQ(EXTI2_3_IRQn);

    rtc_init_if_needed();

    if (rtc_did_seed) {
        /* signal "clock (re)seeded from the firmware build timestamp":
         * all four decimal points flash three times. If you see this after
         * a battery swap WITHOUT having just flashed fresh firmware, the
         * countdown is stale - rebuild and reflash. */
        display_pins_active(1);
        for (int k = 0; k < 3; k++) {
            uint8_t dots[4] = {0x80, 0x80, 0x80, 0x80};
            uint32_t t0 = g_ms;
            while ((g_ms - t0) < 220u)
                show_frame(dots);
            display_pins_active(1); /* keep outputs, clear segments */
            delay_ms(160);
        }
    }

    /* greet: show countdown once at power-up */
    display_countdown();

    for (;;) {
        enter_stop();
        /* woken by button */
        display_countdown();
        /* if the button is stuck/held (pocket squeeze), wait for release so
         * we don't re-light the display forever */
        while (!(BTN_PORT->IDR & (1u << BTN_PIN)))
            delay_ms(50);
    }
}
