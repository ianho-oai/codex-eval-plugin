"""Explicit native Copilot account selection without copying credentials or settings."""
import json
from pathlib import Path

from .core import require


def selected_account(login, home=None):
    path = Path(home or Path.home()) / '.copilot' / 'config.json'
    try:
        # Copilot writes a JSON document preceded by whole-line comments.
        text = '\n'.join(line for line in path.read_text().splitlines()
                         if not line.lstrip().startswith('//'))
        config = json.loads(text)
    except (OSError, ValueError):
        require(False, 'Cannot read native Copilot account metadata; run copilot login first')
    expected = {'host': 'https://github.com', 'login': login}
    require(config.get('lastLoggedInUser') == expected,
            'Native Copilot active account does not match the frozen copilot_account')
    require(expected in config.get('loggedInUsers', []), 'Selected Copilot account is not saved')
    return expected


def seed_account(config_home, login):
    account = selected_account(login)
    # Only identity selectors are copied. Copilot resolves its own credential from
    # the OS store; tokens, hooks, plugins, permissions and other users are absent.
    (config_home / 'config.json').write_text(json.dumps({
        'lastLoggedInUser': account, 'loggedInUsers': [account],
        'disableAllHooks': True, 'ide': {'autoConnect': False},
    }) + '\n')
