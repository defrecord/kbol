import typer
from rich.console import Console

app = typer.Typer(
    name="kbol",
    help="Knowledge Base for OLlama - Process and query technical books",
    no_args_is_help=True,
)
console = Console()


def init_app():
    """Initialize CLI application."""
    # Import commands here to avoid circular imports
    from .commands import process, query, stats, list, validate, topics

    # Register commands
    process.register(app)
    query.register(app)
    stats.register(app)
    list.register(app)
    validate.register(app)
    topics.register(app)

    return app


# For direct use
app = init_app()
