import argparse
import logging

from .main import main

parser = argparse.ArgumentParser(
    prog='RekordboxWatcher',
    description='Extracts state of rekordbox as Snapshots, saving in output_dir or transmitting to api_endpoint.'
)

parser.add_argument('--config_path', default=None, help="path of JSON containing bounding boxes")
parser.add_argument('--api_endpoint', default=None, help="URL of API endpoint accepting snapshots")
parser.add_argument('--output_dir', default="out/", help="directory path to store resulting snapshots")
args = parser.parse_args()

main(logging.DEBUG, args.config_path, args.api_endpoint, args.output_dir)