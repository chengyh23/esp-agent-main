import re
import os
from pathlib import Path

def extract_fonts_from_code(project_root):
    """Scan source files for LVGL font usage."""
    font_pattern = re.compile(r'lv_font_montserrat_(\d+)')
    fonts_used = set()
    
    # Search in common source directories
    source_dirs = ['main', 'src', 'components']
    for src_dir in source_dirs:
        dir_path = Path(project_root) / src_dir
        if dir_path.exists():
            for file_path in dir_path.rglob('*.c'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    matches = font_pattern.findall(content)
                    fonts_used.update(matches)
    
    return sorted(fonts_used, key=int)

def update_sdkconfig(sdkconfig_path, fonts_used):
    """Update sdkconfig with required font configurations."""
    # All available montserrat fonts
    all_sizes = [20, 22, 24, 26, 28, 30, 32, 34, 36]
    
    # Read existing config
    config_lines = []
    if os.path.exists(sdkconfig_path):
        with open(sdkconfig_path, 'r') as f:
            config_lines = f.readlines()
    
    # Build new config section for fonts
    new_font_config = []
    for size in all_sizes:
        if str(size) in fonts_used:
            new_font_config.append(f"CONFIG_LV_FONT_MONTSERRAT_{size}=y\n")
        else:
            new_font_config.append(f"# CONFIG_LV_FONT_MONTSERRAT_{size} is not set\n")
    
    # Remove old font config lines
    filtered_lines = [line for line in config_lines 
                      if 'CONFIG_LV_FONT_MONTSERRAT_' not in line]
    
    # Add new font config
    filtered_lines.extend(new_font_config)
    
    # Write back
    with open(sdkconfig_path, 'w') as f:
        f.writelines(filtered_lines)
    
    print(f"Updated sdkconfig with fonts: {', '.join(fonts_used)}")

if __name__ == '__main__':
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sdkconfig_path = os.path.join(project_root, 'sdkconfig')
    
    fonts_used = extract_fonts_from_code(project_root)
    if fonts_used:
        update_sdkconfig(sdkconfig_path, fonts_used)
    else:
        print("No LVGL fonts found in code")
