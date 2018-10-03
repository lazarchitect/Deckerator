from flask import Flask, render_template, request, redirect, session, abort
import pymysql.cursors
import hashlib
import requests
import json

##
#Table of Contents
#------------------
#Setup Variables
#Helper Methods
#Site Pages
#Error Handler Functions
##























##############################
#SETUP VARIABLES
##############################

site = Flask(__name__)

f = open("environs.txt", "r")

site.secret_key = f.readline()[:-1]
host = f.readline()[:-1]
user = f.readline()[:-1]
password = f.readline()[:-1]
db = f.readline()

f.close()

DELIMITER = "[~{"

connection = None

try:
	connection = pymysql.connect(
		host = host,
		user = user,
		password=password,
		db = db)
except:
	print("sql connection failed. Undo try block for info")

##############################
#HELPER METHODS
##############################


#Given a password, securely hashes it
def password_hash(unsecure_string):
	encoded = unsecure_string.encode('utf-8') #encode string in format for hashing 
	m = hashlib.sha256() #create an object for hashing
	m.update(encoded) #feed it the encoded string
	secure = m.hexdigest() #get a sendable version
	secure = secure[:42] #the hex digest is too long for pymysql. idk why.
	return secure

#self explanatory. checks to see if user is logged in. for pages like homepage/splash
def loggedIn():
	return 'email' in session	

#given a query, returns a single row from the database that matches.
#this method will return None for INSERT statements
def fetchRecord(query, params):
	global connection
	try:
		with connection.cursor() as cursor:
			cursor.execute(query, params)
			connection.commit()
			return cursor.fetchone()
	except (ConnectionAbortedError, pymysql.err.InterfaceError, pymysql.err.OperationalError):
		try:
			connection = pymysql.connect(
				host = host,
				user = user,
				password=password,
				db = db
			)
		except:
			print("sql connection failed. Undo try block for info")


#given a query, returns a single row from the database that matches.
#this method will return () (an empty tuple) for INSERT statements
def fetchAllRecords(query, params):
	global connection
	try:
		with connection.cursor() as cursor:
			cursor.execute(query, params)
			connection.commit()
			return cursor.fetchall() # NOTE THE "ALL"
	except (ConnectionAbortedError, pymysql.err.InterfaceError, pymysql.err.OperationalError):
		try:
			connection = pymysql.connect(
				host = host,
				user = user,
				password=password,
				db = db
			)
		except:
			print("sql connection failed. Undo try block for info")














##############################
#SITE PAGES
##############################


#Main Page of the site. Your homepage if logged in, a welcome page if not.
@site.route('/')
def main():
	if loggedIn():
		return redirect('/homepage')
	return render_template("splash.html")

#Login screen for entering credentials
@site.route("/login")
def loginPage():

	if loggedIn():
		return redirect('/homepage')

	return render_template("login.html")

#the action form for a login attempt. Checks with database for valid credentials.
#if a user tries to GET this page, 405 error triggers.
@site.route("/loginprocess", methods = ['POST'])
def loginProcess():
	
	# check if the user exists.
	# if so, set the session fields to their details and redirect to homepage
	# else, redirect to loginfail

	query = "SELECT userid, username FROM deckerator.users WHERE email=%s AND password=%s"
	params = (request.form['email'], password_hash(request.form['password']))

	row = fetchRecord(query, params)

	if row != None: #if it DOES exist...
		session['userid'] = row[0]
		session['username'] = row[1]
		session['email'] = request.form['email']
		return redirect('/homepage') 
	else:
		return redirect('/loginfail')

#when a user enters invalid credentials
@site.route('/loginfail')
def loginFail():
	if loggedIn():
		return redirect('/homepage')
	return render_template('/loginfail.html')

#signup screen. enter new account details here.
@site.route('/signup')
def signupPage():
	if loggedIn():
		return redirect('/homepage')
	return render_template('signup.html')

#the action form for signing up. 
#Sends email, username, and password to the database IF everything was filled out correctly.
#if a user tries to GET this page, 405 error triggers.
@site.route('/signupprocess', methods=['POST'])
def signupProcess():
	username = request.form['username']
	password = request.form['password']
	repeatpw = request.form['repeatpw']
	email = request.form['email']

	if username == "" or password == "" or email=="":
		return render_template("error.html", back="/signup", name="Signup Error", error="No fields can be empty.")

	if password != repeatpw:
		return render_template("error.html", back="/signup", name="Password Error", error="Incorrect repeat password.")

	query = "SELECT * FROM deckerator.users WHERE username=%s OR email=%s"
	params = (username, email)
	row = fetchRecord(query, params)
	if row != None:
		return render_template("error.html", back="/signup", name="Account Error", error="That username or email was already used.")

	#successful account creation!
	query = "INSERT INTO deckerator.users (username, email, password) VALUES (%s, %s, %s)"
	params = (username, email, password_hash(password))
	fetchRecord(query, params) #nothing is fetched but the query does insert.

	return render_template("signupSuccess.html") #send the user to the proper page.
	
