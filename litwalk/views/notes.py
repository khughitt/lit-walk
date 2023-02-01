"""
lit-walk "notes" view
"""
from __future__ import annotations

import os
import sys
from typing import Any
import click
from rich.color import Color
from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.renderables._blend_colors import blend_colors
from textual.widgets import Checkbox, Input, Footer, Static
from textual import events
from textual.reactive import reactive
from textual_autocomplete._autocomplete import AutoComplete, DropdownItem, Dropdown

class NotesView(App):
    """
    Notes View Textual App class definition
    """
    CSS_PATH = "litwalk.css"
    BINDINGS = [
        Binding("ctrl+d", "toggle_dark", "Day/Night"),
        Binding("ctrl+e", "toggle_existing", "Show All/Existing Only?"),
        Binding("ctrl+q", "quit", "Quit")
    ]

    existing_only = reactive(False)
    num_articles = reactive(0)

    def __init__(self, articles:list[dict[str, Any]], notes_dir:str):
        super().__init__()

        self._articles = articles
        self._notes_dir = notes_dir

        # create a list of article ids with existing notes
        self._existing_ids:list[str] = []

        for article in self._articles:
            note_path = os.path.join(self._notes_dir, article["note"])
            if os.path.exists(note_path):
                self._existing_ids.append(article["id"])

        # create and store DropdownItem instances, indexed by article id
        self._dropdown_items = {}

        for article in articles:
            # ignore "{" and "}" when searching titles
            article_title = article["title"].replace("{", "").replace("}", "")
            self._dropdown_items[article["id"]] = DropdownItem(article_title)

        # set initial select options to include all articles
        self._update_select_opts()

    def _update_select_opts(self) -> None:
        """
        Updates dropdown items to either include all articles or only those with existing
        notes
        """
        #  #if self._existing_only:
        if self.existing_only:
            self._items = []

            for article_id, dropdown_item in self._dropdown_items.items():
                if article_id in self._existing_ids:
                    self._items.append(dropdown_item)
        else:
            self._items = self._dropdown_items.values()

        self.num_articles = len(self._items)
        

    def action_exit(self) -> None:
        """Exit the application"""
        self.exit()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode"""
        self.dark = not self.dark

    def action_toggle_existing(self) -> None:
        """Keyboard handler for toggle existing shortcut"""
        val = self.query_one("#toggle-existing").value
        self.query_one("#toggle-existing").value = not val

    def on_checkbox_changed(self) -> None:
        """Event handler for existing only checkbox toggle"""
        self.existing_only = not self.existing_only
        self._update_select_opts()

        # force refresh of downdown options currently displayed
        input_elem = self.query_one("#search-box")

        user_input = input_elem.value

        input_elem.value = ""
        input_elem.value = user_input

        self.query_one("#num-articles").update(str(f"articles: {self.num_articles}"))

    def on_auto_complete_selected(self, event: AutoComplete.Selected) -> None:
        """Item selection event handler"""
        # open matched article in editor (for now, assumes unique title..)
        for article in self._articles:
            article_title = article["title"].replace("{", "").replace("}", "")

            if article_title == event.item.main.plain:
                note_path = os.path.join(self._notes_dir, article["note"])

                # create directory if needed
                if not os.path.exists(os.path.dirname(note_path)):
                    os.mkdir(os.path.dirname(note_path), mode=0o755)

                # if file doesn't exist, create and add title;
                # later, this can be extended with a more useful template..
                if not os.path.exists(note_path):
                    with open(note_path, "wt", encoding="utf-8") as fp:
                        fp.write(f"# {article_title}\n")

                click.edit(filename=note_path)
                self.exit()

    def on_mount(self) -> None:
        """
        Sets the focus to input field at app init
        """
        # set focus to search input
        self.set_focus(self.query_one("#search-box"))

        self.query_one("#num-articles").update(str(f"articles: {self.num_articles}"))

    def compose(self) -> ComposeResult:

        # auto complete match func
        def get_items(value: str, cursor_position: int) -> list[DropdownItem]:
            # get matching articles
            matches = [c for c in self._items if value.lower() in c.main.plain.lower()]

            # prioritize left-anchored matches
            ordered = sorted(matches, key=lambda v: v.main.plain.startswith(value.lower()))

            return ordered

        yield Static("lit-walk / notes", id="title-text")
        yield Horizontal(
            Static(id="num-articles"),
            id="num-articles-container"
        )
        yield AutoComplete(
            Input(id="search-box", placeholder="Search for an article.."),
            Dropdown(
                items=get_items,
                id="search-opts",
            ),
            id="search-autocomplete"
        )
        yield Horizontal(
            Static("Existing only", classes="label"),
            Checkbox(id="toggle-existing", value=self.existing_only),
            id='settings-bar'
        )
        yield Footer()
