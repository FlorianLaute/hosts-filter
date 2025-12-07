from src.model import HostsManager, SOURCES
import os

def test_fetch_and_parse():
    print("Initializing Manager...")
    mgr = HostsManager()
    
    print("Loading system hosts...")
    mgr.load_system_hosts()
    print(f"System entries: {len(mgr.system_entries)}")
    for e in mgr.system_entries[:3]:
        print(f"  - {e.to_line()}")

    print("\nFetching Sources (Dry Run - fetching 1 source)...")
    # Fetch just one for speed
    name = "Malware (PiHole)"
    url = SOURCES[name]
    print(f"Fetching {name} from {url}...")
    entries = mgr.fetch_source(name, url)
    print(f"Fetched {len(entries)} entries.")
    if entries:
        print(f"Sample: {entries[0].to_line()}")
    
    mgr.remote_entries[name] = entries
    
    print("\nMerging...")
    content = mgr.merge_entries([name])
    print(f"Merged Content Length: {len(content)} chars")
    print("First 10 lines of merged content:")
    print("\n".join(content.splitlines()[:10]))

if __name__ == "__main__":
    test_fetch_and_parse()
