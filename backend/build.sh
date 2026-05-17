#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py shell -c "
from apps.doctors.models import Doctor
if Doctor.objects.count() == 0:
    import subprocess
    subprocess.run(['python', 'manage.py', 'loaddata', 'data/seed.json'])
    print('Seed data loaded')
else:
    print('Seed data already exists, skipping')
"
python manage.py shell -c "
from apps.rag.loader import load_knowledge
load_knowledge()
print('RAG reloaded')
"
