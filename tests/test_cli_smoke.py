from typer.testing import CliRunner
from codex_integration.vector_cli import app

def test_cli_runs_help():
    r = CliRunner().invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "Persistent LangChain wrapper" in r.stdout
