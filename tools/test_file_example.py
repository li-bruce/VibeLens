"""Exercise the standalone recorded example without any observer implementation."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHECK = r"""
import io, re, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from app.web import create_app
app = create_app(Path(sys.argv[1]))
store = app.extensions['sharing'].store
def client(name):
    value = app.test_client()
    text = value.get('/login').get_data(as_text=True)
    token = re.search(r'name="csrf" value="([^"]+)"', text).group(1)
    assert value.post('/login', data={'username': name, 'password': 'file-demo-2026', 'csrf': token}).status_code == 302
    return value
def post(value, path, **data):
    with value.session_transaction() as session: token=session['csrf']
    return value.post(path, data={'csrf': token, **data})
try:
    owner, recipient, other = [client(name) for name in ['linzhou', 'xuning', 'zhoulan']]
    content = b'File-sharing standalone check.\n'
    assert post(owner, '/upload', file=(io.BytesIO(content), 'sample.txt')).status_code == 302
    item = owner.get('/api/files').json[0]
    ident = item['id']; url=f'/files/{ident}/download'
    assert recipient.get(url).status_code == 403
    assert post(owner, f'/files/{ident}/share', recipient_id='xuning').status_code == 302
    assert post(owner, f'/files/{ident}/share', recipient_id='zhoulan').status_code == 302
    assert recipient.get(url).data == content
    assert post(recipient, f'/files/{ident}/share', recipient_id='zhoulan').status_code == 403
    assert post(owner, f'/files/{ident}/revoke', recipient_id='xuning').status_code == 302
    assert recipient.get(url).status_code == 403
    assert owner.get(url).data == other.get(url).data == content
    assert post(owner, f'/files/{ident}/share', recipient_id='xuning').status_code == 302
    assert recipient.get(url).data == content
    assert not any(name == 'bo_observer' or name.startswith(('bo_observer.', 'observer_runtime.', 'integrations.')) for name in sys.modules)
    print('PASS: native core, login/upload/share, recipient-specific revoke, owner/other recipient, regrant and observer-free execution.')
finally:
    store.engine.dispose()
"""


def main():
    scratch = ROOT / ".validation"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="file-core-", dir=scratch) as folder:
        target = Path(folder) / "project"
        shutil.copytree(
            ROOT / "examples/file-sharing",
            target,
            ignore=shutil.ignore_patterns("data", "__pycache__", ".venv"),
        )
        subprocess.run(
            [sys.executable, "-I", "-B", "-X", "utf8", "-c", CHECK, str(target)],
            cwd=folder,
            check=True,
        )


if __name__ == "__main__":
    main()
