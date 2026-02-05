import re
import os
from pathlib import Path
from typing import Set, List

class ArduinoLVGLFontConfigSkill:
    """Skill to detect LVGL font usage in Arduino sketches and configure accordingly."""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.font_sizes = [20, 22, 24, 26, 28, 30, 32, 34, 36]
        self.font_pattern = re.compile(r'lv_font_montserrat_(\d+)')
    
    def extract_fonts_from_code(self) -> Set[str]:
        """Scan Arduino sketch files for LVGL font usage."""
        fonts_used = set()
        
        # Search in Arduino project directories
        source_dirs = ['arduino_project', 'sketch', 'src']
        
        for src_dir in source_dirs:
            dir_path = Path(self.project_root) / src_dir
            if dir_path.exists():
                # Scan .ino and .cpp files
                for ext in ['*.ino', '*.cpp', '*.h']:
                    for file_path in dir_path.rglob(ext):
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                matches = self.font_pattern.findall(content)
                                fonts_used.update(matches)
                        except Exception as e:
                            print(f"Error reading {file_path}: {e}")
        
        return fonts_used
    
    def generate_build_flags(self, fonts_used: Set[str]) -> List[str]:
        """Generate build flags for Arduino/PlatformIO."""
        flags = []
        
        for size in self.font_sizes:
            if str(size) in fonts_used:
                flags.append(f"-DLV_FONT_MONTSERRAT_{size}=1")
            else:
                flags.append(f"-DLV_FONT_MONTSERRAT_{size}=0")
        
        return flags
    
    def generate_lv_conf_defines(self, fonts_used: Set[str]) -> List[str]:
        """Generate lv_conf.h defines."""
        defines = []
        
        for size in self.font_sizes:
            if str(size) in fonts_used:
                defines.append(f"#define LV_FONT_MONTSERRAT_{size} 1")
            else:
                defines.append(f"#define LV_FONT_MONTSERRAT_{size} 0")
        
        return defines
    
    def update_platformio_ini(self, fonts_used: Set[str]) -> bool:
        """Update platformio.ini with font build flags."""
        platformio_path = os.path.join(self.project_root, "platformio.ini")
        
        if not os.path.exists(platformio_path):
            print("platformio.ini not found")
            return False
        
        # Read existing config
        with open(platformio_path, 'r') as f:
            lines = f.readlines()
        
        # Generate font flags
        font_flags = self.generate_build_flags(fonts_used)
        
        # Remove old LVGL font flags
        filtered_lines = [line for line in lines 
                          if 'LV_FONT_MONTSERRAT_' not in line]
        
        # Find build_flags section or create it
        build_flags_idx = -1
        for i, line in enumerate(filtered_lines):
            if line.strip().startswith('build_flags'):
                build_flags_idx = i
                break
        
        if build_flags_idx >= 0:
            # Insert after build_flags line
            insert_idx = build_flags_idx + 1
            # Add font flags with proper indentation
            for flag in font_flags:
                filtered_lines.insert(insert_idx, f"    {flag}\n")
                insert_idx += 1
        else:
            # Add build_flags section
            filtered_lines.append("\nbuild_flags = \n")
            for flag in font_flags:
                filtered_lines.append(f"    {flag}\n")
        
        # Write back
        with open(platformio_path, 'w') as f:
            f.writelines(filtered_lines)
        
        return True
    
    def update_lv_conf_h(self, fonts_used: Set[str]) -> bool:
        """Update lv_conf.h with font configuration."""
        lv_conf_paths = [
            os.path.join(self.project_root, "include", "lv_conf.h"),
            os.path.join(self.project_root, "lv_conf.h"),
            os.path.join(self.project_root, "arduino_project", "lv_conf.h")
        ]
        
        lv_conf_path = None
        for path in lv_conf_paths:
            if os.path.exists(path):
                lv_conf_path = path
                break
        
        if not lv_conf_path:
            # Create new lv_conf.h
            lv_conf_path = os.path.join(self.project_root, "include", "lv_conf.h")
            os.makedirs(os.path.dirname(lv_conf_path), exist_ok=True)
            
            with open(lv_conf_path, 'w') as f:
                f.write("#ifndef LV_CONF_H\n")
                f.write("#define LV_CONF_H\n\n")
                f.write("// LVGL Font Configuration\n")
                for define in self.generate_lv_conf_defines(fonts_used):
                    f.write(f"{define}\n")
                f.write("\n#endif // LV_CONF_H\n")
            return True
        
        # Update existing lv_conf.h
        with open(lv_conf_path, 'r') as f:
            content = f.read()
        
        # Remove old font defines
        lines = content.split('\n')
        filtered_lines = [line for line in lines 
                          if 'LV_FONT_MONTSERRAT_' not in line]
        
        # Add new font defines
        font_defines = self.generate_lv_conf_defines(fonts_used)
        
        # Insert before #endif
        endif_idx = -1
        for i, line in enumerate(filtered_lines):
            if '#endif' in line:
                endif_idx = i
                break
        
        if endif_idx >= 0:
            filtered_lines.insert(endif_idx, "\n// LVGL Font Configuration")
            for define in font_defines:
                filtered_lines.insert(endif_idx + 1, define)
        
        # Write back
        with open(lv_conf_path, 'w') as f:
            f.write('\n'.join(filtered_lines))
        
        return True
    
    def execute(self) -> dict:
        """Execute the skill to configure LVGL fonts for Arduino."""
        fonts_used = self.extract_fonts_from_code()
        
        if not fonts_used:
            return {
                'success': False,
                'message': 'No LVGL fonts found in code',
                'fonts_detected': []
            }
        
        # Update configurations
        platformio_updated = self.update_platformio_ini(fonts_used)
        lvconf_updated = self.update_lv_conf_h(fonts_used)
        
        return {
            'success': platformio_updated or lvconf_updated,
            'message': f'Configured {len(fonts_used)} font(s)',
            'fonts_detected': sorted(fonts_used, key=int),
            'platformio_updated': platformio_updated,
            'lvconf_updated': lvconf_updated
        }
