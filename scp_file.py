import os
import subprocess

# === Configuration ===
REMOTE_USER = "root"
REMOTE_IP = "195.2.60.228"
# REMOTE_PATH = "/home/cloudcraftz/live_monitoring/live_monitoring_alert_system/alerts.json"
LOCAL_DIR = "/home/cloudcraftz/Music/OneDrive_2_22-04-2025/"  # Current directory
PASSWORD = "Shivam$479"

def fetch_file():
    """Fetch the remote alerts.json file using sshpass and SCP."""
    try:
        print("📡 Fetching file from remote server...")
        cmd = [
            "sshpass", "-p", PASSWORD,
            "scp", f"{REMOTE_USER}@{REMOTE_IP}:{REMOTE_PATH}", LOCAL_DIR
        ]
        subprocess.run(cmd, check=True)
        print("✅ File fetched successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to fetch file. Error: {e}")
        exit(1)

# === Entry Point ===
if __name__ == "__main__":
    REMOTE_PATH = "/mcastdata2/ajay_temp/Outputs/BIOCON.tar"
    fetch_file()
