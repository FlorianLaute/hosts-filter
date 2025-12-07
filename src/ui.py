from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Checkbox, Static, RichLog, Label
from textual.screen import Screen
from textual import work
import sys
import os

from src.model import HostsManager, SOURCES

class HostsFilterApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    
    .box {
        height: auto;
        border: solid green;
        margin: 1;
        padding: 1;
    }

    #sources_list {
        height: auto;
        max-height: 50%;
        overflow-y: auto;
    }

    .stats {
         width: 100%;
         height: auto;
         content-align: center middle;
         background: $boost;
         margin: 1;
    }
    
    Button {
        margin: 1;
        width: 100%;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("f", "fetch", "Fetch"),
        ("p", "preview", "Preview"),
        ("a", "apply", "Apply"),
    ]

    def __init__(self):
        super().__init__()
        self.manager = HostsManager()
        self.manager.load_system_hosts()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical():
            yield Static(f"System Hosts Entries: {len(self.manager.system_entries)}", id="system_stats", classes="stats")
            
            yield Label("Select Sources to Fetch & Merge:")
            with ScrollableContainer(id="sources_list", classes="box"):
                for name in SOURCES.keys():
                    safe_id = f"cb_{name.replace(' ', '_').replace('(', '').replace(')', '').lower()}"
                    yield Checkbox(name, id=safe_id)

            yield Static("Welcome! 1. Click 'Fetch & Analyze' to download lists. 2. Select lists below. 3. Click 'Apply' to save to /etc/hosts.", classes="box")
            
            with Horizontal(classes="box"):
                yield Button("Fetch & Analyze", id="btn_fetch", variant="primary")
                yield Button("Preview Merge", id="btn_preview", variant="warning")
                yield Button("Apply to /etc/hosts", id="btn_apply", variant="error")

            yield RichLog(id="log_window", highlight=True)

    def on_mount(self):
        self.query_one("#log_window").write(f"Loaded {len(self.manager.system_entries)} entries from {self.manager.system_hosts_path}")

    @work(exclusive=True, thread=True)
    def action_fetch(self):
        log = self.query_one("#log_window")
        log.write("Starting fetch...")
        
        self.manager.fetch_all_sources()
        
        for name, entries in self.manager.remote_entries.items():
            log.write(f"Fetched {name}: {len(entries)} entries.")
            
        log.write("Fetch complete.")

    def action_preview(self):
        self.show_preview()

    def action_apply(self):
        self.apply_changes()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_fetch":
            self.action_fetch()
        
        elif event.button.id == "btn_preview":
            self.action_preview()

        elif event.button.id == "btn_apply":
            self.action_apply()

    def get_selected_sources(self):
        selected = []
        for name in SOURCES.keys():
            try:
                safe_id = f"cb_{name.replace(' ', '_').replace('(', '').replace(')', '').lower()}"
                cb = self.query_one(f"#{safe_id}", Checkbox)
                if cb.value:
                    selected.append(name)
            except:
                pass
        return selected

    def show_preview(self):
        log = self.query_one("#log_window")
        selected = self.get_selected_sources()
        if not selected:
            log.write("No sources selected!")
            return

        stats = self.manager.preview_stats(selected)
        log.write(f"Preview Stats for {selected}:")
        log.write(f"  System Lines (Preserved): {stats['system_lines']}")
        log.write(f"  New Blocked Domains: {stats['new_blocked_domains']}")
        
    def apply_changes(self):
        log = self.query_one("#log_window")
        selected = self.get_selected_sources()
        
        if not selected:
            log.write("WARNING: No blocklists selected. This will revert /etc/hosts to system entries only.")
        
        missing_data = [s for s in selected if s not in self.manager.remote_entries]
        if missing_data:
            log.write(f"ERROR: No data for {missing_data}. Please click 'Fetch & Analyze' first!")
            return

        log.write(f"Applying changes... Merging {len(selected)} sources.")
        new_content = self.manager.merge_entries(selected)
        
        try:
            log.write(f"Backing up to {self.manager.system_hosts_path}.bak...")
            
            with open(f"{self.manager.system_hosts_path}.bak", "w") as f:
                 with open(self.manager.system_hosts_path, "r") as orig:
                     f.write(orig.read())
            
            with open(self.manager.system_hosts_path, "w") as f:
                f.write(new_content)
                
            log.write("Successfully wrote to /etc/hosts!")
            
        except PermissionError:
            log.write("ERROR: Permission denied! You must run this script with sudo.")
            log.write("Run: sudo python main.py")
        except Exception as e:
            log.write(f"ERROR: {e}")

if __name__ == "__main__":
    app = HostsFilterApp()
    app.run()
