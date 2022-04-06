from django.http import HttpResponse
from django.template import loader


def index(request):
    template = loader.get_template('cloud/index.html')

    return HttpResponse(template.render())

def data(request):
    template = loader.get_template('cloud/data.html')

    return HttpResponse(template.render())

def experiment(request):
    template = loader.get_template('cloud/experiment.html')

    return HttpResponse(template.render())
