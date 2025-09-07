from setuptools import setup, find_packages

setup(
    name="music_trainer",
    version="0.1.0",
    description="AI-powered music practice bot with call-and-response training",
    author="Music Trainer Team",
    author_email="contact@musictrainer.dev",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "python-rtmidi>=1.4.9",
        "sounddevice>=0.4.6",
        "numpy>=1.24.3",
        "music21>=8.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "music-trainer=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Education",
    ],
)
