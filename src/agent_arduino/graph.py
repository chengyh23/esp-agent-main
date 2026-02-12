"""LangGraph agent for creating {ESP_IDF/Arduino} projects from design descriptions.

Reads a design file or description and generates an {ESP_IDF/Arduino} ready project.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

from .config import get_config
from .skillsets import get_skillset
from .skillsets_espidf import get_skillset as get_skillset_espidf
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

    platform: str  # Target platform
    design_file: str = ""  # Path to file containing design description
    design: str = ""  # The actual design text
    firmware_code: str = ""  # Generated ESP-IDF/Arduino code
    wiring_diagram: str = ""  # Generated wiring diagram (structured text/JSON)
    wiring_diagram_svg: str = ""  # SVG representation of wiring diagram
    additional_info: str = ""  # Additional documentation
    message: str = ""

@dataclass
class StateESPIDF(State):

    sdkconfig: str = ""  # Reconciled sdkconfig content



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


def output_result(result: dict, args) -> None:
    """Output the result in requested format."""
    if args.json:
        json_result = {
            "task": result["task"],
            "firmware": result["firmware"],
        }
        output_text = json.dumps(json_result, indent=2)
    else:
        output_text = result["firmware"]

    if args.output:
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            f.write(output_text)
        print(f"Output saved to: {output_file}")
    else:
        print("\nGenerated Firmware:")
        print("=" * 60)
        print(output_text)
        print("=" * 60)
        
async def generate_code_loop(state: State):
    from agent_arduino.iot_agent import IoTAgent
    agent = IoTAgent(state.platform)
    with open("design.txt", "r") as f:
        args_task = f.read().strip()
    result = agent.run(args_task)
    # output_result(result, args)
    code = result["firmware"]
    print(f"💻 Generated {state.platform} code")
    return {"firmware_code": code}


async def generate_diagram(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Generate wiring diagrams and documentation based on the design."""
    config = get_config(state.platform)
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
    config = get_config(state.platform)
    project_name = (runtime.context or {}).get('project_name', config.DEFAULT_PROJECT_NAME)
    project_dir = f"./{project_name}"
    
    # Create project directory
    os.makedirs(project_dir, exist_ok=True)
    
    # Write the generated Arduino code as .ino file
    if state.firmware_code:
        ino_path = os.path.join(project_dir, f"{project_name}.ino")
        with open(ino_path, "w") as f:
            f.write(state.firmware_code)
    
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


