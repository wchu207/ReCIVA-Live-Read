import json
from Application import Application
import tkinter as tk

def main():
    config = None
    with open('config.json', 'r') as f:
        config = json.load(f)

    root = tk.Tk()
    root.title('Breath Collection View')
    root.geometry('1600x1200')
    root.state('zoomed')
    model_path = None
    if 'model_path' in config:
        model_path = config['model_path']

    source_directory = None
    if 'source_directory' in config:
        source_directory = config['source_directory']

    app = Application(root, dir=source_directory, model_path=model_path)
    root.mainloop()



if __name__ == '__main__':
    main()