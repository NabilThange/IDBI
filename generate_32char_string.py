import secrets
import string
from pathlib import Path

alphabet = string.ascii_letters + string.digits
value = ''.join(secrets.choice(alphabet) for _ in range(32))
out_path = Path(__file__).with_name('generated_api_secret.txt')
out_path.write_text(value + '\n', encoding='utf-8')
print(value)
print(f'Saved to: {out_path}')
