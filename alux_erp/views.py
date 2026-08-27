from django.http import HttpResponse


def root_status(request):
    return HttpResponse("Welcome to Alux Extrusions Backend. API is up and running.")
