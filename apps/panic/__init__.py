import logging
import os
import signal
import sys
from typing import Dict, Any

from discord import Client


class PanicFeature:
    def __init__(self, client: Client, config: Dict[str, Any]):
        self.client = client
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.Panic")
    
    async def initialize(self):
        """Initialize the Panic feature"""
        self.logger.info("Initializing Panic feature...")
    
    async def panic(self):
        """Immediately kill the bot process"""
        self.logger.warning("🚨 PANIC ACTIVATED - Killing bot immediately!")
        
        try:
            # Force kill the entire process
            os.kill(os.getpid(), signal.SIGTERM)
        except Exception as e:
            self.logger.error(f"Failed to kill process with SIGTERM: {e}")
            try:
                # Fallback to sys.exit
                sys.exit(1)
            except Exception as e2:
                self.logger.error(f"Failed to exit with sys.exit: {e2}")
                # Last resort
                os._exit(1)