/* Minimal startup for STM32L031 (Cortex-M0+), no vendor startup needed. */
#include <stdint.h>

extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss, _estack;

int main(void);
void SysTick_Handler(void);
void EXTI2_3_IRQHandler(void);

void Reset_Handler(void)
{
    uint32_t *src = &_sidata, *dst = &_sdata;
    while (dst < &_edata)
        *dst++ = *src++;
    for (dst = &_sbss; dst < &_ebss;)
        *dst++ = 0;
    main();
    for (;;)
        ;
}

void Default_Handler(void)
{
    for (;;)
        ;
}

#define WEAK_DEFAULT __attribute__((weak, alias("Default_Handler")))
void NMI_Handler(void) WEAK_DEFAULT;
void HardFault_Handler(void) WEAK_DEFAULT;
void SVC_Handler(void) WEAK_DEFAULT;
void PendSV_Handler(void) WEAK_DEFAULT;

__attribute__((section(".isr_vector"), used))
const void *g_vectors[48] = {
    &_estack,
    Reset_Handler,
    NMI_Handler,
    HardFault_Handler,
    0, 0, 0, 0, 0, 0, 0,
    SVC_Handler,
    0, 0,
    PendSV_Handler,
    SysTick_Handler,
    /* IRQ0.. (WWDG, PVD, RTC, FLASH, RCC, EXTI0_1, EXTI2_3, EXTI4_15, ...) */
    Default_Handler,      /* 0 WWDG */
    Default_Handler,      /* 1 PVD */
    Default_Handler,      /* 2 RTC */
    Default_Handler,      /* 3 FLASH */
    Default_Handler,      /* 4 RCC */
    Default_Handler,      /* 5 EXTI0_1 */
    EXTI2_3_IRQHandler,   /* 6 EXTI2_3 */
    Default_Handler,      /* 7 EXTI4_15 */
    0,                    /* 8 reserved */
    Default_Handler,      /* 9 DMA1_Channel1 */
    Default_Handler,      /* 10 DMA1_Channel2_3 */
    Default_Handler,      /* 11 DMA1_Channel4_5_6_7 */
    Default_Handler,      /* 12 ADC_COMP */
    Default_Handler,      /* 13 LPTIM1 */
    0,                    /* 14 reserved */
    Default_Handler,      /* 15 TIM2 */
    0,                    /* 16 reserved */
    Default_Handler,      /* 17 TIM21 */
    0,                    /* 18 reserved */
    Default_Handler,      /* 19 TIM22 */
    Default_Handler,      /* 20 I2C1 */
    0,                    /* 21 reserved */
    Default_Handler,      /* 22 SPI1 */
    0,                    /* 23 reserved */
    Default_Handler,      /* 24 USART2 */
    Default_Handler,      /* 25 LPUART1 */
    0, 0,                 /* 26,27 reserved */
    0, 0, 0, 0            /* pad */
};
