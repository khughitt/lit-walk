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
    BINDINGS = [Binding("ctrl+d", "toggle_dark", "Day/Night")]

    def __init__(self, articles:list[dict[str, Any]], notes_dir:str):
        super().__init__()
        self._articles = articles
        self._notes_dir = notes_dir

        self._items = [DropdownItem(x['title']) for x in articles]

    def on_auto_complete_selected(self, event: AutoComplete.Selected) -> None:
        """Item selection event handler"""
        # open matched article in editor (for now, assumes unique title..)
        for article in self._articles:
            if article["title"] == event.item.main.plain:
                note_path = os.path.join(self._notes_dir, article['md5'] + ".md")

                # if file doesn't exist, create and add title;
                # later, this can be extended with a more useful template..
                if not os.path.exists(note_path):
                    with open(note_path, "wt", encoding="utf-8") as fp:
                        fp.write(f"# {article['title']}\n")

                click.edit(filename=note_path)
                sys.exit()

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
                    id="my-dropdown",
                ),
            ),
            #Label("Article", id="search-label"),
            id="search-container",
        )
        yield Footer()
