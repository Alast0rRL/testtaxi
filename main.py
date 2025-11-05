
import subprocess
import sys

def main():
    """Runs both the client and driver bots in parallel."""
    try:
        print("Starting client bot...")
        client_bot_process = subprocess.Popen([sys.executable, "bot.py"])
        
        print("Starting driver bot...")
        driver_bot_process = subprocess.Popen([sys.executable, "driver_bot.py"])
        
        print("Both bots are running. Press Ctrl+C to stop.")
        
        # Wait for the processes to complete
        client_bot_process.wait()
        driver_bot_process.wait()
        
    except KeyboardInterrupt:
        print("\nStopping both bots...")
        client_bot_process.terminate()
        driver_bot_process.terminate()
        print("Bots stopped.")

if __name__ == "__main__":
    main()

