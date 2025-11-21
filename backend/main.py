import uvicorn
import subprocess
import sys
import signal
import time
import argparse
import os

def start_celery_worker(logging_mode="none"):
    """Start Celery worker as a subprocess"""
    print("Starting Celery worker...")
    
    # Use absolute imports for Celery app
    # Using --pool=solo to avoid issues with the PDF processing library
    # IMPORTANT: Must use app.core.celery_app (not app.tasks.document_tasks) to get Redis configuration
    celery_cmd = ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info", "--pool=solo"]
    
    # Determine where to send output based on logging mode
    celery_log_file = None
    if logging_mode in ["all", "tasks"]:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        # Open log file for Celery worker output
        celery_log_file = open("logs/tasks.log", "a", buffering=1)  # Line buffered
        stdout_dest = celery_log_file
        stderr_dest = celery_log_file
        print("Celery worker logs will be saved to logs/tasks.log")
    else:
        # When not logging, we still need to consume the output to prevent blocking
        # Open /dev/null (or NUL on Windows) for writing
        devnull = open(os.devnull, 'w')
        stdout_dest = devnull
        stderr_dest = devnull
        celery_log_file = devnull  # Store it so we can close it later
    
    # Start the worker process
    worker_process = subprocess.Popen(
        celery_cmd,
        stdout=stdout_dest,
        stderr=stderr_dest,
        bufsize=1  # Line buffered
    )
    
    # Give it a moment to start and check if it's running
    time.sleep(2)
    if worker_process.poll() is None:
        print("Celery worker started successfully")
        return worker_process, celery_log_file
    else:
        print("Failed to start Celery worker")
        if celery_log_file:
            celery_log_file.close()
        return None, None

def main():
    """Run the FastAPI application with uvicorn and start Celery worker"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the RFP Analysis API server")
    parser.add_argument(
        "--logging",
        type=str,
        choices=["none", "all", "errors", "workflows", "tasks"],
        default="none",
        help="Logging mode: none (console only), all (all logs to files), errors (only errors), workflows (only workflow logs), tasks (only task logs)"
    )
    args = parser.parse_args()
    
    # Set logging mode in environment variable so it's picked up by settings
    os.environ["LOGGING_MODE"] = args.logging
    
    # Import app after setting environment variable
    from app.main import app
    
    print(f"Starting with logging mode: {args.logging}")
    
    # Start Celery worker
    worker_process, celery_log_file = start_celery_worker(args.logging)
    
    # Define signal handler to terminate both processes on exit
    def signal_handler(sig, frame):
        print("Shutting down...")
        if worker_process:
            print("Terminating Celery worker...")
            worker_process.terminate()
        if celery_log_file:
            celery_log_file.close()
        sys.exit(0)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start FastAPI application
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
