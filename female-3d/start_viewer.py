"""Serve the offline viewer on loopback for Obsidian web embeds. Python 3.9+."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser

def main():
    parser=argparse.ArgumentParser(description='Local female 3D teaching viewer')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    if not (root/'female-3d.html').is_file():
        parser.error('female-3d.html is missing. Extract the complete offline package first.')
    try:
        server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(SimpleHTTPRequestHandler,directory=str(root)))
    except OSError as error:
        parser.exit(1,f'Cannot start local viewer: {error}\nUse --port with an available port, and update the embed address to match.\n')
    address=f'http://127.0.0.1:{args.port}/female-3d.html'
    print(f'Viewer: {address}\nKeep this terminal open while teaching. Press Ctrl+C to stop.',flush=True)
    if not args.no_browser:webbrowser.open(address)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
