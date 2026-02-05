"""LangGraph agent for creating Arduino projects from design descriptions.

Reads a design file or description and generates an Arduino ready project.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

from .config import config
from .skillsets import get_skillset, ARDUINO_MEGA_2560_R3
from .wiring_diagrams import save_wiring_diagram_all_formats, save_wiring_diagram_json

class Context(TypedDict):
    """Context parameters for the agent.

    Set these when creating assistants OR when invoking the graph.
    See: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
    """

    project_name: str


@dataclass
class State:
    """Input state for the agent.

    Defines the initial structure of incoming data.
    See: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
    """

    design_file: str = ""  # Path to file containing design description
    design: str = ""  # The actual design text
    arduino_code: str = ""  # Generated Arduino code
    wiring_diagram: str = ""  # Generated wiring diagram (structured text/JSON)
    wiring_diagram_svg: str = ""  # SVG representation of wiring diagram
    additional_info: str = ""  # Additional documentation
    message: str = ""
    platform: str = "arduino-mega-2560-r3"  # Target platform


async def read_design(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Read and parse the design file."""
    if not state.design_file or not os.path.exists(state.design_file):
        raise ValueError(f"Design file not found: {state.design_file}")
    
    with open(state.design_file, 'r') as f:
        design = f.read().strip()
    
    if not design:
        raise ValueError("Design file is empty")
    
    print(f"📄 Read design from {state.design_file}")
    return {"design": design}


