from __future__ import annotations

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.footnote import footnote_plugin


class MarkdownRenderer:
    def __init__(self) -> None:
        self._md = (
            MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True})
            .use(tasklists_plugin, enabled=True)
            .use(footnote_plugin)
        )

    def render(self, text: str) -> str:
        return self._md.render(text or "")
