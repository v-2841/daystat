# the browser chrome colour of each palette in the light and dark theme:
# stops of the page gradients in assets/css/source.css, keep in step
THEME_COLORS = {
    'pink': {'light': '#fdd8f6', 'dark': '#2c0724'},
    'blue': {'light': '#d4e6fe', 'dark': '#0a1a2e'},
}


def palette(request):
    # anonymous pages, the login one among them, keep the default pink
    name = getattr(getattr(request, 'user', None), 'palette', 'pink')
    return {
        'palette': name,
        'theme_color': THEME_COLORS[name],
    }