async def assemble_project_espidf(state: StateESPIDF, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Assemble the final ESP-IDF project from generated components."""
    config = get_config(state.platform)
    project_name = (runtime.context or {}).get('project_name', config.DEFAULT_PROJECT_NAME)
    project_dir = f"./{project_name}"
    
    # Create project directory
    os.makedirs(project_dir, exist_ok=True)
    
    # Create root CMakeLists.txt
    cmake_content = f'''cmake_minimum_required(VERSION 3.16)

include($ENV{{IDF_PATH}}/tools/cmake/project.cmake)

project({project_name})
'''
    
    with open(os.path.join(project_dir, "CMakeLists.txt"), "w") as f:
        f.write(cmake_content)
    
    # Create main directory
    main_dir = os.path.join(project_dir, "main")
    os.makedirs(main_dir, exist_ok=True)

    # Detect if LCD support is required (based on config header usage)
    uses_lcd = bool(state.firmware_code and 'esp32s3_box_lcd_config.h' in state.firmware_code)
    # Detect if DHT11 sensor is used
    uses_dht11 = bool(state.firmware_code and 'dht11.h' in state.firmware_code)
    # Detect if MPU6050 is used
    uses_mpu6050 = bool(state.firmware_code and 'mpu6050' in state.firmware_code)

    # Create idf_component.yml in main component directory with conditional dependencies
    idf_component_lines = [
        'version: "1.0.0"',
        'description: "Main application component for ESP32-S3-BOX-3"',
        'dependencies:',
        '  idf: ">=5.0"',
    ]

    if uses_lcd:
        idf_component_lines.extend([
            '  lvgl/lvgl: ^9.2.0',
            '  esp_lcd_ili9341: ^1.0',
            '  espressif/esp_lvgl_port: ^2.6.0',
        ])
    if uses_mpu6050:
        idf_component_lines.append(
            '  espressif/mpu6050: ^1.1.1',  # idf.py add-dependency "espressif/mpu6050: "^1.1.1"
        )

    idf_component_yml = '\n'.join(idf_component_lines) + '\n'
    with open(os.path.join(main_dir, "idf_component.yml"), "w") as f:
        f.write(idf_component_yml)
    print("📝 Generated idf_component.yml in main/")
    
    # Create main CMakeLists.txt
    main_cmake_content = '''idf_component_register(SRCS "main.c"
                    INCLUDE_DIRS ".")'''
    
    with open(os.path.join(main_dir, "CMakeLists.txt"), "w") as f:
        f.write(main_cmake_content)
    
    # Copy LCD config header if needed
    if uses_lcd:
        header_src = os.path.join(
            os.path.dirname(__file__), '..', '..', 'templates', 'esp_idf', 'esp32s3_box_lcd_config.h'
        )
        header_dst = os.path.join(main_dir, 'esp32s3_box_lcd_config.h')
        if os.path.exists(header_src):
            import shutil
            shutil.copy2(header_src, header_dst)
            print("📄 Copied LCD config header to project")
    if uses_dht11:
        header_src = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'dht11', 'dht11.h')
        implementation_src = os.path.join(os.path.dirname(__file__), '..', '..', 'templates', 'dht11', 'dht11.c')
        header_dst = os.path.join(main_dir, 'dht11.h')
        implementation_dst = os.path.join(main_dir, 'dht11.c')
        if os.path.exists(header_src):
            import shutil
            shutil.copy2(header_src, header_dst)
            shutil.copy2(implementation_src, implementation_dst)
            print("📄 Copied DHT11 header and implementation to project")

    # Write the generated ESP-IDF code as main.c
    if state.firmware_code:
        with open(os.path.join(main_dir, "main.c"), "w") as f:
            f.write(state.firmware_code)
    
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
'''

    readme_content += '''
## Hardware Setup
See `WIRING.md` for complete hardware connection details.

Wiring diagrams are saved in multiple formats:

## Building and Flashing
```bash
idf.py build
idf.py flash
idf.py monitor
```

## Generated Files
'''
    with open(os.path.join(project_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    # Create basic sdkconfig
    with open(os.path.join(project_dir, "sdkconfig"), "w") as f:
        f.write('''# ESP-IDF SDK Configuration
CONFIG_ESPTOOLPY_FLASHMODE_QIO=y
CONFIG_ESPTOOLPY_FLASHFREQ_40M=y
''')
    if state.sdkconfig:
        with open(os.path.join(project_dir, "sdkconfig"), "w") as f:
            f.write(state.sdkconfig)
    
    # Create sdkconfig.defaults for IDF target
    with open(os.path.join(project_dir, "sdkconfig.defaults"), "w") as f:
        f.write('CONFIG_IDF_TARGET="esp32s3"\n')
    
    print("📦 Assembled complete ESP-IDF project")
    print(f"📁 Project files saved to: {project_dir}/")
    return {
        "message": f"ESP-IDF project '{project_name}' created successfully in ./{project_name}/"
    }

async def reconcile_sdkconfig(state: StateESPIDF, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Reconcile sdkconfig for ESP-IDF projects."""
    config = get_config("ESP-IDF")
    try:
        skillset = get_skillset_espidf(state.platform)
    except ValueError as e:
        raise ValueError(f"Invalid platform specified: {e}")

    model = ChatAnthropic(
        model=config.ANTHROPIC_MODEL,
        api_key=config.ANTHROPIC_API_KEY,
        max_retries=config.MAX_RETRIES,
        timeout=config.TIMEOUT_SECONDS
    )

    prompt_lines = [
        f"You are an ESP-IDF configuration expert. Analyze the ESP32 C code and ensure the sdkconfig is consistent with all compile-time requirements.",
        "",
        "Here is the generated ESP-IDF C code:",
        state.firmware_code,
        "",
        """Default sdkconfig is:

# ESP-IDF SDK Configuration
CONFIG_ESPTOOLPY_FLASHMODE_QIO=y
CONFIG_ESPTOOLPY_FLASHFREQ_40M=y
""",
        "Only make necessary changes to default sdkconfig to ensure all required features are enabled based on the generated code.",
        "Output ONLY sdkconfig. No explanations or markdown formatting."
    ]
    prompt = "\n".join(prompt_lines)
    response = await model.ainvoke(prompt)
    code = response.content.strip()

    if code.startswith('```'):
        code = code.split('\n', 1)[1] if '\n' in code else code[3:]
    if code.endswith('```'):
        code = code[:-3].strip()

    print("⚙️ Reconciled sdkconfig")
    return {"sdkconfig": code}


def build_graph(platform: str):
    """Build the appropriate graph based on platform.

    Args:
        platform: "Arduino" or "ESP-IDF"

    Returns:
        Compiled StateGraph for the specified platform
    """
    config = get_config(platform)

    if platform == "ESP-IDF":
        # ESP-IDF graph: read_design → generate_code_loop → reconcile_sdkconfig → assemble_project_espidf
        g = StateGraph(StateESPIDF, context_schema=Context)
        g = g.add_node(read_design)
        g = g.add_node(generate_code_loop)
        g = g.add_node(reconcile_sdkconfig)
        g = g.add_node(assemble_project_espidf)

        g = g.add_edge("__start__", "read_design")
        g = g.add_edge("read_design", "generate_code_loop")
        g = g.add_edge("generate_code_loop", "reconcile_sdkconfig")
        g = g.add_edge("reconcile_sdkconfig", "assemble_project_espidf")

        if config.GENERATE_WIRING_DIAGRAM:
            g = g.add_node(generate_diagram)
            g = g.add_edge("read_design", "generate_diagram")
            g = g.add_edge("generate_diagram", "assemble_project_espidf")

        return g.compile(name="ESP-IDF Project Creator")

    else:
        # Arduino graph: read_design → generate_code_loop → assemble_project
        g = StateGraph(State, context_schema=Context)
        g = g.add_node(read_design)
        g = g.add_node(generate_code_loop)
        g = g.add_node(assemble_project)

        g = g.add_edge("__start__", "read_design")
        g = g.add_edge("read_design", "generate_code_loop")
        g = g.add_edge("generate_code_loop", "assemble_project")

        if config.GENERATE_WIRING_DIAGRAM:
            g = g.add_node(generate_diagram)
            g = g.add_edge("read_design", "generate_diagram")
            g = g.add_edge("generate_diagram", "assemble_project")

        return g.compile(name="Arduino Project Creator")

