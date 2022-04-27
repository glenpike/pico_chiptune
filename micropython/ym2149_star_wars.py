# Raspberry Pi Pico + YM2149 Soundchip test example
# Based on https://github.com/FlorentFlament/ym2149-test

# http://www.ym2149.com/ym2149.pdf
# Pins
# Pico -> YM2149 (DIL)
# GP5  -> CLOCK (22)
# GP6  -> BC1 (29)
# GP7  -> BDIR (27)
# GP8 to GP15 -> DA0 to DA7 (37 to 30)
# VBUS to RESET (23)
# VBUS to BC2 (28)
# VBUS to VCC (40)
from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
import utime

PIO_FREQ = 5000000 #gives us a 20ns cycle time which we can use for delay multipliers

@asm_pio(sideset_init=[rp2.PIO.OUT_LOW] * 2, out_init=[rp2.PIO.OUT_LOW] * 8, out_shiftdir=PIO.SHIFT_RIGHT, pull_thresh=16, push_thresh=8 )
def pio_test():
    pull()        .side(0x3)       #set the mode to address on pins
    out(pins, 8)            [1]  #output first byte (address) from FIFO to 8 pins and wait for 7 more cycles
    nop()                   [3]  
    nop()                   [3]  
    nop()                   [1]  #wait for another 7 cycles (1 instruction + 6) - 300ns total
    nop()                   [3]  
    nop()                   [3]
    nop()         .side(0x0)  [3]  #set mode to inactive for 80ns (1 instruction + 3 cycles)
    nop()         .side(0x2)
    out(pins, 8)            [1]  #output second byte (data) from FIFO to 8 pins and wait for 7 more cycles
    nop()                   [3]  
    nop()                   [3]  
    nop()                   [1]  #wait for another 7 cycles (1 instruction + 6) - 300ns total
    nop()                   [3]  
    nop()                   [3]
    nop()         .side(0x0)  [3]  #set mode to inactive for 80ns (1 instruction + 3 cycles)


ym2149_out = StateMachine(0, pio_test, freq=PIO_FREQ, sideset_base=Pin(6), out_base=Pin(8))

ym2149_out.active(1)          #Activate address program in first PIO

# 2MHz clock on pin 5
CLOCK_FREQ = 2000000

def setup_clock():
    clock = machine.PWM(machine.Pin(5))
    clock.freq(CLOCK_FREQ)
    clock.duty_u16(32768)


# Simple C, D, E, F, G, A, B note sequence
note_freqs = [130.81, 146.83, 164.81, 174.61, 196.00, 220.00, 246.94]

#Take a wild guess
theme = [
[146.83, 0.66],
[146.83, 0.66],
[146.83, 0.66],
[196.00, 4],
[2*146.83, 4],
[294.00, 0.66],
[246.94, 0.66],
[220.00, 0.66],
[2*196.00, 4],
[2*146.83, 2],
[294.00, 0.66],
[246.94, 0.66],
[220.00, 0.66],
[2*196.00, 4],
[2*146.83, 2],
[294.00, 0.66],
[246.94, 0.66],
[294.00, 0.66],
[220.00, 4],
[0, 0.66],
[130.81, 0.66],
[130.81, 0.66]
]

# Convert this to values that YM2149 understands
def note_to_data_val(freq):
    return int((CLOCK_FREQ / (16 * (freq * 2))))

notes = list(map(note_to_data_val, note_freqs))
    
setup_clock()

def set_register(address, data):
    ym2149_out.put((data << 8) | (address & 0xff))
    utime.sleep(0.005)

for i in range(16):
    set_register(i, 0)

set_register(7, 0xf8) #Mixer setup: Only output clear sound (no noise)
set_register(8, 0x0f) # Volume A - fixed, no envelope
set_register(9, 0x0f) # Volume B - fixed, no envelope
set_register(10, 0x0f) # Volume C - fixed, no envelope

while True:
    for i in range(len(theme)):
        freq_time  = theme[i]
        note = 0
        if freq_time[0] != 0:
            note = note_to_data_val(freq_time[0])
        print("note:  {}: {}".format(note, freq_time))
        set_register(0, (note & 0xff))
        set_register(1, (note >> 8))
        set_register(2, ((note >> 1) & 0xff))
        set_register(3, (note >> 9))
        set_register(4, ((note >> 2) & 0xff))
        set_register(5, (note >> 10))
        utime.sleep(0.25 * freq_time[1])