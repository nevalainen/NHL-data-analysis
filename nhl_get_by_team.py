#TODO: Set team and days with parameters or some other nice way
#TODO: Currently it just saves JSON and prints the point difference with sample size,
#	   -> Some visualization to present the differences, maybe in order from best to worse
#TODO: Stat triggers currently not implemented, which would help to filter out the "good" picks

import json
import requests
import pandas as pd
import datetime
from datetime import timedelta
import pytz

TEAM_LINK = "/api/v1/teams/"
PEOPLE_LINK = "/api/v1/people/"
SCHEDULE_LINK = "/api/v1/schedule"
TEAM_SCHEDULE = "?teamId="
STATS_VS_TEAMS = "/stats?stats=vsTeam&season="
ROSTER_LINK = "?expand=team.roster"
TEAM_ID = "10"
BASE_URL = "https://statsapi.web.nhl.com"
STATS_PER_SEASON = "/stats?stats=statsSingleSeason&season="
START_DATE = "&startDate="#2018-01-02
END_DATE = "&endDate=" #2018-01-20
DAYS_QTY = 6

seasons = [
	'20172018',
	'20182019',
	'20192020',
	'20202021',
	'20212022'
]

stats_to_collect = [
	'games',
	'goals',
	'points'
]

sheet = {
	'player_name': 'A',
	'ppg_diff_current': 'B',
	'ppg_diff_p1': 'C',
	'ppg_diff_p2': 'D',
	'ppg_diff_p3': 'E',
	'games_current_season': 'F',
	'ppg_current': 'G',
	'ppg_p1': 'H',
	'ppg_p2': 'I',
	'ppg_p3': 'J',
	'games_against_opp': 'K',
	'ppg_against_opp_current': 'L',
	'ppg_against_opp_p1': 'M',
	'ppg_against_opp_p2': 'N',
	'ppg_against_opp_p3': 'O',
	'last_10_games': 'P',
	'last_5_games': 'Q',
	'last_3_games': 'R',
	'point_game_rate_perc': 'S',
	'point_game_rate_odd': 'T',
	'point_game_rate_against_opp_perc': 'U',
	'point_game_rate_against_opp_odd': 'V',
	'opponent': 'W',
	'opponent_GAA': 'X',
	'opponent_GAA_vs_league': 'Y'

}
"""
stat_triggers determines the limits that need to be exceeded to stand out. 
Current limits:
- Point per game must be over 0.2 points higher than season average
- Player has gained a point in over 60% of the games

Limits to consider
- Number of samples (games played)
"""
stat_triggers = {
	'ppg_diff_current': 0.2,
	'point_game_rate_perc': 60
}



opponent_ids = []
#https://statsapi.web.nhl.com/api/v1/teams/25?expand=team.roster
players = []

"""
This will just return goal and point average
"""
def calc_stats(stats, season = False):

	#print(stats)
	stats_out = {}
	try:
		stats_out['goalsPerGame'] = round(stats['goals'] / stats['games'], 2)
	except ZeroDivisionError:
		stats_out['goalsPerGame'] = 0
	try:
		stats_out['pointsPerGame'] = round(stats['points'] / stats['games'], 2)
	except ZeroDivisionError:
		stats_out['pointsPerGame'] = 0

	return stats_out

""" 
get_opponents will retrieve list of opponents during selected timespan
First it will get starting and ending date with function get_date(), which will
return date of today, and date after DAYS_QTY amount of days
opponents will be saved to opponent_ids -list
"""
def get_opponents():
	#gets list of opponents during selected timespan
	

	date1, date2 = get_date('America/New_York')
	team_games = json.loads(requests.get("{}{}{}{}{}{}{}{}".format(BASE_URL, SCHEDULE_LINK,TEAM_SCHEDULE,TEAM_ID,START_DATE,date1,END_DATE,date2)).text)
	
	
	for game in team_games['dates']:
		for team in game['games'][0]['teams']:
			
			if game['games'][0]['teams'][team]['team']['id'] != int(TEAM_ID):

				opponent_ids.append({
					'id': game['games'][0]['teams'][team]['team']['id'], 
					'name': game['games'][0]['teams'][team]['team']['name']
					})


