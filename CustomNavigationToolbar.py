import json

from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

class CustomNavigationToolbar(NavigationToolbar2Tk):
    toolitems = (
        ('Home', 'Reset original view', 'home', 'home'),
        ('Back', 'Back to previous view', 'back', 'back'),
        ('Forward', 'Forward to next view', 'forward', 'forward'),
        (None, None, None, None),
        ('Pan',
         'Left button pans, Right button zooms\n'
         'x/y fixes axis, CTRL fixes aspect',
         'move', 'pan'),
        ('Zoom', 'Zoom to rectangle\nx/y fixes axis', 'zoom_to_rect', 'zoom'),
        ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
        ('Save Subplot Configurations', 'Save subplot configurations under config.json', 'filesave', 'save_subplot_configs'),
        (None, None, None, None),
        ('Save', 'Save the figure', 'filesave', 'save_figure'),
    )

    def __init__(self, canvas, parent, liveplot):
        self.liveplot = liveplot
        NavigationToolbar2Tk.__init__(self, canvas, parent)

    def save_subplot_configs(self):
        config = None
        with open('config.json', 'r') as f:
            config = json.load(f)
        if config is not None:
            with open('config.json', 'w') as f:
                config['plot_params'] = self.liveplot.get_configs()
                json.dump(config, f)