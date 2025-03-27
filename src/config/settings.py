import os
from pathlib import Path
from typing import Dict, Any

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Look for .env file in the project root directory
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        print(f"Loaded environment variables from {env_path}")
except ImportError:
    print("python-dotenv not installed. Environment variables may not be loaded from .env file.")
    # Continue without dotenv - will use os.environ or defaults

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = BASE_DIR / "src"

# Debug environment variables (uncomment to help with debugging)
# print(f"LLM_HOST: {os.getenv('LLM_HOST')}")
# print(f"LLM_PORT: {os.getenv('LLM_PORT')}")
# print(f"LLM_MODEL: {os.getenv('LLM_MODEL')}")

# LLM server settings
LLM_SERVER = {
    "host": os.getenv("LLM_HOST", "localhost"),
    "port": int(os.getenv("LLM_PORT", "11434")),
    "model": os.getenv("LLM_MODEL", "qwen2:7b"),
    "api_key": os.getenv("LLM_API_KEY", ""),  # If needed
}

# Audio settings
AUDIO = {
    "sample_rate": 16000,
    "channels": 1,
    "input_device": None,  # Auto-select
    "output_device": None,  # Auto-select
}

# Camera settings
CAMERA = {
    "resolution": (640, 480),
    "framerate": 30,
    "rotation": 0,
}

# Motor/servo configuration
MOTORS = {
    "left_motor": {
        "pwm_channel": 0,
        "in1_pin": 5,
        "in2_pin": 6,
    },
    "right_motor": {
        "pwm_channel": 1,
        "in1_pin": 13,
        "in2_pin": 19,
    },
}

# Sensor pins (placeholder values)
SENSORS = {
    "ir_sensors": [17, 27, 22, 23],
    "ultrasonic": {
        "trig_pin": 24,
        "echo_pin": 25,
    },
}

# Environment detection
IS_RASPBERRY_PI = False
try:
    with open('/proc/device-tree/model', 'r') as f:
        if 'Raspberry Pi' in f.read():
            IS_RASPBERRY_PI = True
except:
    pass

# Development mode (enables simulation)
DEV_MODE = not IS_RASPBERRY_PI or os.getenv("MEEBO_DEV_MODE", "false").lower() == "true" 