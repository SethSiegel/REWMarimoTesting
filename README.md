# REW Marimo Testing

## Paths And Data Storage
This project resolves data paths relative to the git repo so it works on both Windows and macOS without editing hardcoded paths.

Default data folders:
1. `data/mdat`
2. `data/json`
3. `data/stepped-sine`

Folders are created automatically on startup.

### Optional: Override With `.env`
You can override the data location by creating a `.env` file at the repo root:

```env
REW_DATA_DIR=C:\Users\yourname\Documents\rew_marimo_data
```

macOS example:

```env
REW_DATA_DIR=/Users/yourname/Documents/rew_marimo_data
```

If `REW_DATA_DIR` is set, all data will be read/written under that folder.
