import os
import re
import json
from pathlib import Path
from typing import Optional, List, Dict

from src.agent_arduino.state import ArduinoState
from src.agent_arduino.skills.lvgl_font_config_skill import ArduinoLVGLFontConfigSkill


class ArduinoAgent:
    """Agent for managing Arduino/ESP32 projects."""
    
    def __init__(self, project_root: str, llm=None):
        self.project_root = project_root
        self.llm = llm
        self.state = ArduinoState()
        
        # Initialize state from existing project
        self._load_project_state()
    
    def _load_project_state(self):
        """Load project state from existing files."""
        # Find main sketch file
        sketch_candidates = [
            os.path.join(self.project_root, "arduino_project", "arduino_project.ino"),
            os.path.join(self.project_root, "sketch", "sketch.ino"),
            os.path.join(self.project_root, "main.ino")
        ]
        
        for sketch_path in sketch_candidates:
            if os.path.exists(sketch_path):
                self.state.sketch_path = sketch_path
                with open(sketch_path, 'r') as f:
                    self.state.sketch_content = f.read()
                break
        
        # Load libraries from sketch
        if self.state.sketch_content:
            self._extract_libraries()
    
    def _extract_libraries(self):
        """Extract library dependencies from sketch."""
        include_pattern = re.compile(r'#include\s*[<"]([^>"]+)[>"]')
        matches = include_pattern.findall(self.state.sketch_content)
        
        # Filter to library includes (not system headers)
        library_includes = [m for m in matches if not m.endswith('.h') or '/' in m]
        self.state.libraries = list(set(library_includes))
    
    def reconcile_libraries(self, code_path: Optional[str] = None) -> dict:
        """
        Analyze Arduino sketch and ensure required libraries are configured.
        Similar to reconcile_sdk_config for ESP-IDF.
        """
        if code_path is None:
            code_path = self.state.sketch_path
        
        if not code_path or not os.path.exists(code_path):
            return {
                'success': False,
                'error': 'Sketch file not found',
                'libraries': []
            }
        
        # Read sketch
        with open(code_path, 'r') as f:
            sketch_content = f.read()
        
        # Extract library requirements
        include_pattern = re.compile(r'#include\s*[<"]([^>"]+)[>"]')
        includes = include_pattern.findall(sketch_content)
        
        # Map includes to Arduino library names
        library_mapping = {
            'WiFi.h': 'WiFi',
            'Wire.h': 'Wire',
            'SPI.h': 'SPI',
            'lvgl.h': 'lvgl',
            'TFT_eSPI.h': 'TFT_eSPI',
            'Adafruit_GFX.h': 'Adafruit GFX Library',
            'Adafruit_ILI9341.h': 'Adafruit ILI9341',
        }
        
        required_libraries = []
        for include in includes:
            lib_name = library_mapping.get(include)
            if lib_name:
                required_libraries.append(lib_name)
        
        self.state.libraries = list(set(required_libraries))
        
        # Check for LVGL fonts if using LVGL
        if 'lvgl' in required_libraries:
            skill = ArduinoLVGLFontConfigSkill(self.project_root)
            fonts_result = skill.execute()
            self.state.lvgl_fonts = fonts_result.get('fonts_detected', [])
        
        return {
            'success': True,
            'libraries': self.state.libraries,
            'lvgl_fonts': self.state.lvgl_fonts
        }
    
    def generate_platformio_ini(self) -> str:
        """Generate platformio.ini configuration file."""
        config_lines = [
            "[env:esp32s3]",
            "platform = espressif32",
            "board = esp32-s3-devkitc-1",
            "framework = arduino",
            ""
        ]
        
        # Add libraries
        if self.state.libraries:
            config_lines.append("lib_deps = ")
            for lib in self.state.libraries:
                config_lines.append(f"    {lib}")
            config_lines.append("")
        
        # Add build flags
        if self.state.build_flags or self.state.compile_definitions:
            config_lines.append("build_flags = ")
            for flag in self.state.build_flags:
                config_lines.append(f"    {flag}")
            for define in self.state.compile_definitions:
                config_lines.append(f"    -D{define}")
            config_lines.append("")
        
        # Add LVGL font flags
        if self.state.lvgl_fonts:
            config_lines.append("    ; LVGL Fonts")
            for font in self.state.lvgl_fonts:
                config_lines.append(f"    -DLV_FONT_MONTSERRAT_{font}=1")
            config_lines.append("")
        
        # Partition scheme for ESP32
        if self.state.partition_scheme:
            config_lines.append(f"board_build.partitions = {self.state.partition_scheme}.csv")
            config_lines.append(f"board_build.flash_size = {self.state.flash_size}")
        
        return '\n'.join(config_lines)
    
    def generate_lv_conf_h(self) -> str:
        """Generate lv_conf.h for LVGL configuration."""
        config_lines = [
            "// LVGL Configuration for Arduino",
            "#ifndef LV_CONF_H",
            "#define LV_CONF_H",
            "",
            "#define LV_COLOR_DEPTH 16",
            "#define LV_COLOR_16_SWAP 1",
            "",
            "// Memory settings",
            "#define LV_MEM_CUSTOM 0",
            "#define LV_MEM_SIZE (48U * 1024U)",
            "",
            "// Font configuration"
        ]
        
        # Add font configurations
        font_sizes = [20, 22, 24, 26, 28, 30, 32, 34, 36]
        for size in font_sizes:
            if str(size) in self.state.lvgl_fonts:
                config_lines.append(f"#define LV_FONT_MONTSERRAT_{size} 1")
            else:
                config_lines.append(f"#define LV_FONT_MONTSERRAT_{size} 0")
        
        config_lines.extend([
            "",
            "#endif // LV_CONF_H"
        ])
        
        return '\n'.join(config_lines)
    
    def save_configuration(self):
        """Save configuration files to project."""
        # Save platformio.ini
        platformio_path = os.path.join(self.project_root, "platformio.ini")
        with open(platformio_path, 'w') as f:
            f.write(self.generate_platformio_ini())
        
        # Save lv_conf.h if LVGL is used
        if 'lvgl' in self.state.libraries:
            lvconf_path = os.path.join(self.project_root, "include", "lv_conf.h")
            os.makedirs(os.path.dirname(lvconf_path), exist_ok=True)
            with open(lvconf_path, 'w') as f:
                f.write(self.generate_lv_conf_h())
        
        return {
            'success': True,
            'files_generated': ['platformio.ini', 'lv_conf.h']
        }