# the user's main page. view meaningful content here.
@site.route('/homepage')
def homepage():
	if not loggedIn():
		return render_template("notloggedin.html") #how did you get here, you rascal?
	
	#get all decks from sqldb that match user's ID.
	#Send names to template.
	
	query = "SELECT name, deckid FROM deckerator.decks WHERE userid=%s"
	params = (session['userid'])
	decks = fetchAllRecords(query, params)

	deckNameString = ""
	deckIdString = ""

	for deck in decks: #comes as tuple. need to turn into json
		deckNameString += deck[0] + DELIMITER #deckData at zero is the name.
		deckIdString += str(deck[1]) + DELIMITER

	deckNameString = deckNameString[:-3] #drop final delimiter
	deckIdString = deckIdString[:-3] #drop final delimiter

	return render_template("homepage.html", decks=deckNameString, ids=deckIdString) 

# when the user hits the logout button, this function happens. 
#then they are redirected back to the welcome page.
@site.route('/logout')
def logout():
	if loggedIn():
		del session['email']
		del session['userid']
		del session['username']
	
	return redirect('/') # clever eh?

@site.route('/settings')
def settingsPage():
	if not loggedIn(): return render_template("notloggedin.html")
	return render_template("settings.html")	

@site.route('/newdeck')
def newDeckPage():
	if not loggedIn(): return render_template("notloggedin.html")
	return render_template("newdeck.html")

#processing method for deck upload. 405 triggers on GET.
@site.route('/submitdeck', methods=["POST"])
def submitDeck():
	#the decklist arrives, with each card name specified with a space
	deck = request.form["deck"]
	name = request.form["name"]
	
	if deck=="" or name=="":
		return "You can't leave the decklist or deck name blank. Go back and try again."
	
	#this block checks for duplicates based on its name. makes it possible to delete a deck later.
	
	query = "SELECT * FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, str(session['userid']))
	collision = fetchRecord(query, params)
	
	if collision != None:
		return render_template("error.html", back="/newdeck", name="Deck Name Error", error="A single user can't have two decks with the same name.")
	
	deck = deck.split("\r\n")
	
	deckdict = {}

	apostropheSpots = []

	for card in deck:
		if card == "": continue #empty line
		try:
			deckdict[card] += 1
		except KeyError:
			deckdict[card] =  1

	deckdict = json.dumps(deckdict) #to make it into valid json
	
	print(deckdict)

	query = "INSERT INTO deckerator.decks (code, name, userid) VALUES (%s, %s, %s)"
	params = (deckdict, name, session["userid"])
	fetchRecord(query, params) #nothing is fetched, dumb name, but it does insert

	# Now that the deck is uploaded, retrieve it with deckID

	query = "SELECT deckid FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, session["userid"])
	deckData = fetchRecord(query, params)
	
	return redirect("/deck/"+deckData[0])
	
#processing method for deck deletion. 405 triggers on GET.
@site.route('/deletedeck', methods=["POST"])
def deleteDeck():
	name = request.form["name"]
	
	query = "DELETE FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, session['userid'])
	fetchRecord(query, params)

	return render_template("deckdeleted.html")	

#processing method for deck updation. 405 triggers on GET.
@site.route('/editdeck', methods=["POST"])
def editDeck():
	name = request.form["name"]
	
	query = "SELECT code, deckid FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, session['userid'])
	deckData = fetchRecord(query, params)

	if deckData == None:
		return "deckData is none?" #this could happen due to sql server down, or the deck was never uploaded?

	print(str(deckData) + " is deckdata")

	#deck is a tuple whos first element is a str representation of a dict (lol)

	deck = eval(deckData[0]) #turn it into a dict
	deckid = deckData[1]

	deckString = ""

	for card in deck:
		for count in range(deck[card]):
			deckString += card + DELIMITER

	deckString = deckString[:-3] #drop final delimiter	

	return render_template("editdeck.html", name=name, deck=deckString, deckid=deckid)

#processing method for deck reupload. 405 triggers on GET.
@site.route('/resubmitdeck', methods=["POST"])
def resubmitDeck():
	#the decklist arrives, with each card name specified with a space
	deck = request.form["deck"]
	name = request.form["name"]
	deckid = request.form["deckid"]
	
	if deck=="":
		return render_template("error.html", name="Deck Edit Error", back="/editdeck", error="You can't leave the decklist blank.")

	if name=="":
		return render_template("error.html", name="Name Edit Error", back="/editdeck", error="You can't leave the deck name blank.")

	deck = deck.split("\r\n")
	
	deckdict = {}

	for card in deck:
		if card == "": continue #empty line
		try:
			deckdict[card] += 1
		except KeyError:
			deckdict[card] = 1

	deckdict = json.dumps(deckdict) #to make it into valid json

	query = "UPDATE deckerator.decks SET code=%s, name=%s WHERE deckid=%s"
	params = (deckdict, name, deckid)
	fetchRecord(query, params)
	
	return redirect("/deck/" + str(deckid))

@site.route("/deck/<deckid>")
def deckview(deckid):

	#its ok if someone whos not logged in sees this, no need for the check

	# get decklist from server based on username and deckname.
	query = "SELECT name, code FROM deckerator.decks WHERE deckid=%s"
	params = (deckid)
	deck = fetchRecord(query, params)

	if deck==None: #no such deck exists
		abort(404)

	return render_template("deck.html", name=deck[0], deck=deck[1])

















##############################
#ERROR HANDLER FUNCTIONS
##############################

#404 error page not found.
@site.errorhandler(404)
def handle404(msg):
	return render_template("404error.html", msg=msg), 404

#405 error method not allowed.
@site.errorhandler(405)
def handle405(msg):
	return render_template("405error.html", msg=msg), 405

#500 error server error. this one's my bad.
@site.errorhandler(500)
def handle500(msg):
	return render_template("500error.html", msg=msg), 500

