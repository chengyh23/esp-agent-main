from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ArduinoState:
    """State management for Arduino agent."""
    
    # Project configuration
    sketch_path: str = ""
    board_config: str = ""  # e.g., "esp32:esp32:esp32s3"
    libraries: List[str] = field(default_factory=list)
    
    # Code content
    sketch_content: str = ""
    header_files: Dict[str, str] = field(default_factory=dict)
    
    # Library configuration
    library_versions: Dict[str, str] = field(default_factory=dict)
    library_changes: List[Dict] = field(default_factory=list)
    
    # Build configuration
    build_flags: List[str] = field(default_factory=list)
    compile_definitions: List[str] = field(default_factory=list)
    
    # LVGL specific (for ESP32 with TFT)
    lvgl_fonts: List[str] = field(default_factory=list)
    lvgl_config: str = ""
    
    # Partition scheme (for ESP32)
    partition_scheme: str = "default"
    flash_size: str = "4MB"
    
    def to_dict(self) -> dict:
        """Convert state to dictionary."""
        return {
            'sketch_path': self.sketch_path,
            'board_config': self.board_config,
            'libraries': self.libraries,
            'library_versions': self.library_versions,
            'build_flags': self.build_flags,
            'compile_definitions': self.compile_definitions,
            'lvgl_fonts': self.lvgl_fonts,
            'partition_scheme': self.partition_scheme,
            'flash_size': self.flash_size
        }
