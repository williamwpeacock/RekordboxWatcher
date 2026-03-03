# Rekordbox Watcher
Python program using Optical Character Recognition to extract the current state of rekordbox from periodic screenshots. Created as part of a wider toolset intended to wrap rekordbox with more useful tools.

## Usage

```bash
cd RekordboxWatcher
python main.py --api_endpoint "127.0.0.1:8000"
```

## Limitations
- Extracted values are not always accurate
- Extraction takes a long time

## Future work
- requirements.txt
- Test suite
- EQ value extraction
- Support for different layouts and screen dimensions
- Implement check for rekordbox on screen
- Refactor into Python module
- Refactor to always extract songs when loaded and track is_playing value
- Optimise by saving previous state and only extracting values when necessary
- Investigate adding options for more control on extraction and transmission of data
- Investigate synchronising screenshot taking with master BPM
- Investigate extraction of values directly from memory
- Improve this README!

## Known bugs
- (Sometimes) crashes when rekordbox screen covered
