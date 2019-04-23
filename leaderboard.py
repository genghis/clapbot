import requests
import json
from flask import Flask, request, jsonify
import os
import boto3
from slacker import Slacker
from slackclient import SlackClient
import re

SLACK_TOKEN = os.environ['SLACK_OAUTH']
slack = Slacker(SLACK_TOKEN)
sc = SlackClient(SLACK_TOKEN)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('leaderboard')

app = Flask(__name__)

@app.route('/', methods=['POST'])
def lambda_handler():
	channel_id = request.form.get('channel_id')
	user_id = request.form.get('user_id')

	rows = table.scan(
			ProjectionExpression="shoutee, claps",
			)

	resultsdict = {}
	for entry in rows['Items']:
		resultsdict[entry['shoutee']] = str(entry['claps'])

	sorteddict = {k: v for k, v in sorted(resultsdict.items(), key=lambda x: x[1], reverse=True)}

	leaderarray = []
	for key, value in sorteddict.items():
		dictobj = [key, value]
		leaderarray.append(dictobj)

	firstPlaceName = leaderarray[0][0]
	firstPlaceCount = leaderarray[0][1]
	secondPlaceName = leaderarray[1][0]
	secondPlaceCount = leaderarray[1][1]
	thirdPlaceName = leaderarray[2][0]
	thirdPlaceCount = leaderarray[2][1]
	fourthPlaceName = leaderarray[3][0]
	fourthPlaceCount = leaderarray[3][1]
	fifthPlaceName = leaderarray[4][0]
	fifthPlaceCount = leaderarray[4][1]

	re2='.*?'	# Non-greedy match on filler
	re3='(@)'	# Any Single Character 1
	re4='((?:[a-z][a-z]*[0-9]+[a-z0-9]*))'	# Alphanum 1

	rg2 = re.compile(re2+re3+re4,re.IGNORECASE|re.DOTALL)
	firsticon= rg2.findall(firstPlaceName)
	secondicon= rg2.findall(secondPlaceName)
	thirdicon= rg2.findall(thirdPlaceName)
	fourthicon= rg2.findall(fourthPlaceName)
	fifthicon= rg2.findall(fifthPlaceName)

	first = firsticon[0]
	second = secondicon[0]
	third = thirdicon[0]
	fourth = fourthicon[0]
	fifth = fifthicon[0]

	iconlist = [first, second, third, fourth, fifth]
	icondict = {}
	realnames = {}

	for icon in iconlist:
		iconresponse = slack.users.profile.get(icon)
		iconblob = json.loads(f'{iconresponse}')
		iconurl = iconblob['profile']['image_512']
		iconname = iconblob['profile']['real_name']
		realnames[icon] = iconname
		icondict[icon] = iconurl

	firstname = f'{realnames[first]}'
	secondname = f'{realnames[second]}'
	thirdname = f'{realnames[third]}'
	fourthname = f'{realnames[fourth]}'
	fifthname = f'{realnames[fifth]}'

	firsturl = f'{icondict[first]}'
	secondurl = f'{icondict[second]}'
	thirdurl = f'{icondict[third]}'
	fourthurl = f'{icondict[fourth]}'
	fifthurl = f'{icondict[fifth]}'
	
	leaderboard = [
		{"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": ":trophy: *Leadboard* :trophy:"
			}
			},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f":champagne: With *{firstPlaceCount}* votes, *{firstname}* is in first place :champagne:"
			},
			"accessory": {
				"type": "image",
				"image_url": f"{firsturl}",
				"alt_text": f"{firstname}'s photo"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f":tada: With *{secondPlaceCount}* votes, *{secondname}* is in second place :tada:"
			},
			"accessory": {
				"type": "image",
				"image_url": f"{secondurl}",
				"alt_text": f"{secondname}'s photo"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f":fireworks: With *{thirdPlaceCount}* votes, *{thirdname}* is in third place :fireworks:"
			},
			"accessory": {
				"type": "image",
				"image_url": f"{thirdurl}",
				"alt_text": f"{thirdname}'s photo"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f":sparkler: With *{fourthPlaceCount}* votes, *{fourthname}* is in fourth place :sparkler:"
			},
			"accessory": {
				"type": "image",
				"image_url": f"{fourthurl}",
				"alt_text": f"{fourthname}'s photo"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f":confetti_ball: With *{fifthPlaceCount}* votes, *{fifthname}* is in fifth place :confetti_ball:"
			},
			"accessory": {
				"type": "image",
				"image_url": f"{fifthurl}",
				"alt_text": f"{fifthname}'s photo"
			}	
		}
		]

	readableleaderboard = json.dumps(leaderboard)

	sc.api_call(
		"chat.postEphemeral",
		channel=channel_id,
		blocks=readableleaderboard,
		user=user_id
		)

	return ""