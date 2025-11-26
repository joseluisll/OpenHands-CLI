"""Custom autocomplete functionality for OpenHands CLI.

This module provides enhanced autocomplete behavior for command input,
including suffix-style descriptions and smart completion logic.
"""

from pathlib import Path

from textual_autocomplete import AutoComplete, DropdownItem, TargetState

from openhands_cli.locations import WORK_DIR


class CommandAutoComplete(AutoComplete):
    """Custom AutoComplete showing descriptions after commands, completing command."""

    def get_search_string(self, target_state: TargetState) -> str:
        """Only match on the leading command token (e.g. `/help`).

        Any characters after the first space (like arguments or ` - `)
        will stop autocomplete from matching at all.
        """
        # Text up to the cursor
        raw = target_state.text[: target_state.cursor_position]

        # Ignore leading whitespace
        raw = raw.lstrip()

        # Only trigger autocomplete if we're starting with a slash-command
        if not raw.startswith("/"):
            return ""

        # If there's a space, user has started typing arguments (" /help - ...")
        # => stop matching entirely
        if " " in raw:
            return ""

        # Otherwise, use the whole token as the search string (e.g. "/he", "/help")
        return raw

    def apply_completion(self, value: str, state) -> None:  # noqa: ARG002
        """Apply completion, but only insert the command part (before the ' - ')."""
        # Extract just the command part (before the description)
        if " - " in value:
            command_only = value.split(" - ")[0]
        else:
            command_only = value

        # Apply the command-only completion to the target input
        if self.target:
            self.target.value = ""
            self.target.insert_text_at_cursor(command_only)


class EnhancedAutoComplete(AutoComplete):
    """Enhanced AutoComplete that handles both commands (/) and file paths (@)."""

    def __init__(self, target, command_candidates=None, **kwargs):
        """Initialize with command candidates and no static candidates."""
        self.command_candidates = command_candidates or []
        # Don't pass candidates to parent - we'll handle them dynamically
        super().__init__(target, candidates=None, **kwargs)

    def get_candidates(self, target_state: TargetState) -> list[DropdownItem]:
        """Get candidates based on the current input context."""
        # Text up to the cursor
        raw = target_state.text[: target_state.cursor_position]
        raw = raw.lstrip()

        if raw.startswith("/"):
            # Command completion
            return self._get_command_candidates(raw)
        elif raw.startswith("@"):
            # File path completion
            return self._get_file_candidates(raw)
        else:
            # No completion for other cases
            return []

    def _get_command_candidates(self, raw: str) -> list[DropdownItem]:
        """Get command candidates for slash commands."""
        # If there's a space, user has started typing arguments
        if " " in raw:
            return []

        return self.command_candidates

    def _get_file_candidates(self, raw: str) -> list[DropdownItem]:
        """Get file path candidates for @ paths."""
        # Remove the @ prefix to get the path part
        path_part = raw[1:]  # Remove @

        # If there's a space, stop completion
        if " " in path_part:
            return []

        # Determine the directory to search in
        if "/" in path_part:
            # User is typing a path with directories
            dir_part = "/".join(path_part.split("/")[:-1])
            search_dir = Path(WORK_DIR) / dir_part
            filename_part = path_part.split("/")[-1]
        else:
            # User is typing in the root working directory
            search_dir = Path(WORK_DIR)
            filename_part = path_part

        candidates = []

        try:
            if search_dir.exists() and search_dir.is_dir():
                # Get all files and directories
                for item in sorted(search_dir.iterdir()):
                    # Skip hidden files unless user is specifically typing them
                    if item.name.startswith(".") and not filename_part.startswith("."):
                        continue

                    # Create relative path from working directory
                    try:
                        rel_path = item.relative_to(Path(WORK_DIR))
                        path_str = str(rel_path)

                        # Add trailing slash for directories
                        if item.is_dir():
                            path_str += "/"
                            prefix = "📁"
                        else:
                            prefix = "📄"

                        candidates.append(
                            DropdownItem(main=f"@{path_str}", prefix=prefix)
                        )
                    except ValueError:
                        # Item is not relative to WORK_DIR, skip it
                        continue

        except (OSError, PermissionError):
            # Directory doesn't exist or no permission
            pass

        return candidates

    def get_search_string(self, target_state: TargetState) -> str:
        """Get the search string based on the input type."""
        raw = target_state.text[: target_state.cursor_position]
        raw = raw.lstrip()

        if raw.startswith("/"):
            # Command completion - only match if no spaces
            if " " in raw:
                return ""
            return raw
        elif raw.startswith("@"):
            # File path completion - match the path part
            path_part = raw[1:]
            if " " in path_part:
                return ""
            # Return the filename part for matching
            if "/" in path_part:
                return path_part.split("/")[-1]
            else:
                return path_part
        else:
            return ""

    def apply_completion(self, value: str, state) -> None:  # noqa: ARG002
        """Apply completion based on the type of completion."""
        if self.target is None:
            return

        current_text = self.target.value

        if current_text.lstrip().startswith("/"):
            # Command completion - extract just the command part
            if " - " in value:
                command_only = value.split(" - ")[0]
            else:
                command_only = value
            self.target.value = ""
            self.target.insert_text_at_cursor(command_only)
        elif current_text.lstrip().startswith("@"):
            # File path completion - replace the @ path
            self.target.value = ""
            self.target.insert_text_at_cursor(value)
