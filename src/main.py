#!/usr/bin/env python3
"""
Music Trainer - Main Application Entry Point

This is the main entry point for the Music Trainer application.
It initializes the GUI and starts the application loop.
"""

import sys
import logging
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logger
from utils.config import Config
from gui.main_window import MainWindow


def main():
    """Main application entry point"""
    # Setup logging
    logger = setup_logger()
    logger.info("Starting Music Trainer application")
    
    try:
        # Load configuration
        config = Config()
        logger.info(f"Loaded configuration: {config.get_summary()}")
        
        # Initialize and run the main window
        app = MainWindow(config)
        logger.info("Initialized main window")
        
        # Start the application
        app.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Music Trainer application shutting down")


if __name__ == "__main__":
    main()
