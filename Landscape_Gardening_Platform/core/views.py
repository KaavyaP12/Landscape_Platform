from urllib import request
from django.http import HttpResponse

# Create your views here.
def index(request):
    # return render(request, "core/index.html")
    return HttpResponse("Hello, welcome to the Landscape Gardening Platform!")
