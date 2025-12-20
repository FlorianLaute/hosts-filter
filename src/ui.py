from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Checkbox, Static, RichLog, Label
from textual.screen import Screen, ModalScreen
from textual import work, on
import sys
import os
import shutil
import re
from datetime import datetime

from src.model import HostsManager, SOURCES

class DiffScreen(ModalScreen):
    """A screen that displays a diff of the changes."""
    def __init__(self, diff_content: str):
        super().__init__()
        self.diff_content = diff_content

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="diff_container", classes="box"):
            yield Label("Proposed Changes (/etc/hosts diff):", classes="stats")
            log = RichLog(id="diff_text", highlight=True, wrap=False)
            yield log
            with Horizontal():
                yield Button("Close", variant="primary", id="close_diff")
        
    def on_mount(self):
        log = self.query_one("#diff_text")
        for line in self.diff_content.splitlines():
            # Escape brackets in the line content to avoid markup issues
            safe_line = line.replace("[", "[[").replace("]", "]]")
            if line.startswith("+") and not line.startswith("+++"):
                log.write(f"[green]{safe_line}[/]")
            elif line.startswith("-") and not line.startswith("---"):
                log.write(f"[red]{safe_line}[/]")
            else:
                log.write(safe_line)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "close_diff":
            self.app.pop_screen()

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

    #diff_text {
        background: $surface;
        color: $text;
        padding: 1;
        height: 1fr;
    }
    
    .diff-add { color: green; }
    .diff-remove { color: red; }

    #log_window {
        height: 1fr;
        min-height: 10;
        border: tall $primary;
        background: $surface;
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
        self.manager.load_whitelist()
        self.manager.load_config()

    def generate_safe_id(self, name: str) -> str:
        """Generates a Textual-safe ID from a string."""
        safe = re.sub(r'[^a-z0-9_]', '_', name.lower())
        return f"cb_{safe}"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Vertical():
            yield Static(f"System Hosts Entries: {len(self.manager.system_entries)}", id="system_stats", classes="stats")
            
            yield Label("Select Sources to Fetch & Merge:")
            with ScrollableContainer(id="sources_list", classes="box"):
                for name in SOURCES.keys():
                    yield Checkbox(name, id=self.generate_safe_id(name))

            yield Static("Welcome! 1. Click 'Fetch & Analyze' to download lists. 2. Select lists below. 3. Click 'Apply' to save to /etc/hosts.", classes="box")
            
            with Horizontal(classes="box"):
                yield Button("Fetch & Analyze", id="btn_fetch", variant="primary")
                yield Button("Preview Merge", id="btn_preview", variant="warning")
                yield Button("Apply to /etc/hosts", id="btn_apply", variant="error")

            yield RichLog(id="log_window", highlight=True, markup=True)

    def on_mount(self):
        log = self.query_one("#log_window")
        log.write(f"Loaded {len(self.manager.system_entries)} entries from {self.manager.system_hosts_path}")
        
        if self.manager.whitelist:
            log.write(f"Loaded {len(self.manager.whitelist)} domains from whitelist.txt")
        else:
            log.write("No whitelist.txt found or empty (optional).")

        if not self.manager.is_root():
            log.write("[bold red]WARNING: Not running as root (UID != 0). SAVE DISABLED.[/]")
            self.query_one("#btn_apply").disabled = True
        else:
            log.write("[bold green]Running as root. Application ready.[/]")

        # Restore selected sources from config
        selected_in_config = self.manager.config.get("selected_sources", [])
        for name in selected_in_config:
            try:
                cb = self.query_one(f"#{self.generate_safe_id(name)}", Checkbox)
                cb.value = True
            except Exception:
                pass
        log.scroll_end()

    @on(Button.Pressed, "#btn_fetch")
    @work(exclusive=True, thread=True)
    def handle_fetch(self):
        log = self.query_one("#log_window")
        log.write("Fetching blocklists...")
        
        try:
            self.manager.fetch_all_sources()
            for name, entries in self.manager.remote_entries.items():
                log.write(f"Fetched {name}: {len(entries)} entries.")
            log.write("Fetch complete.")
        except Exception as e:
            log.write(f"FETCH ERROR: {e}")
        log.scroll_end()

    @on(Button.Pressed, "#btn_preview")
    def handle_preview(self):
        log = self.query_one("#log_window")
        selected = self.get_selected_sources()
        if not selected:
            log.write("No sources selected!")
            log.scroll_end()
            return
            
        try:
            diff = self.manager.generate_diff(selected)
            if not diff:
                 log.write("No changes detected (hosts already up-to-date).")
                 log.scroll_end()
                 return
                 
            self.push_screen(DiffScreen(diff))
        except Exception as e:
            log.write(f"PREVIEW ERROR: {e}")
            log.scroll_end()

    @on(Checkbox.Changed)
    def handle_checkbox_change(self):
        selected = self.get_selected_sources()
        self.manager.config["selected_sources"] = selected
        self.manager.save_config()

    def get_selected_sources(self):
        selected = []
        for name in SOURCES.keys():
            try:
                safe_id = self.generate_safe_id(name)
                cb = self.query_one(f"#{safe_id}", Checkbox)
                if cb.value:
                    selected.append(name)
            except Exception:
                pass
        return selected

    @on(Button.Pressed, "#btn_apply")
    def handle_apply(self):
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
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.manager.system_hosts_path}.{timestamp}.bak"
            log.write(f"Backing up to {backup_path}...")
            
            shutil.copy2(self.manager.system_hosts_path, backup_path)
            
            with open(self.manager.system_hosts_path, "w") as f:
                f.write(new_content)
                
            log.write("Successfully wrote to /etc/hosts!")
            if hasattr(self.manager, 'last_whitelisted_count') and self.manager.last_whitelisted_count > 0:
                 log.write(f"Note: {self.manager.last_whitelisted_count} domains were skipped due to whitelist.")
            
        except PermissionError:
            log.write("ERROR: Permission denied! You must run this script with sudo.")
            log.write("Run: sudo python main.py")
        except Exception as e:
            log.write(f"ERROR: {e}")
        log.scroll_end()

    def action_fetch(self):
        self.handle_fetch()

    def action_preview(self):
        self.handle_preview()

    def action_apply(self):
        self.handle_apply()

if __name__ == "__main__":
    app = HostsFilterApp()
    app.run()
