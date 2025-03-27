from setuptools import setup, find_packages

setup(
    name="meebo",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "numpy",
        "pydantic",
        "openai",
        "sounddevice",
        "soundfile",
        "pydub",
        "SpeechRecognition",
        "opencv-python",
        "pillow",
    ],
    author="Devon",
    description="Meebo: An LLM-powered robot using Qwen2.5:7b",
    keywords="robot, llm, ai, raspberry-pi",
    python_requires=">=3.9",
) 