import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import subprocess

import time
import board
import adafruit_dht
import datetime
from influxdb import InfluxDBClient

# Initial the dht device, with data pin connected to:
dhtDevice = adafruit_dht.DHT22(board.D4)

# you can pass DHT22 use_pulseio=False if you wouldn't like to use pulseio.
# This may be necessary on a Linux single board computer like the Raspberry Pi,
# but it will not work in CircuitPython.
# dhtDevice = adafruit_dht.DHT22(board.D18, use_pulseio=False)

# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used

disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST, i2c_address=0x3C)


# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=1, fill=1)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('Minecraftia.ttf', 8)

### INFLUX REGION

influx_client = InfluxDBClient('localhost', 8086, 'admin', 'admin', 'telemetry')

temperature_structure = {
    'measurement': 'temperature',
    'tags': {
        'sensor': 'DHT11',
        'software_version': '0.01'
    },
    'time': None,
    'fields': {
        'value': None
    }
}

humidity_structure = {
    'measurement': 'humidity',
    'tags': {
        'sensor': 'DHT22',
        'software_version': '0.01'
    },
    'time': None,
    'fields': {
        'value': None
    }
}

### END INFLUX REGION


while True:
    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)

    # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname -I | cut -d\' \' -f1"
    IP = subprocess.check_output(cmd, shell = True )
    try:
        temperature_c = dhtDevice.temperature
        humidity = dhtDevice.humidity
        timepoint = int(time.time())
        time_precision='s'
        temperature_structure['time'] = timepoint
        temperature_structure['fields']['value'] = temperature_c
        humidity_structure['time'] = timepoint
        humidity_structure['fields']['value'] = humidity
        influx_client.write_points([temperature_structure, humidity_structure], time_precision=time_precision)

    except Exception as e:
        print(e)
        time.sleep(1)
        continue
    dht_string = "Temp: {:.1f} C\nHumidity: {}% ".format(
                temperature_c, humidity
            )
    draw.text((0, 0),       f"IP: {IP.decode('utf-8')}",  font=font, fill=255)
    draw.text((0, 10), 'Current sensor data:', font=font, fill = 255)
    draw.text((0, 25),    str(dht_string),  font=font, fill=255)
    draw.text((0, 50), f'{datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}', font=font, fill=255)


    # Display image.
    disp.image(image)
    disp.display()
    time.sleep(10)
