from pyramid.view import view_config

from pinyon.toolchain import ToolChain


@view_config(route_name='home', renderer='template/home.jinja2')
def home(request):
    """Home page"""

    # Get the names of the extractors
    toolchains = ToolChain.objects.all()
    return {'toolchains': toolchains}


def includeme(config):
    """Used to perform includes for routes"""
    config.add_route('home', '/')