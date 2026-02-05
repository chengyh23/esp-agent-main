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
    
    # Arduino framework version
    arduino_version: str = "1.8.19"
    
    def get_specs_text(self) -> str:
        """Generate board specifications text for prompts."""
        specs = f"""
{self.platform_name} Board Specifications:
- MCU: {self.mcu}
- Arduino Framework Version: {self.arduino_version}
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
        return text
    
    def to_anthropic_tool_format(self) -> Dict[str, Any]:
        """Export skillset as Anthropic tool/skill JSON schema."""
        return {
            "type": "object",
            "name": self.platform_name.lower().replace("-", "_").replace(" ", "_"),
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
        """Export skillset as JSON-compatible dictionary."""
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


# Arduino Mega 2560 R3 Skillset
ARDUINO_MEGA_2560_R3 = PlatformSkillset(
    platform_name="Arduino Mega 2560 R3",
    mcu="ATmega2560 (8-bit AVR)",
    description="High-performance Arduino board with extensive I/O capabilities",
    
    core_voltage="5V",
    clock_speed="16MHz",
    ram="8KB SRAM",
    flash="256KB Flash (8KB used by bootloader)",
    arduino_version="1.8.19",
    
    peripherals={
        "Built-in LED": Peripheral(
            name="Built-in LED",
            description="Onboard LED connected to digital pin 13",
            interface="GPIO",
            pins={"LED": 13},
            notes="Useful for testing and status indication"
        ),
        "SPI": Peripheral(
            name="SPI Interface",
            description="Serial Peripheral Interface for high-speed communication",
            interface="SPI",
            pins={"MOSI": 51, "MISO": 50, "SCK": 52, "SS": 53},
            notes="Hardware SPI for faster communication with peripherals"
        ),
        "I2C": Peripheral(
            name="I2C/TWI Interface",
            description="Two-Wire Interface for sensor communication",
            interface="I2C",
            pins={"SDA": 20, "SCL": 21},
            notes="Also available on dedicated SDA/SCL pins near AREF"
        ),
        "UART0": Peripheral(
            name="Serial Port 0",
            description="Primary serial interface (USB)",
            interface="UART",
            pins={"RX": 0, "TX": 1},
            notes="Connected to USB-to-Serial converter"
        ),
        "UART1": Peripheral(
            name="Serial Port 1",
            description="Hardware serial port 1",
            interface="UART",
            pins={"RX": 19, "TX": 18},
            notes="Additional hardware serial"
        ),
        "UART2": Peripheral(
            name="Serial Port 2",
            description="Hardware serial port 2",
            interface="UART",
            pins={"RX": 17, "TX": 16},
            notes="Additional hardware serial"
        ),
        "UART3": Peripheral(
            name="Serial Port 3",
            description="Hardware serial port 3",
            interface="UART",
            pins={"RX": 15, "TX": 14},
            notes="Additional hardware serial"
        ),
    },
    
    gpio_mapping={
        # Digital Pins
        "Digital Pin 0 (RX0)": "D0",
        "Digital Pin 1 (TX0)": "D1",
        "Digital Pin 2 (PWM)": "D2",
        "Digital Pin 3 (PWM)": "D3",
        "Digital Pin 4 (PWM)": "D4",
        "Digital Pin 5 (PWM)": "D5",
        "Digital Pin 6 (PWM)": "D6",
        "Digital Pin 7 (PWM)": "D7",
        "Digital Pin 8 (PWM)": "D8",
        "Digital Pin 9 (PWM)": "D9",
        "Digital Pin 10 (PWM)": "D10",
        "Digital Pin 11 (PWM)": "D11",
        "Digital Pin 12 (PWM)": "D12",
        "Digital Pin 13 (PWM, LED)": "D13",
        "Digital Pin 14 (TX3)": "D14",
        "Digital Pin 15 (RX3)": "D15",
        "Digital Pin 16 (TX2)": "D16",
        "Digital Pin 17 (RX2)": "D17",
        "Digital Pin 18 (TX1)": "D18",
        "Digital Pin 19 (RX1)": "D19",
        "Digital Pin 20 (SDA)": "D20",
        "Digital Pin 21 (SCL)": "D21",
        "Digital Pin 22-53": "D22-D53",
        
        # PWM Pins
        "PWM Pin 2": "D2",
        "PWM Pin 3": "D3",
        "PWM Pin 4": "D4",
        "PWM Pin 5": "D5",
        "PWM Pin 6": "D6",
        "PWM Pin 7": "D7",
        "PWM Pin 8": "D8",
        "PWM Pin 9": "D9",
        "PWM Pin 10": "D10",
        "PWM Pin 11": "D11",
        "PWM Pin 12": "D12",
        "PWM Pin 13": "D13",
        "PWM Pin 44": "D44",
        "PWM Pin 45": "D45",
        "PWM Pin 46": "D46",
        
        # Analog Pins
        "Analog Pin A0": "A0",
        "Analog Pin A1": "A1",
        "Analog Pin A2": "A2",
        "Analog Pin A3": "A3",
        "Analog Pin A4": "A4",
        "Analog Pin A5": "A5",
        "Analog Pin A6": "A6",
        "Analog Pin A7": "A7",
        "Analog Pin A8": "A8",
        "Analog Pin A9": "A9",
        "Analog Pin A10": "A10",
        "Analog Pin A11": "A11",
        "Analog Pin A12": "A12",
        "Analog Pin A13": "A13",
        "Analog Pin A14": "A14",
        "Analog Pin A15": "A15",
        
        # SPI Pins
        "SPI MOSI": "D51",
        "SPI MISO": "D50",
        "SPI SCK": "D52",
        "SPI SS": "D53",
        
        # I2C Pins
        "I2C SDA": "D20",
        "I2C SCL": "D21",
        
        # Power Pins
        "5V Power": "5V",
        "3.3V Power": "3.3V",
        "Ground": "GND",
        "VIN": "VIN",
        "AREF": "AREF",
    },
    
    available_interfaces=[
        "GPIO (54 digital pins, 16 analog inputs)",
        "PWM (15 pins with 8-bit PWM)",
        "UART (4 hardware serial ports)",
        "SPI (Hardware SPI on pins 50-53)",
        "I2C/TWI (Hardware I2C on pins 20-21)",
        "ADC (16 analog inputs with 10-bit resolution)",
    ],
    
    connectivity_features=[
        "USB Type-B (power and programming via Serial)",
        "External power jack (7-12V recommended, 6-20V limits)",
        "ICSP header for ISP programming",
    ],
    
    hardware_best_practices={
        "GPIO Interrupt Handling": "Use attachInterrupt(digitalPinToInterrupt(pin), ISR, mode) for pins 2, 3, 18, 19, 20, 21. Use modes: LOW, CHANGE, RISING, FALLING. Keep ISR functions short and fast.",
        "ISR definition: if ESP32: void IRAM_ATTR buttonISR() {}, else: void buttonISR() {}"
        "Button Debounce": "Implement software debouncing with 50ms delay. Use volatile variables for ISR communication. Check button state in loop() after ISR sets flag.",
        "PWM Output": "Use analogWrite(pin, value) for PWM output (0-255). Available on 15 pins. PWM frequency is ~490Hz (pins 4,13) or ~980Hz (other PWM pins).",
        "Analog Input": "Use analogRead(pin) to read analog values (0-1023) from A0-A15. Reference voltage is 5V by default, configurable with analogReference().",
        "Serial Communication": "Use Serial (USB), Serial1, Serial2, Serial3 for hardware UART. Initialize with begin(baudrate). Common baud rates: 9600, 115200.",
        "I2C Communication": "Use Wire library. Initialize with Wire.begin(). Use Wire.beginTransmission(), Wire.write(), Wire.endTransmission() for writing. Wire.requestFrom() and Wire.read() for reading.",
        "SPI Communication": "Use SPI library. Initialize with SPI.begin(). Use SPI.transfer() for data exchange. Set SPI mode, bit order, and clock divider with SPI.setDataMode(), SPI.setBitOrder(), SPI.setClockDivider().",
        "Memory Management": "Arduino Mega has 8KB SRAM. Minimize global variables. Use F() macro for string literals in Serial.print() to save RAM. Use PROGMEM for constant data.",
        "Timers": "Use millis() for non-blocking timing. Avoid delay() in time-critical code. For precise timing, use Timer interrupts (Timer1, Timer3, Timer4, Timer5 available).",
        "Power Consumption": "Use sleep modes from avr/sleep.h for low power. Disable unused peripherals. Set unused pins as INPUT_PULLUP or OUTPUT LOW.",
        "MPU6050": "When using the MPU6050 IMU sensor, include <Adafruit_MPU6050.h>. Check the usage of MPU6050 by the dirver in MPU6050 USAGE EXAMPLE.",
    },
    
    header_files={
        "<Arduino.h>": "Main Arduino framework header (implicit, not needed in .ino files). Provides digitalWrite(), digitalRead(), analogRead(), pinMode(), delay(), millis(), etc.",
        "<Wire.h>": "I2C/TWI communication library for sensor interfacing",
        "<SPI.h>": "SPI communication library for high-speed peripheral communication",
        "<Servo.h>": "Servo motor control library (uses Timer1)",
        "<LiquidCrystal.h>": "LCD display library for HD44780-compatible displays",
        "<SD.h>": "SD card file system library",
        "<EEPROM.h>": "Internal EEPROM read/write library (4KB EEPROM on ATmega2560)",
        "<SoftwareSerial.h>": "Software-emulated serial communication (use hardware serial when possible)",
    },

    compile_time={
        "board": "Select 'Arduino Mega or Mega 2560' in Arduino IDE. Board: Arduino AVR Boards > Arduino Mega or Mega 2560. Processor: ATmega2560 (Mega 2560)",
        "platformio-ini": "Configure board in platformio.ini:\nboard = megaatmega2560\nframework = arduino\nboard_build.mcu = atmega2560\nboard_build.f_cpu = 16000000L",
        "memory-optimization": "Use F() macro for strings in Serial.print(F(\"text\")). Store constants in PROGMEM. Minimize global variables. Check memory usage with IDE: Sketch > Verify/Compile shows RAM usage.",
        "bootloader": "Arduino Mega uses Optiboot bootloader (8KB). Effective flash is 248KB for sketches.",
    }
)


# Registry of available skillsets
SKILLSETS: Dict[str, PlatformSkillset] = {
    "arduino-mega-2560-r3": ARDUINO_MEGA_2560_R3,
    "mega-2560": ARDUINO_MEGA_2560_R3,  # Alias
    "mega": ARDUINO_MEGA_2560_R3,  # Alias
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
