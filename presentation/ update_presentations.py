# update_presentations.py

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'source.settings')  # Изменено имя приложения

django.setup()

from presentation.models import Presentation  # Изменено имя модели

def main():
    presentations = Presentation.objects.all()

    for presentation in presentations:
        content_data = presentation.json
        presentation.author = content_data.get('author', None)
        presentation.title = content_data.get('title', None)
        presentation.group = content_data.get('group', None)
        presentation.favourite = content_data.get('favourite', False)
        presentation.removed = content_data.get('removed', False)
        presentation.date_created = content_data.get('date_created', None)
        presentation.date_edited = content_data.get('date_edited', None)
        presentation.theme = content_data.get('theme', None)
        presentation.save()

if __name__ == "__main__":
    main()
