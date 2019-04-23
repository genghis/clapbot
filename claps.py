import requests
import json
from flask import Flask, request
import os
from slacker import Slacker
import re
import boto3
import uuid
import datetime
import decimal

dynamodb = boto3.resource('dynamodb')
claptable = dynamodb.Table('claps')
leadertable = dynamodb.Table('leaderboard')

SLACK_TOKEN = os.environ['SLACK_OAUTH']
slack = Slacker(SLACK_TOKEN)

app = Flask(__name__)

@app.route('/', methods=['POST'])
def lambda_handler():
	
	try:
		username = request.form.get('user_name')
		userid = request.form.get('user_id')
		shouter = f"<@{userid}|{username}>"
		text = request.form.get('text')
		reason = text
		test = False

		re1='(<@[^>]+>)'	# Tag 1
		rg = re.compile(re1,re.IGNORECASE|re.DOTALL)
		namelist = rg.findall(reason)

		re2='.*?'	# Non-greedy match on filler
		re3='(@)'	# Any Single Character 1
		re4='((?:[a-z][a-z]*[0-9]+[a-z0-9]*))'	# Alphanum 1

		rg2 = re.compile(re2+re3+re4,re.IGNORECASE|re.DOTALL)
		idlist= rg2.findall(reason)

		for i in namelist:
			reason = reason.replace(i,'')

		reason = reason.lstrip()
		today = datetime.date.today()

		for i in namelist:
			shoutee = i
			idnumber = uuid.uuid4()
			try:
				leadertable.put_item(
					Item={
					'shoutee': shoutee,
					'claps': decimal.Decimal(1),
					},
					ConditionExpression='attribute_not_exists(shoutee)')
			except:
				leadertable.update_item(
					Key={'shoutee': shoutee},
					UpdateExpression='set claps = claps + :val',
					ExpressionAttributeValues={
					':val': decimal.Decimal(1),
					},
					ReturnValues="UPDATED_NEW")
			finally:
				claptable.put_item(
					Item={
						'shoutee': shoutee,
						'shouter': shouter,
						'reason': reason,
						'id': str(idnumber),
						'test': False,
						'date': str(today),
					})

		shoutericonresponse = slack.users.profile.get(userid)
		shouterblob = json.loads(f'{shoutericonresponse}')
		shoutericon = shouterblob['profile']['image_512']
		realname = shouterblob['profile']['real_name']

		shouteefinal = namelist[-1]
		del namelist[-1]

		if namelist:
			shouteelist = ', '.join(namelist)
			channeltext = f"{shouter} gave {shouteelist} and {shouteefinal} :clap: three :clap: claps :clap: {reason}"
		else:
			channeltext = f"{shouter} gave {shouteefinal} :clap: three :clap: claps :clap: {reason}"

		slack.chat.post_message(as_user = False, username = realname, icon_url = shoutericon, channel = '#threeclaps', text = channeltext)
		
	except:
		return 'Looks like that didn\'t work. Making sure you\'re `@`ing one or more people and including a reason.\nExample: `/clap @brucewayne for clever deceptions`'
	else:
		return 'Claps Away! (note: you can see the current clap-leaders by using the `/leaderboard` command.)', 200