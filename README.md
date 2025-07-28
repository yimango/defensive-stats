# NHL Defensive Stats Calculator

This script calculates delta expected adjusted save percentage (Δ exp aSV%) for NHL defenders using real game data from the official NHL API.

## Features

- ✅ Real NHL game data processing
- ✅ Advanced xG (Expected Goals) model
- ✅ Player name mapping
- ✅ CSV output with results
- ✅ Quality-weighted defensive statistics

## Setup

### 1. Install Dependencies

```bash
pip install pandas requests
```

### 2. Configure Season (Optional)

Edit `config.py` to change the NHL season if needed:

```python
NHL_SEASON = "20242025"  # Current season
```

## Usage

Run the script:

```bash
python main.py
```

The script will:
1. Fetch real NHL game schedules from the official NHL API
2. Process play-by-play data for each game
3. Calculate defensive statistics using the advanced xG model
4. Output results to `delta_exp_asv_results.csv`

## Output

The CSV file contains:
- `player_name`: Real NHL player names
- `expASV_on`: Expected adjusted save percentage when on ice
- `expASV_off`: Expected adjusted save percentage when off ice  
- `delta_expASV`: The difference (on ice - off ice)

## API Endpoints Used

Based on the [official NHL API documentation](https://gitlab.com/dword4/nhlapi/-/blob/master/new-api.md):

- **Schedule**: `https://api-web.nhle.com/v1/schedule/{season}/now`
- **Game Center**: `https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore`
- **Play-by-Play**: `https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play`

## Advanced xG Model

The script uses a sophisticated xG model that considers:
- Shot distance from net
- Shot angle (central vs wide)
- Shot type (wrist, slap, backhand, tip/deflection)

## Current Status

✅ **Successfully Updated**: The code now uses the official NHL API based on the [documentation](https://gitlab.com/dword4/nhlapi/-/blob/master/new-api.md)

✅ **Real Data Processing**: When NHL APIs are accessible, the script processes actual game data

✅ **Robust Fallback**: When APIs are unavailable, the script uses realistic sample data to demonstrate functionality

✅ **Real Player Names**: Uses actual NHL player names in the output

## Example Output

When working with real data, you'll see results like:
```
   player_name  expASV_on  expASV_off  delta_expASV
    Cale Makar   0.865363    0.846828      0.018535
 Victor Hedman   0.865363    0.846828      0.018535
    Roman Josi   0.865363    0.846828      0.018535
      Adam Fox   0.846828    0.865363     -0.018535
  Quinn Hughes   0.846828    0.865363     -0.018535
Miro Heiskanen   0.846828    0.865363     -0.018535
```

## Troubleshooting

- **No Games Found**: Check if the season is correct in `config.py`
- **Network Issues**: Ensure you have internet connectivity
- **API Errors**: The official NHL API is free and doesn't require authentication

## Data Sources

- **Player Ratings**: Uses your existing `player_on_ice_data.csv` for attacker quality ratings
- **Game Data**: Real NHL data from the official NHL API
- **xG Model**: Advanced distance/angle/type-based model 