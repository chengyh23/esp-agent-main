"""Platform-specific skillsets for ESP-IDF project generation.

Each skillset contains comprehensive specifications, peripherals, GPIO mappings,
and generation prompts for a specific microcontroller platform.

Format is based on Anthropic's tool/skill schema for compatibility with AI model context.
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional


@dataclass
class Peripheral:
    """Represents a peripheral on the board."""
    name: str
    description: str
    interface: str  # SPI, I2C, UART, GPIO, I2S, etc.
    pins: Dict[str, int]  # e.g., {"MOSI": 11, "MISO": 13, "CLK": 14}
    notes: str = ""


@dataclass
class PlatformSkillset:
    """Complete specification and capabilities for a platform."""
    platform_name: str
    mcu: str
    description: str
    
    # General specs
    core_voltage: str
    clock_speed: str
    ram: str
    flash: str
    
    # Peripherals
    peripherals: Dict[str, Peripheral]
    
    # GPIO mapping
    gpio_mapping: Dict[str, str]  # e.g., {"LED_RED": "GPIO 4"}
    
    # Available interfaces
    available_interfaces: List[str]  # SPI, I2C, UART, etc.
    
    # Connectivity
    connectivity_features: List[str]
    
    # Hardware best practices and guidelines
    hardware_best_practices: Dict[str, str]
    
    # Important header files and their purposes
    header_files: Dict[str, str]

    # Compile-time configuration notes
    compile_time: Dict[str, str]
    
    # ESP-IDF version
    esp_idf_version: str = "5.5"
    
    def get_specs_text(self) -> str:
        """Generate board specifications text for prompts."""
        specs = f"""
{self.platform_name} Board Specifications:
- MCU: {self.mcu}
- ESP-IDF Version: {self.esp_idf_version}
- Core Voltage: {self.core_voltage}
- Clock Speed: {self.clock_speed}
- RAM: {self.ram}
- Flash: {self.flash}

