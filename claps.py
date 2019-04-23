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
	# I'm sure there's a more elegant way to do this, but I just wrap everything in a Try/Except/Else loop. There's another one INSIDE. 
	try:
		username = request.form.get('user_name')
		userid = request.form.get('user_id')
		shouter = f"<@{userid}|{username}>" # This is the way you need to format incoming stuff to form a proper userID/username combo because Slack refuses to make this easy
		reason = request.form.get('text')
		test = False #This will only ever be 'True' if you manually set it in the code for a test version of this code. ALSO, I don't REALLY use this anymore but figured it may end up being useful in the future.

		re1='(<@[^>]+>)'	# Regular Expression looking for stuff that is clearly a userid/username combo in <@SOMESTUFF|SOMEOTHERSTUFF> format
		rg = re.compile(re1,re.IGNORECASE|re.DOTALL)
		namelist = rg.findall(reason) # Actually pulls the total number of shoutees

		# This takes the text of the command and yanks out all the names
		for i in namelist:
			reason = reason.replace(i,'') 

		reason = reason.lstrip() # This removes whitespace before the 'reason' so it displays nicer
		today = datetime.date.today() 

		for i in namelist:
			shoutee = i
			idnumber = uuid.uuid4() # Black magic voodoo, necessary for unique primary keys in Dynamo
			
			# If there is no item with the shoutee name, create on.
			try:
				leadertable.put_item(
					Item={
					'shoutee': shoutee,
					'claps': decimal.Decimal(1),
					},
					ConditionExpression='attribute_not_exists(shoutee)') # This is the logic to only create it if there's not already an entry for this person
			
			# If the above doesn't work, you should update the existing one by incrementing the claps value +1
			except:
				leadertable.update_item(
					Key={'shoutee': shoutee},
					UpdateExpression='set claps = claps + :val',
					ExpressionAttributeValues={
					':val': decimal.Decimal(1),
					},
					ReturnValues="UPDATED_NEW")

			# No matter what, add the entry for the actual clap to the clap table with all the info. The leaderboard no longer looks at this soooooo it's only useful for future development now.
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

		shoutericonresponse = slack.users.profile.get(userid) # Gets the profile info of the person giving claps
		shouterblob = json.loads(f'{shoutericonresponse}')  # Make that profile info pretty and parsable
		shoutericon = shouterblob['profile']['image_512'] # Pulls the image from the shouter's profile so we can pretend we're them when we post to slack
		realname = shouterblob['profile']['real_name'] # Grabs the shouter's name so it's less robotic seeming

		shouteefinal = namelist[-1] # VERY PYTHONIC -- storing the last entry in namelist[] in 'shouteefinal'
		del namelist[-1] # AND THEN DELETING IT TO DO LOGIC

		if namelist: # VERY PYTHONIC -- 'if thing' has an inherent truthiness. If something has a Null value (as in, we deleted its only entry above) this will throw an exception. If not, as in, it has any value, it is 'True'. Practcally speaking, this means "if there was more than one name in the list, do this"
			shouteelist = ', '.join(namelist) 
			channeltext = f"{shouter} gave {shouteelist} and {shouteefinal} :clap: three :clap: claps :clap: {reason}"
		else: # If there was only one person getting shouted, get the grammar right
			channeltext = f"{shouter} gave {shouteefinal} :clap: three :clap: claps :clap: {reason}"

		slack.chat.post_message(as_user = False, username = realname, icon_url = shoutericon, channel = '#threeclaps', text = channeltext) # Post the claps
		
	except: # Fires if someone gave a bad command
		return 'Looks like that didn\'t work. Making sure you\'re `@`ing one or more people and including a reason.\nExample: `/clap @brucewayne for clever deceptions`'
	else: # Actually returns if Try is successful, sends the '200' and this message to slack to stop it from having a breakdown about timeouts
		return 'Claps Away! (note: you can see the current clap-leaders by using the `/leaderboard` command.)', 200