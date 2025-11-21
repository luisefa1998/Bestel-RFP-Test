"""
Logging configuration for the application.
Sets up file and console logging with detailed formatting.

Logging modes:
- "none": Console only (default for production)
- "all": All logs to files (app.log, errors.log, workflow.log)
- "errors": Only errors to file (errors.log)
- "workflows": Only workflow logs to file (workflow.log)
"""
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(mode: str = "none"):
    """
    Configure logging for the application
    
    Args:
        mode: Logging mode - "none", "all", "errors", "workflows", or "tasks"
    """
    
    # Validate mode
    valid_modes = ["none", "all", "errors", "workflows", "tasks"]
    if mode not in valid_modes:
        raise ValueError(f"Invalid logging mode: {mode}. Must be one of {valid_modes}")
    
    # Create logs directory if it doesn't exist (only if file logging is enabled)
    log_dir = Path("logs") if mode != "none" else None
    if log_dir:
        log_dir.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Add file handlers based on mode
    if mode == "all" and log_dir:
        # File handler for all logs (DEBUG level)
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    
    if mode in ["all", "errors"] and log_dir:
        # File handler for errors only
        error_handler = RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
    
    if mode in ["all", "workflows"] and log_dir:
        # File handler for workflow logs ONLY (not all app logs)
        workflow_handler = RotatingFileHandler(
            log_dir / "workflow.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        workflow_handler.setLevel(logging.DEBUG)
        workflow_handler.setFormatter(detailed_formatter)
        
        # Add workflow handler ONLY to workflow logger, not root logger
        workflow_logger = logging.getLogger('app.workflows')
        # Clear any existing handlers first
        workflow_logger.handlers = []
        workflow_logger.addHandler(workflow_handler)
        workflow_logger.setLevel(logging.DEBUG)
        workflow_logger.propagate = True  # Propagate to root for console output
    
    if mode in ["all", "tasks"] and log_dir:
        # File handler for task logs (Celery tasks)
        task_handler = RotatingFileHandler(
            log_dir / "tasks.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        task_handler.setLevel(logging.DEBUG)
        task_handler.setFormatter(detailed_formatter)
        
        # Add task handler to both root logger and task-specific loggers
        root_logger.addHandler(task_handler)
        
        # Also configure task-specific loggers
        task_logger = logging.getLogger('app.tasks')
        task_logger.setLevel(logging.DEBUG)
        task_logger.propagate = True  # Propagate to root for console output
        
        # Configure Celery logger to also use the task handler
        celery_logger = logging.getLogger('celery')
        celery_logger.setLevel(logging.INFO)
        celery_logger.propagate = True
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific loggers to appropriate levels
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('celery').setLevel(logging.INFO)
    
    # Reduce verbosity of HTTP libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('ibm_watsonx_ai').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logging.info(f"Logging configured successfully (mode: {mode})")
    if log_dir:
        logging.info(f"Log files location: {log_dir.absolute()}")
    else:
        logging.info("Console-only logging (no log files)")

# Made with Bob
