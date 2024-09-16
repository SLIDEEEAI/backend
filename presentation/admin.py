from django.contrib import admin
from .models import Roles, User, Presentation


admin.site.register([
    Roles, User
])


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'updated_at',)
