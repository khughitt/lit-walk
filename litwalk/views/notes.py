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
from textual.containers import Container
from textual.renderables._blend_colors import blend_colors
from textual.widgets import Button, Input, Footer, Label
from textual import events
from textual_autocomplete._autocomplete import AutoComplete, DropdownItem, Dropdown

class NotesView(App):
    """
    Notes View Textual App class definition
    """
    CSS_PATH = "litwalk.css"
    BINDINGS = [
        Binding("ctrl+d", "toggle_dark", "Day/Night"),
        Binding("ctrl+e", "toggle_existing", "Show All/Existing Only?"),
        Binding("escape", "exit", "Exit")
    ]

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
            self._dropdown_items[article["id"]] = DropdownItem(article["title"])

        # set initial select options to include all articles
        self._existing_only = False
        self._update_select_opts()

        #self._items = [DropdownItem(x["title"]) for x in articles]

    def _update_select_opts(self) -> None:
        """
        Updates dropdown items to either include all articles or only those with existing
        notes
        """
        if self._existing_only:
            self._items = []

            for article_id, dropdown_item in self._dropdown_items.items():
                if article_id in self._existing_ids:
                    self._items.append(dropdown_item)
        else:
            self._items = self._dropdown_items.values()

    def action_exit(self) -> None:
        """Exit the application"""
        self.exit()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode"""
        self.dark = not self.dark

    def action_toggle_existing(self) -> None:
        """Toggle all/existing notes display"""
        self._existing_only = not self._existing_only
        self._update_select_opts()

        # refresh downdown options currently displayed?
        input_elem = self.query_one("#search-box")

        user_input = input_elem.value

        input_elem.value = ""
        input_elem.value = user_input

    def on_auto_complete_selected(self, event: AutoComplete.Selected) -> None:
        """Item selection event handler"""
        # open matched article in editor (for now, assumes unique title..)
        for article in self._articles:
            if article["title"] == event.item.main.plain:
                note_path = os.path.join(self._notes_dir, article["note"])

                # create directory if needed
                if not os.path.exists(os.path.dirname(note_path)):
                    os.mkdir(os.path.dirname(note_path), mode=0o755)

                # if file doesn't exist, create and add title;
                # later, this can be extended with a more useful template..
                if not os.path.exists(note_path):
                    with open(note_path, "wt", encoding="utf-8") as fp:
                        fp.write(f"# {article['title']}\n")

                click.edit(filename=note_path)
                self.exit()

    def on_mount(self) -> None:
        """
        Sets the focus to input field at app init
        """
        # set focus to search input (?)
        self.set_focus(self.query_one("#search-box"))

    def compose(self) -> ComposeResult:

        # auto complete match func
        def get_items(value: str, cursor_position: int) -> list[DropdownItem]:
            # get matching articles
            matches = [c for c in self._items if value.lower() in c.main.plain.lower()]

            # prioritize left-anchored matches
            ordered = sorted(matches, key=lambda v: v.main.plain.startswith(value.lower()))

            return ordered

        yield Container(
            Label("lit-walk Notes", id="lead-text"),
            AutoComplete(
                Input(id="search-box", placeholder="Search for an article.."),
                Dropdown(
                    items=get_items,
                    id="search-opts",
                ),
                id="search-autocomplete"
            )
            #Label("Article", id="search-label"),
        )
        yield Footer()
