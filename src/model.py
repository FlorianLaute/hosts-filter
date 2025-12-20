import requests
import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import os
import json
import difflib

# Source URLs
SOURCES = {
    "Malware (PiHole)": "https://raw.githubusercontent.com/davidonzo/Threat-Intel/master/lists/latestdomains.piHole.txt",
    "Malware (URLHaus)": "https://urlhaus.abuse.ch/downloads/hostfile/",
    "Malware (URLHaus Filter)": "https://curben.gitlab.io/malware-filter/urlhaus-filter-hosts.txt",
    "Spam": "https://raw.githubusercontent.com/FadeMind/hosts.extras/master/add.Spam/hosts",
    "No Coin": "https://raw.githubusercontent.com/greatis/Anti-WebMiner/master/hosts",
    "Ads (StevenBlack)": "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
}

@dataclass
class HostEntry:
    ip: str
    domains: List[str]
    comment: Optional[str] = None
    source: str = "System"
    enabled: bool = True
    
    def to_line(self) -> str:
        if not self.enabled:
             return f"# {self.ip} {' '.join(self.domains)}"
        
        line = f"{self.ip:<15} {' '.join(self.domains)}"
        if self.comment:
            line += f" # {self.comment}"
        return line

class HostsManager:
    def __init__(self, system_hosts_path: str = "/etc/hosts"):
        self.system_hosts_path = system_hosts_path
        self.system_entries: List[HostEntry] = []
        self.remote_entries: Dict[str, List[HostEntry]] = {} # Keyed by source name
        self.managed_domains: Set[str] = set()
        self.whitelist: Set[str] = set()
        self.config: Dict = {"selected_sources": []}

    def load_config(self, path: str = "config.json"):
        """Loads configuration from a JSON file."""
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.config = json.load(f)
            except Exception:
                pass

    def save_config(self, path: str = "config.json"):
        """Saves current configuration to a JSON file."""
        try:
            with open(path, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception:
            pass

    @staticmethod
    def is_root() -> bool:
        """Checks if the script is running with root privileges."""
        try:
            return os.geteuid() == 0
        except AttributeError:
            # os.geteuid() not available on Windows, but this tool is for Linux
            return True

    def parse_content(self, content: str, source_name: str) -> List[HostEntry]:
        """Parses hosts file content into HostEntry objects."""
        entries = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Remove inline comments
            parts = line.split("#", 1)
            comment = parts[1].strip() if len(parts) > 1 else None
            clean_line = parts[0].strip()
            
            if not clean_line:
                continue

            tokens = clean_line.split()
            if len(tokens) < 2:
                continue
                
            ip = tokens[0]
            domains = tokens[1:]
            
            entries.append(HostEntry(ip=ip, domains=domains, comment=comment, source=source_name))
            
        return entries

    def load_system_hosts(self):
        """Loads and parses the system /etc/hosts file."""
        try:
            with open(self.system_hosts_path, "r") as f:
                content = f.read()

            self.system_entries = self.parse_content(content, "System")
        except FileNotFoundError:
            self.system_entries = []

    def load_whitelist(self, path: str = "whitelist.txt"):
        """Loads a list of domains to never block."""
        if not os.path.exists(path):
            self.whitelist = set()
            return
            
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.whitelist.add(line)

    def fetch_source(self, name: str, url: str) -> List[HostEntry]:
        """Fetches and parses a remote hosts file."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            return self.parse_content(response.text, name)
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            return []

    def fetch_all_sources(self):
        """Fetches all configured remote sources."""
        self.remote_entries = {}
        for name, url in SOURCES.items():
            entries = self.fetch_source(name, url)
            self.remote_entries[name] = entries

    def merge_entries(self, selected_sources: List[str]) -> str:
        """Merges system entries with selected remote sources and generates file content."""
        lines = []
        
        lines.append("### SYSTEM ENTRIES (PRESERVED) ###")
        for entry in self.system_entries:
            lines.append(entry.to_line())
        lines.append("")

        lines.append("### BLOCKLIST ENTRIES (GENERATED) ###")
        
        timestamp = "# Generated by HostsFilter"
        lines.append(timestamp)
        
        self.last_whitelisted_count = 0
        seen_domains = set()
        for entry in self.system_entries:
            for d in entry.domains:
                seen_domains.add(d)
        
        for source in selected_sources:
            if source not in self.remote_entries:
                continue
                
            lines.append(f"# Source: {source}")
            for entry in self.remote_entries[source]:
                new_domains = []
                for d in entry.domains:
                    if d in seen_domains:
                        continue
                    if d in self.whitelist:
                        self.last_whitelisted_count += 1
                        continue
                    new_domains.append(d)

                if new_domains:
                    block_entry = HostEntry(ip="0.0.0.0", domains=new_domains, source=source)
                    lines.append(block_entry.to_line())
                    seen_domains.update(new_domains)
            lines.append("")
            
        return "\n".join(lines)

    def preview_stats(self, selected_sources: List[str]) -> Dict:
        """Returns stats about what would happen if we merged."""
        total_system = len(self.system_entries)
        total_blocked = 0
        whitelisted_count = 0
        
        # We need to simulate the merge to get accurate stats
        seen_domains = set()
        for entry in self.system_entries:
            for d in entry.domains:
                seen_domains.add(d)
        
        for source in selected_sources:
             if source in self.remote_entries:
                 for entry in self.remote_entries[source]:
                     for d in entry.domains:
                         if d in seen_domains:
                             continue
                         if d in self.whitelist:
                             whitelisted_count += 1
                             continue
                         total_blocked += 1
                         seen_domains.add(d)
                      
        return {
            "system_lines": total_system,
            "new_blocked_domains": total_blocked,
            "whitelisted_skipped": whitelisted_count
        }

    def generate_diff(self, selected_sources: List[str]) -> str:
        """Generates a diff between current /etc/hosts and the new proposed content."""
        try:
            with open(self.system_hosts_path, "r") as f:
                current_content = f.read()
        except FileNotFoundError:
            current_content = ""

        new_content = self.merge_entries(selected_sources)
        
        diff = difflib.unified_diff(
            current_content.splitlines(),
            new_content.splitlines(),
            fromfile="/etc/hosts (current)",
            tofile="/etc/hosts (new)",
            lineterm=""
        )
        return "\n".join(diff)