Peripherals:
"""
        for name, peripheral in self.peripherals.items():
            specs += f"- {name}: {peripheral.description} ({peripheral.interface})\n"
        
        specs += "\nAvailable Interfaces:\n"
        for interface in self.available_interfaces:
            specs += f"- {interface}\n"
        
        specs += "\nConnectivity Features:\n"
        for feature in self.connectivity_features:
            specs += f"- {feature}\n"
        
        if self.hardware_best_practices:
            specs += "\nHardware Best Practices:\n"
            for practice, description in self.hardware_best_practices.items():
                specs += f"- {practice}: {description}\n"
        
        if self.header_files:
            specs += "\nImportant Header Files:\n"
            for header, purpose in self.header_files.items():
                specs += f"- {header}: {purpose}\n"
        
        if self.compile_time:
            specs += "\nCompile-Time Configuration Notes:\n"
            for item, note in self.compile_time.items():
                specs += f"- {item}: {note}\n"
        
        return specs
    
    def get_gpio_reference(self) -> str:
        """Generate GPIO reference text for prompts."""
        text = f"\n{self.platform_name} GPIO Reference:\n"
        for usage, gpio in sorted(self.gpio_mapping.items()):
            text += f"- {usage}: {gpio}\n"
        text += "You MUST choose GPIOs exclusively from the list above.\nDo NOT use any GPIO not explicitly listed here.\n"
        return text
    
    def to_anthropic_tool_format(self) -> Dict[str, Any]:
        """Export skillset as Anthropic tool/skill JSON schema.
        
        This format is compatible with Anthropic's tool use and can be passed
        to models for structured generation.
        """
        return {
            "type": "object",
            "name": self.platform_name.lower().replace("-", "_"),
            "description": f"Platform specifications and capabilities for {self.platform_name}",
            "properties": {
                "platform_name": {
                    "type": "string",
                    "description": "Name of the platform",
                    "const": self.platform_name
                },
                "mcu": {
                    "type": "string",
                    "description": "Microcontroller unit details"
                },
                "specifications": {
                    "type": "object",
                    "properties": {
                        "core_voltage": {"type": "string"},
                        "clock_speed": {"type": "string"},
                        "ram": {"type": "string"},
                        "flash": {"type": "string"}
                    }
                },
                "peripherals": {
                    "type": "object",
                    "description": "Available peripherals and their specifications",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "interface": {"type": "string"},
                            "pins": {"type": "object"},
                            "notes": {"type": "string"}
                        }
                    }
                },
                "gpio_mapping": {
                    "type": "object",
                    "description": "GPIO pin assignments and mappings"
                },
                "available_interfaces": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Available communication interfaces"
                },
                "connectivity_features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Available connectivity features"
                },
                "hardware_best_practices": {
                    "type": "object",
                    "description": "Hardware implementation best practices and guidelines",
                    "additionalProperties": {"type": "string"}
                },
                "header_files": {
                    "type": "object",
                    "description": "Important header files and their purposes",
                    "additionalProperties": {"type": "string"}
                },
                "compile_time": {
                    "type": "object",
                    "description": "Compile-time configuration notes",
                    "additionalProperties": {"type": "string"}
                }
            }
        }
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Export skillset as JSON-compatible dictionary.
        
        Useful for saving to files, APIs, or tool contexts.
        """
        peripherals_json = {}
        for name, peripheral in self.peripherals.items():
            peripherals_json[name] = {
                "name": peripheral.name,
                "description": peripheral.description,
                "interface": peripheral.interface,
                "pins": peripheral.pins,
                "notes": peripheral.notes
            }
        
        return {
            "platform": self.platform_name,
            "description": self.description,
            "mcu": self.mcu,
            "specifications": {
                "core_voltage": self.core_voltage,
                "clock_speed": self.clock_speed,
                "ram": self.ram,
                "flash": self.flash
            },
            "peripherals": peripherals_json,
            "gpio_mapping": self.gpio_mapping,
            "available_interfaces": self.available_interfaces,
            "connectivity_features": self.connectivity_features,
            "hardware_best_practices": self.hardware_best_practices,
            "header_files": self.header_files,
            "compile_time": self.compile_time,
        }
    
    def save_to_json(self, filepath: str) -> None:
        """Save skillset as JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_json_schema(), f, indent=2)
        print(f"💾 Saved skillset to {filepath}")


# ESP32-S3-BOX-3 Skillset
ESP32_S3_BOX_3 = PlatformSkillset(
    platform_name="ESP32-S3-BOX-3",
    mcu="ESP32-S3-WROOM-1 (Dual-core Xtensa LX7)",
    description="Compact AI development board with integrated display and audio",
    
    core_voltage="3.3V",
    clock_speed="240MHz",
    ram="512KB SRAM + 8MB PSRAM",
    flash="8MB QSPI Flash",
    esp_idf_version="5.5",
    
    peripherals={
        "Display": Peripheral(
            name="Display",
            description="2.4-inch LCD TFT",
            interface="SPI",
            pins={"CS": 5, "DC": 4, "RST": 9, "CLK": 7, "MOSI": 6},
            notes="320x240 resolution, ST7789 controller"
        ),
        "Microphone": Peripheral(
            name="Microphone",
            description="Digital MEMS Microphone",
            interface="I2S",
            pins={"CLK": 32, "WS": 33, "SD": 34},
            notes="MSM261S4030H0, PDM interface"
        ),
        "Speaker": Peripheral(
            name="Speaker",
            description="Audio amplifier with speaker",
            interface="I2S",
            pins={"LRCK": 33, "BCLK": 32, "DOUT": 35},
            notes="NS4150 amplifier, mono output"
        ),
        "IMU": Peripheral(
            name="6-Axis IMU",
            description="Inertial Measurement Unit",
            interface="I2C",
            pins={"SDA": 8, "SCL": 9},
            notes="QMI8658, 3-axis accelerometer + 3-axis gyroscope"
        ),
        "Ambient Light Sensor": Peripheral(
            name="Ambient Light Sensor",
            description="Light intensity sensor",
            interface="I2C",
            pins={"SDA": 8, "SCL": 9},
            notes="Provides ambient light level"
        ),
        "RGB LED": Peripheral(
            name="RGB LED",
            description="Programmable RGB indicator LED",
            interface="GPIO",
            pins={"RED": 21, "GREEN": 47, "BLUE": 48},
            notes="Common anode configuration"
        ),
        "White LED": Peripheral(
            name="White LED",
            description="Ambient light indicator",
            interface="GPIO",
            pins={"LED": 46},
            notes="Status indicator"
        ),
    },
    
    gpio_mapping={
        "RST Button": "RESET",
        "Display CS": "GPIO 5",
        "Display DC": "GPIO 4",
        "Display RST": "GPIO 9",
        "Display CLK (SPI)": "GPIO 7",
        "Display MOSI (SPI)": "GPIO 6",
        "Display MISO (SPI)": "GPIO 8",
        "IMU SDA": "GPIO 8",
        "IMU SCL": "GPIO 9",
        "Microphone CLK": "GPIO 32",
        "Microphone WS": "GPIO 33",
        "Microphone SD": "GPIO 34",
        "Speaker LRCK": "GPIO 33",
        "Speaker BCLK": "GPIO 32",
        "Speaker DOUT": "GPIO 35",
        "RGB LED Red": "GPIO 21",
        "RGB LED Green": "GPIO 47",
        "RGB LED Blue": "GPIO 48",
        "White LED": "GPIO 46",
        # Bread Breakout Board - Fixed Pin Mapping (based on ESP32-S3-BOX-3-BREAD official layout)
        # "Bread GPIO 1": "GPIO 1",
        # "Bread GPIO 2": "GPIO 2", 
        # "Bread GPIO 3": "GPIO 3",
        # "Bread GPIO 4": "GPIO 4",
        # "Bread GPIO 5": "GPIO 5",
        # "Bread GPIO 6": "GPIO 6",
        # "Bread GPIO 7": "GPIO 7",
        # "Bread GPIO 8": "GPIO 8",
        "Bread GPIO 9": "GPIO 9",
        "Bread GPIO 10": "GPIO 10",
        "Bread GPIO 11": "GPIO 11",
        "Bread GPIO 12": "GPIO 12",
        "Bread GPIO 13": "GPIO 13", 
        "Bread GPIO 14": "GPIO 14",
        # "Bread GPIO 15": "GPIO 15",
        # "Bread GPIO 16": "GPIO 16",
        # "Bread GPIO 17": "GPIO 17",
        # "Bread GPIO 18": "GPIO 18",
        "Bread GPIO 19": "GPIO 19",
        "Bread GPIO 20": "GPIO 20",
        "Bread GPIO 21": "GPIO 21",
        # "Bread GPIO 35": "GPIO 35",
        # "Bread GPIO 36": "GPIO 36",
        # "Bread GPIO 37": "GPIO 37",
        "Bread GPIO 38": "GPIO 38",
        "Bread GPIO 39": "GPIO 39",
        "Bread GPIO 40": "GPIO 40",
        "Bread GPIO 41": "GPIO 41",
        "Bread GPIO 42": "GPIO 42",
        "Bread GPIO 43": "GPIO 43",
        "Bread GPIO 44": "GPIO 44",
        
        # "GPIO_NUM_9": "9",
        # "GPIO_NUM_10": "10",
        # "GPIO_NUM_11": "11",
        # "GPIO_NUM_12": "12",
        # "GPIO_NUM_13": "13", 
        # "GPIO_NUM_14": "14",
        # "GPIO_NUM_19": "19",
        # "GPIO_NUM_20": "20",
        # "GPIO_NUM_21": "21",
        # "GPIO_NUM_38": "38",
        # "GPIO_NUM_39": "39",
        # "GPIO_NUM_40": "40",
        # "GPIO_NUM_41": "41",
        # "GPIO_NUM_42": "42",
        # "GPIO_NUM_42": "43",
        # "GPIO_NUM_42": "44",

        "Bread GND": "GND",
        "Bread 3.3V": "3.3V",
        
        # https://github.com/espressif/esp-idf/blob/v5.5/components/soc/esp32s3/include/soc/adc_channel.h
        # "ADC1_CHANNEL_0_GPIO_NUM": "1",
        # "ADC1_CHANNEL_1_GPIO_NUM": "2",
        # "ADC1_CHANNEL_2_GPIO_NUM": "3",
        # "ADC1_CHANNEL_3_GPIO_NUM": "4",
        # "ADC1_CHANNEL_4_GPIO_NUM": "5",
        # "ADC1_CHANNEL_5_GPIO_NUM": "6",
        # "ADC1_CHANNEL_6_GPIO_NUM": "7",
        # "ADC1_CHANNEL_7_GPIO_NUM": "8",
        "ADC1_CHANNEL_8_GPIO_NUM": "9",
        "ADC1_CHANNEL_9_GPIO_NUM": "10",
        "ADC2_CHANNEL_0_GPIO_NUM": "11",
        "ADC2_CHANNEL_1_GPIO_NUM": "12",
        "ADC2_CHANNEL_2_GPIO_NUM": "13",
        "ADC2_CHANNEL_3_GPIO_NUM": "14",
        # "ADC2_CHANNEL_4_GPIO_NUM": "15",
        # "ADC2_CHANNEL_5_GPIO_NUM": "16",
        # "ADC2_CHANNEL_6_GPIO_NUM": "17",
        # "ADC2_CHANNEL_7_GPIO_NUM": "18",
        "ADC2_CHANNEL_8_GPIO_NUM": "19",
        "ADC2_CHANNEL_9_GPIO_NUM": "20",
    },
    
    available_interfaces=[
        "SPI (Display interface)",
        "I2C (Sensors)",
        "I2S (Audio)",
        "UART (Serial communication)",
        "GPIO (General purpose I/O)",
        "ADC (Analog to Digital conversion)",
        "PWM (Pulse Width Modulation)",
    ],
    
    connectivity_features=[
        "USB Type-C (power and programming)",
        "Battery connector",
        "Bread breakout board for GPIO access",
        "Wi-Fi 802.11 b/g/n",
        "Bluetooth 5.0 (LE + BR/EDR)",
    ],
    
    hardware_best_practices={
        "GPIO Interrupt Button Handling": "When binding GPIO interrupts to buttons, always implement 50ms debounce. Button press should be detected as logic HIGH read by GPIO. Use GPIO_INTR_POSEDGE for rising edge detection with internal pull-down resistor.",
        "Button Debounce Implementation": "Always implement software debouncing with 50ms delay in interrupt service routines. Use FreeRTOS queues to communicate button events from ISR to task level.",
        "GPIO Configuration for Buttons": "Configure button GPIOs with GPIO_MODE_INPUT, enable internal pull-down resistors (GPIO_PULLDOWN_ENABLE), and use GPIO_INTR_POSEDGE for interrupt on rising edge.",
        "Interrupt Service Routine": "Keep ISR functions short and fast.",
        "Timer Implementation": "Use esp_timer for high-resolution timing and periodic tasks. Prefer esp_timer over legacy timer APIs for ESP-IDF 5.5+. Create one-shot or periodic timers with esp_timer_create() and manage with esp_timer_start_once() or esp_timer_start_periodic().",
        "ESP Timer Best Practices": "For periodic tasks, use esp_timer with microsecond precision. Register timer callbacks that run in timer task context. Avoid blocking operations in timer callbacks. Use ESP_TIMER_TASK for timer callback execution.",
        "Timer vs GPTimer": "Use esp_timer for general-purpose timing needs. Use gptimer for hardware-timed PWM generation or precise hardware timing requirements.",
        "LEDC PWM Controller": "Use LEDC (LED Control) for PWM applications including breathing LEDs, motor control, servo positioning, RGB LEDs, and buzzer tone generation. Supports up to 8 channels with configurable frequency and duty resolution.",
        "LEDC Configuration": "Configure LEDC timers first with ledc_timer_config(), then channels with ledc_channel_config(). Use LEDC_AUTO_CLK for automatic clock selection. Set appropriate duty resolution (8-15 bits) based on precision needs.",
        "LEDC Breathing LED": "For breathing/fading effects, use LEDC with gradual duty cycle changes in a loop. Calculate max_duty as (1 << duty_resolution) - 1. Use ledc_set_duty() and ledc_update_duty() for smooth transitions.",
        "LEDC vs Software PWM": "Prefer LEDC over software PWM for better precision and CPU efficiency. LEDC runs in hardware with minimal CPU overhead, ideal for multiple PWM channels.",
        "LEDC Frequency Selection": "Choose LEDC frequency based on application: 50Hz for servos, 1-5kHz for LEDs, 2-4kHz for buzzers. Higher frequencies reduce audible noise but may limit duty resolution.",
        "LCD Pin Macro Usage": "For all LCD/display code, you MUST use the macros defined in 'esp32s3_box_lcd_config.h' for all pin assignments and configuration values (e.g., EXAMPLE_PIN_NUM_BK_LIGHT, EXAMPLE_PIN_NUM_SCLK, etc.). Do NOT use hardcoded GPIO numbers or values. Follow the canonical style in 'templates/esp_idf/esp32s3_lcd_template.c'.",
        "LCD Component Dependencies": "If the embedded LCD is used, you MUST add the following to idf_component.yml dependencies: lvgl/lvgl: ^9.2.0, esp_lcd_ili9341: ^1.0, espressif/esp_lvgl_port: ^2.6.0. This ensures all required display and graphics libraries are available for ESP-IDF build.",
        "DHT11": "When using the DHT11 temperature and humidity sensor, include 'dht11.h' and use DHT11_init(gpio_num_t) to initialize the sensor on the specified GPIO pin. Use DHT11_read() to read temperature and humidity values, which returns a dht11_reading struct containing the data.",
    },
    
    header_files={
        "<stdio.h>": "Standard I/O functions like printf() for debugging output",
        "<stdlib.h>": "Standard library functions including memory allocation",
        "<freertos/FreeRTOS.h>": "FreeRTOS kernel API for task management, queues, and synchronization",
        "<freertos/task.h>": "FreeRTOS task creation, deletion, and control functions",
        "<freertos/queue.h>": "FreeRTOS queue API for inter-task communication",
        "<driver/gpio.h>": "GPIO driver for configuring and controlling GPIO pins",
        "<driver/ledc.h>": "LED Control (PWM) driver for LED dimming and motor control",
        "<driver/gptimer.h>": "General Purpose Timer driver for periodic interrupts and timing",
        "<esp_timer.h>": "High-resolution timer API for one-shot and periodic timers",
        "<esp_log.h>": "Logging macros (ESP_LOGI, ESP_LOGE, etc.) for debug output",
        "<esp_err.h>": "ESP-IDF error codes and error checking macros",
        "<esp_system.h>": "System-level functions including restart and chip information",
        "<nvs_flash.h>": "Non-Volatile Storage (NVS) for persistent data storage",
        "<esp_wifi.h>": "Wi-Fi driver for wireless connectivity",
        "<esp_bt.h>": "Bluetooth driver for BLE and classic Bluetooth",
        "esp32s3_box_lcd_config.h": "LCD configuration header for ESP32-S3-BOX with ILI9341 controller, SPI pin definitions, and LVGL display settings (available as template in templates/esp_idf/)",
        "dht11.h": "DHT11 temperature and humidity sensor driver. DHT11_init(gpio_num_t) - Initialize sensor on specified GPIO pin. DHT11_read() - Read temperature/humidity, returns dht11_reading struct",
    },

    compile_time={
        "sdkconfig-font": "Ensure the font used in  ESP-IDF C code is enabled in sdkconfig. Read ESP-IDF C code written by generate_code, if lv_font_montserrat_<number> is found in the ESP_IDF C code, then ensure set CONFIG_LV_FONT_MONTSERRAT_<number>=y (not =n) in sdkconfig. Run scripts/configure_lvgl_fonts.py to do this step.",

    }
)


# Registry of available skillsets
SKILLSETS: Dict[str, PlatformSkillset] = {
    "esp32-s3-box-3": ESP32_S3_BOX_3,
    "esp32-s3-box3": ESP32_S3_BOX_3,  # Alias
    "box-3": ESP32_S3_BOX_3,  # Alias
}


def get_skillset(platform_name: str) -> PlatformSkillset:
    """Get a skillset by platform name."""
    name = platform_name.lower().strip()
    if name not in SKILLSETS:
        available = ", ".join(SKILLSETS.keys())
        raise ValueError(
            f"Unknown platform: {platform_name}\n"
            f"Available platforms: {available}"
        )
    return SKILLSETS[name]


def get_available_platforms() -> List[str]:
    """Get list of available platforms."""
    return list(SKILLSETS.keys())
