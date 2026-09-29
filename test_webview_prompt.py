import webview
import time
import threading

def on_loaded():
    res = webview.windows[0].evaluate_js('prompt("Test");')
    print("Prompt returned:", res)
    webview.windows[0].destroy()

if __name__ == '__main__':
    window = webview.create_window('Test', html='<html><body><h1>Test</h1></body></html>')
    webview.start(on_loaded)
