import sys
import os
import pytest
from typer.testing import CliRunner

# Add service root to path so 'cli' module is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli import app as cli_app

runner = CliRunner()

def test_create_customer_and_license(setup_db):
    result = runner.invoke(cli_app, [
        "create-customer", "--email", "cli@test.com", "--name", "CLI User"
    ])
    if result.exit_code != 0:
        with open("cli_error.txt", "w", encoding="utf-8") as f:
            f.write(f"Exit code: {result.exit_code}\n")
            f.write(f"Output: {result.output}\n")
            f.write(f"Exception: {result.exception}\n")
            if result.exception:
                import traceback
                f.write("".join(traceback.format_exception(type(result.exception), result.exception, result.exception.__traceback__)))
    assert result.exit_code == 0, f"Exit code: {result.exit_code}, Output: {result.output}"
    assert "Creado" in result.output
    assert "cli@test.com" in result.output

    result2 = runner.invoke(cli_app, [
        "create-license", "--customer-id", "1", "--plan", "personal"
    ])
    assert result2.exit_code == 0
    assert "HM-" in result2.output
    assert "COPIA ESTA KEY" in result2.output

def test_list_licenses(setup_db):
    result = runner.invoke(cli_app, ["list-licenses"])
    assert result.exit_code == 0

def test_revoke_license(setup_db):
    # Create customer and license first
    runner.invoke(cli_app, ["create-customer", "--email", "revoke@test.com"])
    runner.invoke(cli_app, ["create-license", "--customer-id", "1", "--plan", "personal"])

    result = runner.invoke(cli_app, ["revoke-license", "--license-id", "1"])
    assert result.exit_code == 0, f"Failed: {result.output}"
    assert "revocada" in result.output
