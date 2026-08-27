from django.contrib import admin

# Register your models here.
from user.models import CustomGroup, User

admin.site.register(User)
admin.site.register(CustomGroup)