async def generate_code(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Generate Arduino code based on the design."""
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set in configuration")
    
    # Get platform skillset
    try:
        skillset = get_skillset(state.platform)
    except ValueError as e:
        raise ValueError(f"Invalid platform specified: {e}")
    
    model = ChatAnthropic(
        model=config.ANTHROPIC_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        max_retries=config.MAX_RETRIES,
        timeout=config.TIMEOUT_SECONDS
    )

    design_text = state.design or ""
    design_lower = design_text.lower()
    wants_timer = any(keyword in design_lower for keyword in ["timer", "timer interrupt", "timerinterrupt"])
    wants_lcd = any(keyword in design_lower for keyword in ["lcd", "display", "screen", "tft", "ili9341"])
    wants_dht11 = "dht11" in design_lower
    wants_mpu6050 = any(keyword in design_lower for keyword in ["mpu 6050", "mpu6050"])
    wants_wifi = any(keyword in design_lower for keyword in ["wifi", "web server", "http", "mqtt"])
    print(f"🧠 Generating Arduino code for design (timer: {wants_timer}, lcd: {wants_lcd}, dht11: {wants_dht11}, mpu6050: {wants_mpu6050}, wifi: {wants_wifi})")

    prompt_lines = [
        f"You are an expert Arduino developer specializing in {skillset.platform_name} ({skillset.mcu}) development. Generate ONLY the Arduino .ino code based on this design.",
        "",
        f"Design: {design_text}",
        "",
        skillset.get_specs_text(),
        "",
        skillset.get_gpio_reference(),
        "",
        "AVAILABLE ARDUINO LIBRARIES:",
    ]

    if skillset.header_files:
        for header, purpose in skillset.header_files.items():
            if not header.startswith('<'):
                prompt_lines.append(f"- {header}: {purpose}")

    prompt_lines.extend([
        "",
        "CRITICAL ARDUINO REQUIREMENTS:",
        "- Target: Arduino Mega 2560 R3 using Arduino framework",
        "- Use standard Arduino functions: pinMode(), digitalWrite(), digitalRead(), analogRead(), etc.",
        "- Include setup() and loop() functions",
        "- Use Serial.begin() for serial communication",
        "- Use delay() or millis() for timing",
        "- Include proper library includes at the top (e.g., #include <WiFi.h>, #include <Wire.h>)",
        "- Use GPIO pin numbers directly (e.g., 5, 18, 19)",
        "- For I2C, use Wire.begin(SDA, SCL) with specific pins",
        "- For SPI, use SPI.begin(SCK, MISO, MOSI, SS)",
        "",
    ])
    if wants_timer:
        # https://github.com/khoih-prog/TimerInterrupt/blob/master/examples/Argument_Simple/Argument_Simple.ino
        timer_template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates_arduino', 'timer_interrupt', 'Argument_Simple.ino')
        if os.path.exists(timer_template_path):
            with open(timer_template_path, 'r') as template_file:
                timer_template = template_file.read().strip()
            prompt_lines.extend([
                "",
                "REFERENCE TIMER INTERRUPT USAGE EXAMPLE (adapt it to satisfy the current design):",
                "```c",
                timer_template,
                "```",
            ])
    if wants_lcd:
        prompt_lines.extend([
            "For LCD/TFT displays:",
            "- Use libraries like Adafruit_GFX, TFT_eSPI, or LovyanGFX",
            "- Initialize display in setup()",
            "- Use appropriate pin configurations for SPI interface",
            "",
        ])

    if wants_dht11:
        # https://github.com/dhrubasaha08/DHT11/blob/main/examples/ReadTempAndHumidity/ReadTempAndHumidity.ino
        dht11_template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates_arduino', 'dht11', 'ReadTempAndHumidity.ino')
        if os.path.exists(dht11_template_path):
            with open(dht11_template_path, 'r') as template_file:
                dht11_template = template_file.read().strip()
            prompt_lines.extend([
                "",
                "REFERENCE DHT11 USAGE EXAMPLE:",
                "```c",
                dht11_template,
                "```",
            ])

    if wants_mpu6050:
        # https://github.com/adafruit/Adafruit_MPU6050/blob/master/examples/basic_readings/basic_readings.ino
        mpu6050_template_path = os.path.join(os.path.dirname(__file__), '..', '..', 'templates_arduino', 'mpu6050', 'basic_readings.ino')
        if os.path.exists(mpu6050_template_path):
            with open(mpu6050_template_path, 'r') as template_file:
                mpu6050_template = template_file.read().strip()
            prompt_lines.extend([
                "",
                "REFERENCE MPU6050 USAGE EXAMPLE (adapt it to satisfy the current design):",
                "```c",
                mpu6050_template,
                "```",
            ])

    if wants_wifi:
        prompt_lines.extend([
            "For WiFi functionality:",
            "- #include <WiFi.h>",
            "- Use WiFi.begin(ssid, password) to connect",
            "- Check connection with WiFi.status() == WL_CONNECTED",
            "",
        ])

    prompt_lines.append("Output ONLY the complete, compilable Arduino .ino code with all necessary includes, setup(), and loop() functions. No explanations or markdown formatting.")

    prompt = "\n".join(prompt_lines)
    
    response = await model.ainvoke(prompt)
    code = response.content.strip()
    
    # Clean up any markdown formatting
    if code.startswith('```cpp') or code.startswith('```c++') or code.startswith('```arduino'):
        code = code.split('\n', 1)[1].strip()
    if code.startswith('```c'):
        code = code[4:].strip()
    if code.startswith('```'):
        code = code[3:].strip()
    if code.endswith('```'):
        code = code[:-3].strip()
    
    # Extract only the code
    lines = code.split('\n')
    clean_lines = []
    
    for line in lines:
        line_upper = line.upper()
        if ('**WIRING DIAGRAM**' in line_upper or 
            '**CONNECTION' in line_upper or 
            '=== WIRING' in line_upper or
            line.strip().startswith('# ') and 'wiring' in line.lower()):
            break
        clean_lines.append(line)
    
    code = '\n'.join(clean_lines).strip()
    
    # Additional cleanup
    if '}' in code:
        last_brace = code.rfind('}')
        potential_end = code[last_brace + 1:]
        if potential_end.strip() and not potential_end.strip().startswith('//'):
            code = code[:last_brace + 1].strip()
    
    print("💻 Generated Arduino code")
    return {"arduino_code": code}


async def generate_diagram(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Generate wiring diagrams and documentation based on the design."""
    if not config.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set in configuration")
    
    # Get platform skillset
    try:
        skillset = get_skillset(state.platform)
    except ValueError as e:
        raise ValueError(f"Invalid platform specified: {e}")
    
    model = ChatAnthropic(
        model=config.ANTHROPIC_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        max_retries=config.MAX_RETRIES,
        timeout=config.TIMEOUT_SECONDS
    )
    
    # Adapt prompt based on platform
    if "mega" in state.platform.lower() or "arduino" in state.platform.lower():
        board_specific_info = """
Official Arduino Mega 2560 R3 pinout reference:
- 54 digital I/O pins (D0-D53), 15 with PWM
- 16 analog input pins (A0-A15)
- 4 hardware serial ports (Serial, Serial1, Serial2, Serial3)
- SPI: pins 50 (MISO), 51 (MOSI), 52 (SCK), 53 (SS)
- I2C: pins 20 (SDA), 21 (SCL)
- Use standard Arduino pin numbering (e.g., D13 for built-in LED, A0 for analog pin 0)
"""
    else:
        board_specific_info = ""
    
    prompt_lines = [
        f"You are an expert hardware engineer specializing in {skillset.platform_name} (Arduino) development. Generate wiring diagrams and documentation based on this design.",
        "",
        f"Design: {state.design}",
        "",
        skillset.get_specs_text(),
        "",
        skillset.get_gpio_reference(),
        "",
        board_specific_info,
        "Generate comprehensive wiring instructions using standard Arduino conventions.",
        "",
        "Format your response exactly as:",
        "",
        "=== WIRING DIAGRAM ===",
        "[Provide clear pin-to-pin connections using Arduino pin names (D0-D53, A0-A15)]",
        "",
        "=== ADDITIONAL INFO ===",
        "[Setup instructions, component lists, power requirements, required Arduino libraries, and notes]",
        "",
        "Be specific with pin numbers matching the Arduino Mega 2560 R3 layout.",
    ]
    prompt = "\n".join(prompt_lines)
    
    response = await model.ainvoke(prompt)
    content = response.content.strip()
    
    # Parse the response into sections
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        if '=== ' in line and ' ===' in line:
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            start = line.find('===') + 4
            end = line.rfind('===')
            section_name = line[start:end].strip().lower().replace(' ', '_')
            current_section = section_name
            current_content = []
        elif current_section is not None and line.strip():
            if not line.strip().startswith('```'):
                current_content.append(line)
        elif current_section is not None and not line.strip():
            current_content.append(line)
    
    if current_section:
        sections[current_section] = '\n'.join(current_content).strip()
    
    wiring_diagram = sections.get('wiring_diagram', '')
    additional_info = sections.get('additional_info', '')
    
    print(f"🔌 Generated wiring diagram ({len(wiring_diagram)} chars) and documentation")
    
    return {
        "wiring_diagram": wiring_diagram,
        "additional_info": additional_info
    }


async def assemble_project(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Assemble the final Arduino project from generated components."""
    project_name = (runtime.context or {}).get('project_name', config.DEFAULT_PROJECT_NAME)
    project_dir = f"./{project_name}"
    
    # Create project directory
    os.makedirs(project_dir, exist_ok=True)
    
    # Write the generated Arduino code as .ino file
    if state.arduino_code:
        ino_path = os.path.join(project_dir, f"{project_name}.ino")
        with open(ino_path, "w") as f:
            f.write(state.arduino_code)
    
    # Save wiring diagrams in multiple formats
    if state.wiring_diagram:
        try:
            saved_diagram_files = save_wiring_diagram_all_formats(
                wiring_diagram_text=state.wiring_diagram,
                additional_info=state.additional_info,
                project_dir=project_dir,
                project_name=project_name,
                platform=state.platform
            )
        except Exception as e:
            print(f"❌ Error saving wiring diagrams: {e}")
            import traceback
            traceback.print_exc()
    
    # Write additional info to README
    readme_content = f'''# {project_name}

## Project Description
{state.design}

## Additional Information
{state.additional_info}

## Hardware Setup
See `WIRING.md` for complete hardware connection details.

## Arduino IDE Setup
1. Install Arduino IDE (version 2.0 or later recommended)
2. Add ESP32 board support:
   - Go to File > Preferences
   - Add to Additional Board Manager URLs: https://espressif.github.io/arduino-esp32/package_esp32_index.json
   - Go to Tools > Board > Boards Manager
   - Search for "esp32" and install "esp32 by Espressif Systems"
3. Select board: Tools > Board > ESP32 Arduino > ESP32S3 Dev Module
4. Install required libraries (see Additional Information section above)

## Uploading
1. Connect your ESP32-S3 board via USB
2. Select the correct COM port: Tools > Port
3. Click Upload button
4. Open Serial Monitor (Tools > Serial Monitor) to view output

## Generated Files
- {project_name}.ino - Main Arduino sketch
- README.md - This file
- WIRING.md - Wiring diagram and connections
'''
    
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    print("📦 Assembled complete Arduino project")
    print(f"📁 Project files saved to: {project_dir}/")
    return {
        "message": f"Arduino project '{project_name}' created successfully in ./{project_name}/"
    }


# Define the graph
graph = StateGraph(State, context_schema=Context)
graph = graph.add_node(read_design)
graph = graph.add_node(generate_code)

# Conditionally add wiring diagram generation based on configuration
if config.GENERATE_WIRING_DIAGRAM:
    graph = graph.add_node(generate_diagram)

graph = graph.add_node(assemble_project)

# Add edges
graph = graph.add_edge("__start__", "read_design")
graph = graph.add_edge("read_design", "generate_code")

if config.GENERATE_WIRING_DIAGRAM:
    graph = graph.add_edge("read_design", "generate_diagram")
    graph = graph.add_edge("generate_diagram", "assemble_project")
else:
    graph = graph.add_edge("generate_code", "assemble_project")

graph = graph.compile(name="Arduino Project Creator")
