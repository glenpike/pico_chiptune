from machine import Pin
from rp2 import PIO, StateMachine, asm_pio
import utime

PIO_FREQ = 5000 #gives us a 20ns cycle time which we can use for delay multipliers

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


test_sm = StateMachine(0, pio_test, freq=PIO_FREQ, sideset_base=Pin(6), out_base=Pin(8))

test_sm.active(1)          #Activate address program in first PIO

# 2kHz clock on pin 5
CLOCK_FREQ = 2000

def setup_clock():
    clock = machine.PWM(machine.Pin(5))
    clock.freq(CLOCK_FREQ)
    clock.duty_u16(32768)
    
setup_clock()

def set_register(address, data):
    test_sm.put((data << 8) | (address & 0xff))
    utime.sleep(0.005)

for i in range(16):
    set_register(i, 0)


set_register(7, 0xc0) #Mixer setup: Output noise too
set_register(8, 0x0f) # Volume A - fixed, no envelope
set_register(9, 0x0f) # Volume B - fixed, no envelope
set_register(10, 0x0f) # Volume C - fixed, no envelope

while True:
    utime.sleep(1)
