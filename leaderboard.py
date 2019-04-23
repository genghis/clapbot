import requests
import json
from flask import Flask, request, jsonify
import os
import boto3
from slacker import Slacker
from slackclient import SlackClient
import re

# NOTE: I have to use both Slacker and SlackClient, because I can't use Slacker to pass blocks the way I want to in an ephemeralMessage. I'm just as unhappy about it as you are.

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

	# This asks dynamoDB for every entry in the DB. It is NOT performant but will not matter in an org as small as Revel
	rows = table.scan(
			ProjectionExpression="shoutee, claps",
			)

	# This next little bit just creates some dictionary entries for the stuff returned from the DB.
	resultsdict = {}
	for entry in rows['Items']: 
		resultsdict[entry['shoutee']] = str(entry['claps'])

	# Using foul sorcery, the following sorts the dictionary items by value -- specifically, it ranks the highest number of claps first)
	sorteddict = {k: v for k, v in sorted(resultsdict.items(), key=lambda x: x[1], reverse=True)}

	# This is me being a bad programmer. I have to take the dictionary above and turn it into a series of listed pairs in a different list in order to later pull the info I need out of it
	leaderarray = []
	for key, value in sorteddict.items():
		dictobj = [key, value]
		leaderarray.append(dictobj)

	# Directly referencing the indexes within my newly created ordered list
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

	# This regular expression set just finds the userid in order to later pull icons, names, etc.
	re2='.*?'	
	re3='(@)'	
	re4='((?:[a-z][a-z]*[0-9]+[a-z0-9]*))'	
	rg2 = re.compile(re2+re3+re4,re.IGNORECASE|re.DOTALL)

	# This uses the regular expression to actually tear apart the string inside of firstPlaceName, secondPlaceName, etc.
	firsticon= rg2.findall(firstPlaceName)
	secondicon= rg2.findall(secondPlaceName)
	thirdicon= rg2.findall(thirdPlaceName)
	fourthicon= rg2.findall(fourthPlaceName)
	fifthicon= rg2.findall(fifthPlaceName)

	# Storing the userid, which will be used as a key in a couple dictionaries later
	first = firsticon[0]
	second = secondicon[0]
	third = thirdicon[0]
	fourth = fourthicon[0]
	fifth = fifthicon[0]

	iconlist = [first, second, third, fourth, fifth]
	icondict = {}
	realnames = {}

	# Take each userid and go get profile info -- an image url and a human readable name. Then put that info into some ordered lists.
	for icon in iconlist:
		iconresponse = slack.users.profile.get(icon)
		iconblob = json.loads(f'{iconresponse}')
		iconurl = iconblob['profile']['image_512']
		iconname = iconblob['profile']['real_name']
		realnames[icon] = iconname
		icondict[icon] = iconurl

	# This is some hackery to be able to use iteration instead of a lot of copy-paste manual stuff.
	firstname = f'{realnames[first]}'
	secondname = f'{realnames[second]}'
	thirdname = f'{realnames[third]}'
	fourthname = f'{realnames[fourth]}'
	fifthname = f'{realnames[fifth]}'

	# This is ALSO some hackery to be able to use iteration instead of a lot of copy-paste manual stuff.
	firsturl = f'{icondict[first]}'
	secondurl = f'{icondict[second]}'
	thirdurl = f'{icondict[third]}'
	fourthurl = f'{icondict[fourth]}'
	fifthurl = f'{icondict[fifth]}'
	
	# leaderboard[] is the preliminary list that will become json that will become a Block passed to slack.
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

	readableleaderboard = json.dumps(leaderboard) # make that list into some json

	# This is your actual info, pushed to the user who sent the /leaderboard request. "postEphemeral" is Slack's "only you can see this" option.
	sc.api_call(
		"chat.postEphemeral",
		channel=channel_id,
		blocks=readableleaderboard,
		user=user_id
		)

	return ""