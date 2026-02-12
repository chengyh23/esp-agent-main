---
name: dht11-sensor
description: Read temperature and humidity from DHT11 sensors. Use when implementing environmental monitoring, IoT sensor integration, or climate control logic.
---

# DHT11 Temperature & Humidity Sensor

## Arduino

Install the DHT11 library in Arduino IDE > Manage Libraries > search "DHT11".

Basic usage → See [resources/ReadTempAndHumidity.ino](resources/ReadTempAndHumidity.ino)

## ESP-IDF

Include [resources/dht11.h](resources/dht11.h) and use DHT11_init(gpio_num_t) to initialize the sensor on the specified GPIO pin. Use DHT11_read() to read temperature and humidity values, which returns a dht11_reading struct containing the data.

Usage example → See [resources/dht11.c](resources/dht11.c)