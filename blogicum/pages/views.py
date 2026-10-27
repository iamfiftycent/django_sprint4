from django.views.generic import TemplateView


class AboutView(TemplateView):
    template_name = 'pages/about.html'


class RulesView(TemplateView):
    template_name = 'pages/rules.html'


class PageNotFoundView(TemplateView):
    template_name = 'pages/404.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.status_code = 404
        return response


class ServerErrorView(TemplateView):
    template_name = 'pages/500.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.status_code = 500
        return response


class CsrfFailureView(TemplateView):
    template_name = 'pages/403csrf.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.status_code = 403
        return response
