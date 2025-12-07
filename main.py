import sys
from src.ui import HostsFilterApp
import os

if __name__ == "__main__":
    # Check if we are running locally or in a way that we can warn about functionality
    # if os.geteuid() != 0:
    #     print("Warning: not running as root. You will not be able to save changes to /etc/hosts.")
    #     # We do not block start, as the user might just want to test fetching.
    
    app = HostsFilterApp()
    app.run()
