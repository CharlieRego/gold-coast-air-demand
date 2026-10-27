class SourceChangedError(RuntimeError):
    """A source page or file no longer looks the way the pipeline expects. Stop and inspect."""


class DataCheckError(RuntimeError):
    """One or more data checks failed. Nothing downstream should be published."""
