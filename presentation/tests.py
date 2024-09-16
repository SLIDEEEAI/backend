import os
import json
import django
from django.core.exceptions import ObjectDoesNotExist

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'source.settings')
django.setup()

from presentation.models import Presentation

def main():
    presentations = Presentation.objects.all()

    for presentation in presentations:
        try:
            content_data = json.loads(presentation.json)
        except json.JSONDecodeError:
            print(f"Error decoding JSON for presentation ID {presentation.id}")
            continue

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
