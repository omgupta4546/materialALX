import os

replacements = {
    'app.models.base': 'app.models.base',
    'app.repositories.base': 'app.repositories.base',
    'app.core.connection': 'app.core.connection',
    'app.core.db_config': 'app.core.db_config'
}

for root, _, files in os.walk('.'):
    if '.git' in root or '.venv' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            original = content
            for old, new in replacements.items():
                content = content.replace(old, new)
            if content != original:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'Updated {filepath}')
