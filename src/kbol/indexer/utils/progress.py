from rich import progress

def create_progress() -> progress.Progress:
    """Create a progress bar with standard formatting."""
    return progress.Progress(
        progress.TextColumn("[progress.description]{task.description}"),
        progress.BarColumn(),
        progress.TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        progress.TimeElapsedColumn(),
        progress.TimeRemainingColumn(),
    )
