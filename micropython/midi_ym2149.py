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
from machine import UART, Pin, Timer
from rp2 import PIO, StateMachine, asm_pio
import utime
import SimpleMIDIDecoder

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

# Convert this to values that YM2149 understands
def note_to_data_val(freq):
    return int((CLOCK_FREQ / (16 * (freq))))

notes = list(map(note_to_data_val, note_freqs))
    
setup_clock()

def midi_note_to_freq(note):
  # Actually half the freq
  return 440 * 2.0 ** (1.0 * (note - 57) / 12);

def set_register(address, data):
    ym2149_out.put((data << 8) | (address & 0xff))
    utime.sleep(0.005)

uart = UART(0,31250, tx=Pin(16), rx=Pin(17))
md = SimpleMIDIDecoder.SimpleMIDIDecoder()


notes_on = [{}, {}, {}]

timers=[Timer(-1), Timer(-1), Timer(-1)] #create an instance of Timer method

def doMidiNoteOn(ch,cmd,note,vel):
    #print("Note On \t", ch, "\t", note, "\t", vel)
    # note, channel vel
    channel = min(ch, 3) - 1
    timers[channel].deinit()
    data_val = note_to_data_val(midi_note_to_freq(note))
    level = int(vel / 8)
    print("Note On \t", channel, "\t", note, "\t", data_val, "\t", level)

    any_notes_on = False
    for note_channel in notes_on:
        if len(note_channel) > 0:
           any_notes_on = True
           break

    if any_notes_on == False:
        set_register(13, 0xd) # Envelope control
    
    notes_on[channel][note] = vel

    # note pitch on channel
    set_register(channel * 2, (data_val & 0xff))
    set_register(channel * 2 + 1, (data_val >> 8))
    # velocity affects volume
    set_register(channel + 8, (level & 0x0f) | 0x10) # Volume
      

def doMidiNoteOff(ch,cmd,note,vel):
    #print("Note Off \t", ch, "\t", note, "\t", vel)
    channel = min(ch, 3) - 1
    print("Note Off \t", channel, "\t", note)
    
    try:
        notes_on[channel].pop(note)
    except:
        pass

    old_notes = sorted(notes_on[channel].keys())
    
    note_was_highest = True
    
    def set_note_off(t):
        set_register(channel * 2, 0)
        set_register(channel * 2 + 1, 0)  
    
    if len(notes_on[channel]) > 0:
        for old_note in old_notes:
            if old_note > note:
                note_was_highest = False
        if note_was_highest:
            old_note = old_notes[-1]
        else:      
            old_note = old_notes[0]
        
        vel = notes_on[channel][old_note]
        data_val = note_to_data_val(midi_note_to_freq(old_note))
        level = (int(vel / 8) & 0x0f) | 0x10
        print("Replaying Note On \t", channel, "\t", old_note, "\t", data_val, "\t", level)
    
        # note pitch on channel
        set_register(channel * 2, (data_val & 0xff))
        set_register(channel * 2 + 1, (data_val >> 8))
        # velocity affects volume
        set_register(channel + 8, level) # Volume
    else:
        set_register(channel + 8, 0x10) # Volume
        timers[channel].init(period = envelope_period, mode=Timer.ONE_SHOT, callback = set_note_off)
    
    all_notes_off = True
    for note_channel in notes_on:
        if len(note_channel) > 0:
           all_notes_off = False
           break
    if all_notes_off:
        set_register(13, 0x0) # Envelope control - off

def doMidiThru(ch,cmd,data1,data2):
    print("Thru\t", cmd, "\t", data1, "\t", data2) 

md = SimpleMIDIDecoder.SimpleMIDIDecoder()
md.cbNoteOn (doMidiNoteOn)
md.cbNoteOff (doMidiNoteOff)
md.cbThru (doMidiThru)

for i in range(16):
    set_register(i, 0)

set_register(7, 0x38) #Mixer setup: Only output clear sound (no noise)
#set_register(8, 0x0f) # Volume A - fixed, no envelope
#set_register(9, 0x0f) # Volume B - fixed, no envelope
#set_register(10, 0x0f) # Volume C - fixed, no envelope


set_register(8, 0x1f) # Volume A -  use envelope
set_register(9, 0x1f) # Volume B - use envelope
set_register(10, 0x1f) # Volume C - use envelope
# 100ms clock period for envelope generator
#
envelope_period = 40 #ms
envelope_freq = 1000.0 / envelope_period

envelope_control = int(CLOCK_FREQ / (256 * envelope_freq))


set_register(11, envelope_control & 0xff) # Env Freq multiplier, lower 8bits
set_register(12, (envelope_control >> 8) & 0xff) # Env Freq multiplier, upper 8bits

#set_register(13, 0xd) # Envelope control

while True:
    if (uart.any()):
        md.read(uart.read(1)[0])




