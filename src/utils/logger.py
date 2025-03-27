import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(level="INFO", log_file=None):
    """
    Set up logging configuration.
    
    Args:
        level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file (str, optional): Path to log file. If None, logs to stdout only.
    """
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory if log_file is specified but not provided
    if log_file is None:
        log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"meebo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
    
    # Add a filter to avoid duplicated logs if multiple handlers are present
    if len(handlers) > 1:
        for handler in handlers:
            handler.addFilter(lambda record: not hasattr(record, 'handled'))
            
    logging.info(f"Logging initialized at level {level}")
    logging.info(f"Log file: {log_file}")
    
    return logging.getLogger()

class SimulatedLogger:
    """Special logger for simulated components."""
    
    def __init__(self, component_name):
        """Initialize simulated logger."""
        self.logger = logging.getLogger(f"sim.{component_name}")
        
    def debug(self, message, *args, **kwargs):
        """Log debug message with [SIM] prefix."""
        self.logger.debug(f"[SIM] {message}", *args, **kwargs)
        
    def info(self, message, *args, **kwargs):
        """Log info message with [SIM] prefix."""
        self.logger.info(f"[SIM] {message}", *args, **kwargs)
        
    def warning(self, message, *args, **kwargs):
        """Log warning message with [SIM] prefix."""
        self.logger.warning(f"[SIM] {message}", *args, **kwargs)
        
    def error(self, message, *args, **kwargs):
        """Log error message with [SIM] prefix."""
        self.logger.error(f"[SIM] {message}", *args, **kwargs)
        
    def critical(self, message, *args, **kwargs):
        """Log critical message with [SIM] prefix."""
        self.logger.critical(f"[SIM] {message}", *args, **kwargs) 