"""Extracts state of rekordbox as Snapshots.

Uses Optical Character Recognition to extract deck and mixer
values from a rekordbox session. Rekordbox must be the top window
on the primary monitor for the watcher to work.

Typical usage example:

  watcher = RekordboxWatcher()
  watcher.watch(api_endpoint="127.0.0.1:8000/incoming_snapshot")
"""
import pyautogui
import datetime
import json
import time
import psutil
import logging
import requests
import os

from .layout import load_from_json
from .extractor import ExtractorFactory, Extractor
from .schema import Snapshot

from typing import List, Optional

DEFAULT_CONFIG_PATH = f"{os.path.dirname(__file__)}/bounding_boxes.json"

logger = logging.getLogger(__name__)

def is_rekordbox_running():
    """Returns True if rekordbox.exe process found in process list."""
    return ("rekordbox.exe" in (p.name() for p in psutil.process_iter()))

class RekordboxWatcher:
    """Extracts state of rekordbox as Snapshots."""
    extractor_factory: ExtractorFactory
    num_decks: int

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        """Creates a new RekordboxWatcher using the config provided.

        Args:
            config_path (str): Path to JSON file containing bounding boxes.
        """
        logger.info(f"Creating RekordboxWatcher using config at: {config_path}")
        config = load_from_json(config_path)

        self.extractor_factory = ExtractorFactory(config)
        self.num_decks = 4

    def _transmit(self, api_endpoint: str, snapshot: Snapshot):
        """Sends snapshot in POST request to api_endpoint.

        Args:
            api_endpoint (str): URL of API endpoint accepting snapshots.
            snapshot (Snapshot): Snapshot to send
        """
        try:
            requests.post(api_endpoint, json = snapshot.model_dump(mode="python"))
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error occurred when transmitting snapshot: {e}")

    def look(self, previous_snapshot: Optional[Snapshot] = None) -> Optional[Snapshot]:
        """Extracts current state of rekordbox.

        Args:
            previous_snapshot (Snapshot, optional): Snapshot from previous extraction.
                Defaults to None.

        Returns:
            Snapshot, or None: Snapshot if rekordbox on screen and songs loaded,
                None if not.
        """
        current_time = time.time()
        current_image = pyautogui.screenshot()

        extractor: Extractor = self.extractor_factory.get_extractor(current_image)

        return extractor.extract_snapshot(current_time, current_image, previous_snapshot)

    def watch(self, api_endpoint = None) -> List[Snapshot]:
        """Repeatedly extracts and transmits rekordbox state.

        Args:
            api_endpoint (str, optional): URL of API endpoint accepting snapshots.

        Returns:
            List of Snapshot: List of snapshots extracted.
        """
        snapshots: List[Snapshot] = []
        snapshot: Optional[Snapshot] = None

        logger.info(f"Starting watch process.")
        while is_rekordbox_running():
            snapshot = self.look(snapshot)
            if snapshot is not None:
                logger.info(f"Extracted snapshot: {snapshot}")
                print(snapshot)
                if api_endpoint is not None:
                    self._transmit(api_endpoint, snapshot)
                else:
                    snapshots.append(snapshot)

        logger.info("No rekordbox process found.")

        return snapshots

def main(logging_level, config_path, api_endpoint, output_dir):
    logger.setLevel(logging_level)

    watcher = RekordboxWatcher(
        config_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    )
    snapshots = watcher.watch(api_endpoint)

    if len(snapshots) > 0:
        dt = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{output_dir}/session_{dt}.json"

        logger.info(f"Saving to: {output_path}")
        with open(output_path, "w") as f:
            f.write(
                json.dumps(
                    [snapshot.model_dump(mode="python") for snapshot in snapshots],
                    indent=4
                )
            )
        logger.info("Done!")
