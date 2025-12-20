from src.model import HostsManager, SOURCES
import os

def test_fetch_and_parse():
    print("Initializing Manager...")
    mgr = HostsManager()
    
    print(f"Is Root: {mgr.is_root()}")
    
    print("Loading system hosts...")
    mgr.load_system_hosts()
    print(f"System entries: {len(mgr.system_entries)}")
    
    print("Loading whitelist...")
    mgr.load_whitelist()
    print(f"Whitelist entries: {len(mgr.whitelist)}")

    print("\nFetching Sources (Dry Run - fetching 1 source)...")
    # Fetch just one for speed
    name = "Malware (PiHole)"
    url = SOURCES[name]
    print(f"Fetching {name} from {url}...")
    entries = mgr.fetch_source(name, url)
    print(f"Fetched {len(entries)} entries.")
    
    mgr.remote_entries[name] = entries
    
    print("\nMerging...")
    content = mgr.merge_entries([name])
    print(f"Merged Content Length: {len(content)} chars")
    print(f"Whitelisted domains skipped: {mgr.last_whitelisted_count}")
    
    print("\nDiff Generation...")
    diff = mgr.generate_diff([name])
    print(f"Diff Length: {len(diff)} chars")
    if diff:
        print("Diff Sample (first 5 lines):")
        print("\n".join(diff.splitlines()[:5]))
    else:
        print("No diff generated (identical content).")

    print("\nPersistence (Config) Test...")
    mgr.config["selected_sources"] = [name]
    mgr.save_config("test_config.json")
    print("Saved test_config.json")
    
    mgr2 = HostsManager()
    mgr2.load_config("test_config.json")
    print(f"Loaded config: {mgr2.config}")
    if mgr2.config.get("selected_sources") == [name]:
        print("Persistence Test: SUCCESS")
    else:
        print("Persistence Test: FAILED")
    
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")

if __name__ == "__main__":
    test_fetch_and_parse()
