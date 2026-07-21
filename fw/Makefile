# Firmware for the keyring countdown (STM32L031G6U6)
# make        -> build countdown.elf/.bin (RTC seeded with *current* local time)
# make flash  -> rebuild with fresh timestamp and flash via pyocd (ST-Link/CMSIS-DAP + TC2030)

CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

# Local-time epoch at build. date +%s is UTC-epoch; add the current UTC offset
# so the RTC (which we keep in local time) is seeded correctly.
BUILD_UNIX_LOCAL := $(shell python3 -c "import time; print(int(time.time()) + time.localtime().tm_gmtoff)")

CFLAGS = -mcpu=cortex-m0plus -mthumb -Os -g -Wall -Wextra -std=c11 -ffreestanding \
         -ffunction-sections -fdata-sections -Ivendor \
         -DSTM32L031xx -DBUILD_UNIX_LOCAL=$(BUILD_UNIX_LOCAL)
LDFLAGS = -mcpu=cortex-m0plus -mthumb -nostartfiles -Wl,--gc-sections \
          -T stm32l031.ld -Wl,-Map=countdown.map -nostdlib -lgcc

SRCS = main.c startup.c

countdown.elf: $(SRCS) config.h stm32l031.ld Makefile
	$(CC) $(CFLAGS) $(SRCS) $(LDFLAGS) -o $@
	$(OBJCOPY) -O binary $@ countdown.bin
	$(SIZE) $@

flash:
	rm -f countdown.elf
	$(MAKE) countdown.elf
	pyocd flash -t stm32l031g6ux countdown.elf

clean:
	rm -f countdown.elf countdown.bin countdown.map

.PHONY: flash clean
