"""LangGraph agent for creating ESP-IDF projects from design descriptions.

Reads a design file or description and generates an ESP-IDF ready project.
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
from .skillsets import get_skillset, ESP32_S3_BOX_3
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
    esp_idf_code: str = ""  # Generated ESP-IDF C code
    wiring_diagram: str = ""  # Generated wiring diagram (structured text/JSON)
    wiring_diagram_svg: str = ""  # SVG representation of wiring diagram
    additional_info: str = ""  # Additional documentation
    message: str = ""
    platform: str = "esp32-s3-box-3"  # Target platform


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
    """Generate ESP-IDF C code based on the design."""
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
    wants_lcd = any(keyword in design_lower for keyword in ["lcd", "display", "screen", "tft", "ili9341"])

    prompt_lines = [
        f"You are an expert ESP-IDF {skillset.esp_idf_version} developer specializing in {skillset.platform_name} ({skillset.mcu}) development. Generate ONLY the ESP-IDF C code for main.c based on this design.",
        "",
        f"Design: {design_text}",
        "",
        skillset.get_specs_text(),
        "",
        skillset.get_gpio_reference(),
        "",
        "AVAILABLE HEADER FILES:",
    ]

    if skillset.header_files:
        for header, purpose in skillset.header_files.items():
            if not header.startswith('<'):
                prompt_lines.append(f"- {header}: {purpose}")

    prompt_lines.extend([
        "",
        f"CRITICAL ESP-IDF {skillset.esp_idf_version} REQUIREMENTS:",
        "- Target: ESP32-S3 chip family",
        f"- ESP-IDF Version: {skillset.esp_idf_version} (do NOT use deprecated APIs)",
        "- Use GPIO_NUM_xx macros for all GPIO references",
        "- Use esp_err_t for error handling",
        "- Use ESP_LOGx macros for logging",
        "- Include proper error checking with ESP_ERROR_CHECK() or manual checks",
        "- Use appropriate FreeRTOS task functions (xTaskCreate, vTaskDelay, etc.)",
        "- DO NOT use timer-specific registers like TIMERG0 or timer_spinlock_t (use high-level timer APIs)",
        "- DO NOT use chip-specific low-level APIs unless absolutely necessary",
        "- Use standard ESP-IDF driver APIs (gpio, i2c, spi, uart, etc.)",
        "- If the design involves LCD/display functionality, include \"esp32s3_box_lcd_config.h\" header",
        "",
        "Output ONLY the complete, compilable ESP-IDF C code with proper includes and app_main() function. No explanations or markdown formatting.",
    ])

    if wants_lcd:
        lcd_template_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'templates', 'esp_idf', 'esp32s3_lcd_template.c'
        )
        if os.path.exists(lcd_template_path):
            with open(lcd_template_path, 'r') as template_file:
                lcd_template = template_file.read().strip()
            prompt_lines.extend([
                "",
                "REFERENCE LCD TEMPLATE (adapt it to satisfy the current design; keep macro usage intact):",
                "```c",
                lcd_template,
                ", and just use default fonts.```",
            ])

    prompt = "\n".join(prompt_lines)
    
    response = await model.ainvoke(prompt)
    code = response.content.strip()
    
    # Clean up any markdown formatting
    if code.startswith('```c'):
        code = code[4:].strip()
    if code.startswith('```'):
        code = code[3:].strip()
    if code.endswith('```'):
        code = code[:-3].strip()
    
    # Extract only the C code - be more careful about what we consider non-code
    lines = code.split('\n')
    clean_lines = []
    
    for line in lines:
        # Stop if we encounter clear non-code markers (but be more specific)
        line_upper = line.upper()
        if ('**WIRING DIAGRAM**' in line_upper or 
            '**CONNECTION' in line_upper or 
            '=== WIRING' in line_upper or
            line.strip().startswith('# ') and 'wiring' in line.lower()):
            break
        
        # Keep the line if it's code or empty/comment
        clean_lines.append(line)
    
    code = '\n'.join(clean_lines).strip()
    
    # Additional cleanup - remove any trailing non-code content after the last closing brace
    if '}' in code:
        last_brace = code.rfind('}')
        # Look for the last complete function/struct ending
        potential_end = code[last_brace + 1:]
        if potential_end.strip() and not potential_end.strip().startswith('//'):
            # If there's non-comment content after the last brace, truncate there
            code = code[:last_brace + 1].strip()
    
    print("💻 Generated ESP-IDF C code")
    return {"esp_idf_code": code}


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
    
    prompt_lines = [
        f"You are an expert hardware engineer specializing in {skillset.platform_name} (ESP32-S3, ESP-IDF {skillset.esp_idf_version}) development. Generate wiring diagrams and documentation based on this design.",
        "",
        f"Design: {state.design}",
        "",
        skillset.get_specs_text(),
        "",
        skillset.get_gpio_reference(),
        "",
        "Generate comprehensive wiring instructions using the official bread breakout board layout.",
        "",
        "Official bread breakout reference:",
        "- Header: 2x12 (24 pins), 2.54mm pitch",
        "- Official pinlayout image: https://github.com/espressif/esp-box/blob/master/docs/_static/box_3_hardware_overview/pinlayout_box_3_bread.png",
        "- Use the official image above for exact pin numbering and mapping; do not invent or assume alternate arrangements.",
        "",
        "Format your response exactly as:",
        "",
        "=== WIRING DIAGRAM ===",
        "[Use the official bread breakout layout and show specific pin connections for this project]",
        "",
        "=== ADDITIONAL INFO ===",
        "[Put setup instructions, component lists, power considerations, and any important notes here]",
        "",
        "Be specific with GPIO numbers and pin names matching the FIXED layout above.",
    ]
    prompt = "\n".join(prompt_lines)
    
    response = await model.ainvoke(prompt)
    content = response.content.strip()
    
    # Parse the response into sections - more flexible to handle markdown formatting
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        # Match section headers with optional markdown formatting
        # Handles both "=== NAME ===" and "## === NAME ===" etc.
        if '=== ' in line and ' ===' in line:
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            # Extract section name from between === markers
            start = line.find('===') + 4
            end = line.rfind('===')
            section_name = line[start:end].strip().lower().replace(' ', '_')
            current_section = section_name
            current_content = []
        elif current_section is not None and line.strip():
            # Skip code fence markers and continue accumulating content
            if not line.strip().startswith('```'):
                current_content.append(line)
        elif current_section is not None and not line.strip():
            current_content.append(line)  # Preserve blank lines within sections
    
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
    """Assemble the final ESP-IDF project from generated components."""
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
    uses_lcd = bool(state.esp_idf_code and 'esp32s3_box_lcd_config.h' in state.esp_idf_code)

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

    # Write the generated ESP-IDF code as main.c
    if state.esp_idf_code:
        with open(os.path.join(main_dir, "main.c"), "w") as f:
            f.write(state.esp_idf_code)
    
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
    
    # Create sdkconfig.defaults for IDF target
    with open(os.path.join(project_dir, "sdkconfig.defaults"), "w") as f:
        f.write('CONFIG_IDF_TARGET="esp32s3"\n')
    
    print("📦 Assembled complete ESP-IDF project")
    print(f"📁 Project files saved to: {project_dir}/")
    return {
        "message": f"ESP-IDF project '{project_name}' created successfully in ./{project_name}/"
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

graph = graph.add_edge("generate_code", "assemble_project")

graph = graph.compile(name="ESP-IDF Project Creator")
