import json
from datetime import datetime

from presentation.models import User, Presentation


class PresentationsService:

    @staticmethod
    def get_default_empty_project_object():
        return {
            "group" : None,
            "favourite" : False,
            "removed": False,
            "date_created" : datetime.now().timestamp(),
            "date_edited": datetime.now().timestamp(),
            "theme" : {
                "background_color": [255, 248, 220],
                "font_info": {
                    "titles": {"name": "Onest", "size": 44, "bold": True, "italic": False},
                    "main_texts": {"name": "Onest", "size": 18, "bold": False, "italic": False}
                }
            },
            "len_slides": 0,
            "title": "DefaultProjectName",
            "slides": []
        }

    @staticmethod
    def create_empty_project(user: User, title: str) -> Presentation:
        presentation_object = PresentationsService.get_default_empty_project_object()
        presentation_object['title'] = title
        project_json = json.dumps(presentation_object)

        presentation = Presentation.objects.create(
            user=user,
            json=project_json
        )
        return presentation
