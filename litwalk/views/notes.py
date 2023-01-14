"""
lit-walk "notes" view
"""
from __future__ import annotations

from typing import Any
from rich.color import Color
from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.renderables._blend_colors import blend_colors
from textual.widgets import Input, Footer, Label

from textual_autocomplete._autocomplete import AutoComplete, DropdownItem, Dropdown

class NotesView(App):
    """
    Notes View Textual App class definition
    """
    CSS_PATH = "litwalk.css"
    BINDINGS = [Binding("ctrl+d", "toggle_dark", "Day/Night")]

    def __init__(self, articles:list[dict[str, Any]]):
        super().__init__()
        self._items = [DropdownItem(x['title']) for x in articles]

    def compose(self) -> ComposeResult:

        # auto complete match func
        def get_items(value: str, cursor_position: int) -> list[DropdownItem]:
            # Only keep cities that contain the Input value as a substring
            matches = [c for c in self._items if value.lower() in c.main.plain.lower()]

            # Favour items that start with the Input value, pull them to the top
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
            Label("Article", id="search-label"),
            id="search-container",
        )
        yield Footer()

if __name__ == "__main__":
    app = NotesView([{'title': "foo"}, {'title': 'bar'}])
    app.run()
