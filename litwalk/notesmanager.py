"""
NotesManager class definition
"""
import pathlib

class NotesManager:
    def __init__(self, notes_dir:str):
        """Initializes NotesManager"""
        # create directory if it doesn't already exist
        path = pathlib.Path(notes_dir)

        if not path.exists():
            path.mkdir(mode=0o755, parents=True)

