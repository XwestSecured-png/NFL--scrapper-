import requests
import json
import os
from datetime import datetime
from google.oauth2.service_account import Credentials
import gspread

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = "1fkUoF1o-R0vQEB_IPcJfWwZBDLLbJHrCw955_GxSuNU"

def get_nfl_schedule(year, week):
    """Fetch NFL schedule from ESPN API"""
    url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    params = {'dates': f"{year}{str(week).zfill(2)}01"}
    
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching NFL schedule: {e}")
        return None

def write_to_sheet(games_data):
    """Write game data to Google Sheet"""
    try:
        creds = Credentials.from_service_account_info(
            json.loads(os.getenv('GOOGLE_SHEETS_CREDS')),
            scopes=SCOPES
        )
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        
        for game in games_data:
            row = [
                game['week'],
                game['date'],
                game['game_label'],
                game['home_team'],
                game['away_team'],
                game['stadium'],
                game['time'],
            ] + [''] * 31
            sheet.append_row(row)
            
        print(f"✓ Added {len(games_data)} games")
    except Exception as e:
        print(f"Sheet error: {e}")

def process_schedule(schedule_json):
    """Parse ESPN schedule"""
    games = []
    events = schedule_json.get('events', [])
    
    for event in events:
        competitor = event['competitions'][0]['competitors']
        home = next((c for c in competitor if c['homeAway'] == 'home'), None)
        away = next((c for c in competitor if c['homeAway'] == 'away'), None)
        
        if home and away:
            game = {
                'week': event.get('week', ''),
                'date': event['date'][:10],
                'game_label': f"{away['team']['displayName']} @ {home['team']['displayName']}",
                'home_team': home['team']['displayName'],
                'away_team': away['team']['displayName'],
                'stadium': event['competitions'][0].get('venue', {}).get('fullName', 'TBD'),
                'time': event['date'][11:16],
            }
            games.append(game)
    
    return games

if __name__ == "__main__":
    today = datetime.now()
    year = today.year
    week = max(1, (today.timetuple().tm_yday - 245) // 7 + 1)
    
    print(f"Fetching week {week}...")
    schedule = get_nfl_schedule(year, week)
    
    if schedule:
        games = process_schedule(schedule)
        if games:
            write_to_sheet(games)
    else:
        print("No schedule data")
