import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, List
from pathlib import Path

import serial
from influxdb import InfluxDBClient

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "stats.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'DEVICE': '/dev/ttyUSB_arduino',
    'BAUD_RATE': 112500,
    'TIMEOUT': 1,
    'INFLUX_HOST': 'localhost',
    'INFLUX_PORT': 8086,
    'INFLUX_USER': 'admin',
    'INFLUX_PASSWORD': 'admin',
    'INFLUX_DB': 'telemetry',
    'SOFTWARE_VERSION': '0.01'
}


@dataclass
class SensorMeasurement:
    measurement: str
    sensor_type: str
    value: float = None
    time: int = None

    def to_influx_format(self) -> Dict[str, Any]:
        return {
            'measurement': self.measurement,
            'tags': {
                'sensor': self.sensor_type,
                'software_version': CONFIG['SOFTWARE_VERSION']
            },
            'time': self.time,
            'fields': {
                'value': self.value
            }
        }


# Initialize measurements
temperature = SensorMeasurement('temperature', 'AHT10')  # Changed from DHT22 to AHT10, let's see.
humidity = SensorMeasurement('humidity', 'AHT10')
h2_ppm = SensorMeasurement('h2_ppm', 'MQ-5')
co2_ppm = SensorMeasurement('co2', 'MQ-135')
co_ppm = SensorMeasurement('co', 'MQ-7')
pressure = SensorMeasurement('pressure', 'BMP280')
alcohol_ppm = SensorMeasurement('alcohol', 'MQ-135')
nh4_ppm = SensorMeasurement('nh4', 'MQ-135')
bmp_temperature = SensorMeasurement('temperature', 'BMP280')


logger.info("Initializing InfluxDB client...")
try:
    # Initialize InfluxDB client using configuration
    influx_client = InfluxDBClient(
        CONFIG['INFLUX_HOST'],
        CONFIG['INFLUX_PORT'],
        CONFIG['INFLUX_USER'],
        CONFIG['INFLUX_PASSWORD'],
        CONFIG['INFLUX_DB']
    )
    logger.info("InfluxDB client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize InfluxDB client: {e}")
    raise


def update_measurements(data: List[str], timepoint: int) -> List[SensorMeasurement]:
    """Update measurement objects with new data and timestamp."""
    try:
        h2_ppm.value = float(data[0])
        # data[1] is DHT22 temperature - replaced with AHT10
        # data[2] is DHT22 humidity - replaced with AHT10
        alcohol_ppm.value = float(data[3])
        co2_ppm.value = float(data[4])
        nh4_ppm.value = float(data[5])
        co_ppm.value = float(data[6])
        temperature.value = float(data[7])  # AHT10 temperature
        humidity.value = float(data[8])  # AHT10 humidity
        pressure.value = float(data[9])
        # data[10] is altitude - no need
        # bmp_temperature.value = float(data[11]) - duplicate

        measurements = [
            temperature, humidity, h2_ppm, co2_ppm, co_ppm,
            pressure, alcohol_ppm, nh4_ppm
        ]

        for measurement in measurements:
            measurement.time = timepoint

        logger.debug(f"Updated measurements - Temp(AHT10): {temperature.value}°C, "
                     f"Humidity(AHT10): {humidity.value}%, H2: {h2_ppm.value}ppm, "
                     f"CO2: {co2_ppm.value}ppm, CO: {co_ppm.value}ppm, "
                     f"Pressure: {pressure.value}hPa, Alcohol: {alcohol_ppm.value}ppm, "
                     f"NH4: {nh4_ppm.value}ppm")

        return measurements
    except (ValueError, IndexError) as e:
        logger.error(f"Error updating measurements: {e}")
        raise


if __name__ == '__main__':
    logger.info("Starting sensor monitoring service...")

    while True:
        try:
            logger.info(f"Attempting to connect to {CONFIG['DEVICE']}...")
            ser = serial.Serial(CONFIG["DEVICE"], CONFIG["BAUD_RATE"], timeout=CONFIG["TIMEOUT"])
            ser.reset_input_buffer()
            logger.info("Serial connection established successfully")

            while True:
                try:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8').rstrip()
                        logger.debug(f'Raw data from arduino: {line}')

                        data = line.split('|')
                        if len(data) >= 12:
                            timepoint = int(time.time())
                            measurements = update_measurements(data, timepoint)

                            influx_client.write_points(
                                [m.to_influx_format() for m in measurements],
                                time_precision='s'
                            )
                            logger.debug("Data successfully written to InfluxDB")
                        else:
                            logger.warning(
                                f"Invalid data format. Expected at least 12 values, received {len(data)}. "
                                f"Data: {data}"
                            )
                except Exception as e:
                    logger.error(f"Error processing data: {e}", exc_info=True)
                    time.sleep(1)
                    continue
                time.sleep(1)

        except Exception as e:
            logger.error(f"Failed to connect to device {CONFIG['DEVICE']}: {e}", exc_info=True)
            time.sleep(1)