import time

import time
from influxdb import InfluxDBClient
import serial

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

h2_ppm_structure = {
    'measurement': 'h2_ppm',
    'tags': {
        'sensor': 'MQ-5',
        'software_version': '0.01'
    },
    'time': None,
    'fields': {
        'value': None
    }
}

### END INFLUX REGION

if __name__ == '__main__':
    ser = serial.Serial('/dev/ttyUSB0', 112500, timeout=1)
    ser.reset_input_buffer()
    while True:
        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').rstrip()
                print(f'Got the following data from arduino: {line}')
                data = line.split('|')
                if len(data) > 1:
                    h2_ppm = float(data[0])
                    temperature_c = float(data[1])
                    humidity = float(data[2])
                    timepoint = int(time.time())
                    time_precision='s'
                    temperature_structure['time'] = timepoint
                    temperature_structure['fields']['value'] = temperature_c
                    humidity_structure['time'] = timepoint
                    humidity_structure['fields']['value'] = humidity
                    h2_ppm_structure['time'] = timepoint
                    h2_ppm_structure['fields']['value'] = h2_ppm
                    influx_client.write_points([temperature_structure, humidity_structure, h2_ppm_structure], time_precision=time_precision)
        except Exception as e:
            print(e)
            time.sleep(1)
            continue
        time.sleep(1)
