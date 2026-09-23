import os
import re

endpoints_dir = 'c:/Users/OMEN/Documents/New folder/backend/app/api/endpoints'
for file in os.listdir(endpoints_dir):
    if file.endswith('.py'):
        path = os.path.join(endpoints_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if 'def get_db():' in content and 'yield db' in content:
            # Replace local get_db with import
            content = re.sub(r'def get_db\(\):[\s\S]*?db\.close\(\)', '', content)
            
            # Add import app.api.deps
            if 'from app.api.deps import get_db' not in content:
                content = content.replace('from sqlalchemy.orm import Session', 'from sqlalchemy.orm import Session\nfrom app.api.deps import get_db')
                
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Fixed {file}')
