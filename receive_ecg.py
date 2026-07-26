import serial
import time

port = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=9600,
    bytesize=8,
    parity='N',
    stopbits=1,
    timeout=5,
    write_timeout=None,   # ← remove write timeout
    xonxoff=False,
    rtscts=True,          # ← enable hardware flow control
    dsrdtr=True           # ← enable DSR/DTR
)

print("✔  Port open: /dev/ttyACM0 @ 9600 baud")
print("→  Sending handshake to wake machine ...")

# Send 'C' repeatedly — this is the Ymodem-CRC start signal
# The machine waits for this before it starts sending
for i in range(10):
    port.write(b'C')
    port.flush()
    print(f"   Sent 'C' handshake #{i+1} ...")
    time.sleep(1)
    if port.in_waiting > 0:
        print(f"   Machine responded! {port.in_waiting} bytes waiting")
        break

print("→  Press SEND on the ECG machine NOW ...")

# Keep sending C and collect all incoming bytes
received = bytearray()
start_time = time.time()
last_data  = time.time()

while True:
    # Keep sending handshake until transfer starts
    if len(received) == 0 and time.time() - start_time < 30:
        port.write(b'C')
        port.flush()

    # Read whatever is available
    waiting = port.in_waiting
    if waiting > 0:
        chunk = port.read(waiting)
        received.extend(chunk)
        last_data = time.time()
        print(f"\r   Receiving ... {len(received)} bytes", end="", flush=True)

    # Stop if no data for 3 seconds after transfer started
    if len(received) > 0 and time.time() - last_data > 3:
        print(f"\n✔  Transfer complete: {len(received)} bytes received")
        break

    # Timeout with no data at all
    if time.time() - start_time > 35:
        print("\n✘  Timeout — no response from machine")
        break

    time.sleep(0.05)

# Save raw file
if received:
    with open('ecg_received.bin', 'wb') as f:
        f.write(received)
    print(f"✔  Saved → ecg_received.bin")

    # Show first bytes to identify format
    print(f"\n   First 32 bytes (hex):")
    print('   ' + ' '.join(f'{b:02X}' for b in received[:32]))
    print(f"\n   First 32 bytes (ascii):")
    print('   ' + ''.join(chr(b) if 32 <= b < 127 else '.' for b in received[:32]))
else:
    print("✘  No data received")
    print("   Try: sudo stty -F /dev/ttyACM0 115200 and rerun")

port.close()
