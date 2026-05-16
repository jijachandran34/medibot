#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py shell -c "
from apps.rag.loader import load_knowledge
load_knowledge()
print('RAG loaded')
"
