import time
import serial
 
ser = serial.Serial('/dev/ttyS0', 9600)
 
print("Raspberry's sending : ")
 
try:
    while True:
        ser.write(b'hehe')
        # ser.flush()
        print("hehe")
        time.sleep(5)
except KeyboardInterrupt:
	ser.close()