def get_date(timezone):
	date = datetime.datetime.now(pytz.timezone(timezone))
	date2 = date + timedelta(days=DAYS_QTY)
	date2 = date2.strftime("%Y-%m-%d")
	date = date.strftime("%Y-%m-%d")

	return date, date2
	

def main():

	stats = []
	get_opponents()

	#Gets the roster and saves it to list
	
	resp = requests.get("{}{}{}{}".format(BASE_URL,TEAM_LINK,TEAM_ID,ROSTER_LINK))
	roster_json = json.loads(resp.text)	
	for i in roster_json['teams'][0]['roster']['roster']:
		if i['position']['code'] != "G": #No goalies included
			players.append(i['person'])
	
	"""
	Player constains keys id, fullName, and link. Next steps will add seasonal statistics to that
	"""
	for player in players:
		#print(player['fullName'])
		#https://statsapi.web.nhl.com/api/v1/people/
		player['seasons'] = {}
		for season in seasons:
			season_stats = json.loads(requests.get("{}{}{}{}{}".format(BASE_URL,PEOPLE_LINK,player['id'],STATS_PER_SEASON,season)).text)
			stats_vs_team = json.loads(requests.get("{}{}{}{}{}".format(BASE_URL,PEOPLE_LINK,player['id'],STATS_VS_TEAMS,season)).text)
		
			player['seasons'][season] = {}
			
			"""
			This messy for-loop-thingy here first checks if player has even played the season
			If so, it:
			-> Initializes the keys for seasonal stats
			-> Loops through opponent teams from opponent_ids
			-> saves the stats defined in stats_to_collect:
				-> Total season stats
				-> Stats in season against the selected opponent
				-> Adds the stats against the opponent to player/season/opponents, which
				contains total stats against selected opponents (useful if there is many games
				during selected timespan)
			->  Finally, calculates the goals and points per game by looping through data saved in above steps
			"""
			if len(season_stats['stats'][0]['splits']) != 0:
				player['seasons'][season]['season'] = {}
				player['seasons'][season]['opponents']	= {}

				for opponent in opponent_ids:
					player['seasons'][season][opponent['name']] = {}
					for i in stats_vs_team['stats'][0]['splits']:
						if i['opponent']['id'] == int(opponent['id']):
							for stat in stats_to_collect:
								#If combined points against chosen teams do not exist yet, it will be created here
								if stat not in player['seasons'][season]['opponents']: 
									player['seasons'][season]['opponents'][stat] = 0

								player['seasons'][season][opponent['name']][stat] = i['stat'][stat]
								player['seasons'][season]['season'][stat] = season_stats['stats'][0]['splits'][0]['stat'][stat]
								player['seasons'][season]['opponents'][stat] += i['stat'][stat] 
							#adv_stats = calc_stats(player[season][opponent['name']])
							#for stat in adv_stats:
						#		player[season][opponent['name']][stat] = adv_stats[stat]
				for opp in player['seasons'][season]:
					if len(player['seasons'][season][opp]) != 0:
						adv_stats = calc_stats(player['seasons'][season][opp])
						for stat in adv_stats:
							player['seasons'][season][opp][stat] = adv_stats[stat]		
					
		print(player)

		
	
	"""
	Save the data to json, so it can be viewed/used 
	"""
	with open('data.json', 'w') as outfile:
		json.dump(players, outfile)
		
	
	for player in stats:
		print(player['fullName'])
		for season in seasons:
			if len(player['seasons'][season]) != 0:
				if len(player['seasons'][season]['season']) != 0: 
					point_diff = player['seasons'][season]['opponents']['pointsPerGame'] - player['seasons'][season]['season']['pointsPerGame']
					print("{} n={}".format(round(point_diff, 2),player['seasons'][season]['opponents']['games']))  	

		#point_diff = player[]

if __name__ == '__main__':
	main()