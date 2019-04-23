# Clapbot

This bot takes a command (/clap) and uses it to log who you're giving kudos to (as well as setting up a leaderboard).

It requires setting up a DynamoDB instance and two Lambda functions. The DB should have two tables:

1) claps-- with id as the primary key and other columns for shoutee, shouter, reason, date, and test.

2) leaderboard-- with shoutee as primary key and another column for claps.

You'll also need to declare a SLACK_OAUTH environment variable for both Lambdas to do Slack authentication.

--

Once you've created those, you can just deploy claps.py and leaderboard.py to their own lambdas and point the appropriate Slackbot or Slack command to each. Voila!