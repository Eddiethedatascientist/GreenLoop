import machine as mc
import utime
#Add sys to better machine to machine communication
import sys

# --- 1. INITIALIZE 4 LEDs (Pins 2 to 5) ---
led_plastic = mc.Pin(2, mc.Pin.OUT)
led_paper   = mc.Pin(5, mc.Pin.OUT)
led_other   = mc.Pin(27, mc.Pin.OUT)

leds = {
    "plastic": led_plastic,
    "paper":   led_paper,
    "metal":   led_plastic,
    "other":   led_other
}

# --- 2. INITIALIZE 4 SERVOS (PWM 50Hz) ---
plastic_servo = mc.PWM(mc.Pin(18), freq=50)
paper_servo   = mc.PWM(mc.Pin(26), freq=50)
other_servo   = mc.PWM(mc.Pin(23), freq=50)

servos = {
    "plastic": plastic_servo,
    "paper":   paper_servo,
    "metal":   plastic_servo,
    "other":   other_servo
}

def set_servo_angle(servo, angle):
    """Adjust servo angle from 0 to 180 degrees"""
    duty = int(500000 + (angle / 180.0) * 2000000)
    servo.duty_ns(duty)

def reset_all_servos():
    """Reset all servo angles to 0 degrees"""
    for s in servos.values():
        set_servo_angle(s, 0)

def clear_all_leds():
    """Turn off all LEDs"""
    for l in leds.values():
        l.value(0)

def sort_waste(waste_type, hold_sec=2):
    """Handle waste sorting: Turn on matching LED and open corresponding servo bin"""
    clear_all_leds()
    reset_all_servos()
    
    if waste_type in leds and waste_type in servos:
        print(f"[GreenLoop] Sorting: {waste_type.upper()} -> Activating LED and opening servo bin...")
        leds[waste_type].value(1)
        set_servo_angle(servos[waste_type], 90)
        utime.sleep(hold_sec)
        
        set_servo_angle(servos[waste_type], 0)
        leds[waste_type].value(0)
        print(f"[GreenLoop] Closed {waste_type.upper()} bin.\n")
    else:
        print("[Error] Invalid waste type!\n")

# --- 3. MAIN LOOP FOR TERMINAL INPUT ---
print("=== GREENLOOP SYSTEM READY ===")
reset_all_servos()
clear_all_leds()

print("Available keywords for testing: plastic, metal, paper, or other\n")

while True:
    reset_all_servos()
    clear_all_leds()
    #Use sys.stdin.readline()
    raw = sys.stdin.readline()
    user_input = raw.strip().lower()
    if user_input in leds:
        sort_waste(user_input, hold_sec=2)
    else:
        if user_input:
            print(f"'{user_input}' is an invalid command! Please try again.\n")