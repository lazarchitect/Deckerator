from flask import Flask, render_template, request, redirect, session, abort
import pymysql.cursors
import hashlib
import requests
import json
import time

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
	print("-------------------------\n\nDatabase down!\n\n-------------------------")

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
			return fetchRecord(query, params)
		except:
			return render_template("sqldberror.html")
	
	except AttributeError: #this ones serious. the connection cant be made at all
		return render_template("sqldberror.html")


#given a query, returns a single row from the database that matches.
#this method will return () (an empty tuple) for INSERT statements
def fetchAllRecords(query, params):
	global connection
	try:
		with connection.cursor() as cursor:
			cursor.execute(query, params)
			connection.commit()
			return cursor.fetchall() # NOTE THE "ALL"
	except (ConnectionAbortedError, pymysql.err.InterfaceError, pymysql.err.OperationalError) as e:
		# print("sql connection failed as " + str(e) + ". Reupping now.")
		try:
			connection = pymysql.connect(
				host = host,
				user = user,
				password=password,
				db = db
			)
			return fetchAllRecords(query, params) #NOTE THE 'ALL'
		except:
			return render_template("sqldberror.html")

	except AttributeError: #this ones serious. the connection cant be made at all
		return render_template("sqldberror.html")

#given a card name that has the number at the end, strip it and return just the name
def dropCount(cardRaw):
	retval = ""
	cardNameList = cardRaw.split(" ")[1:]
	for i in cardNameList:
		retval += (i + " ")
	return retval[:-1] #drop final space added.	

def StringAllColors(colorList):
	retval = ""
	for i in colorList:
		retval += i
	
	return "C" if retval=="" else retval	

def scryfallGetCard(cardName):
	cardData = requests.get("https://api.scryfall.com/cards/named?fuzzy=" + cardName).json()
	####### GET CARD COLOR, CMC, TYPE, AND ART FROM SCRYFALL
			
	try:
		if cardData['status'] == 404:
			###A GIVEN CARD DOESNT EXIST!
			return render_template("error.html", 
				name="Invalid Card Name", 
				back="javascript:history.back()", 
				error="The card name \"" + cardName + "\" is invalid. No such card exists.")
	except:
		pass #this is fine, the 'status' wont even appear if the request is valid, because it returns a card object, not a response object

	time.sleep(0.1)
	####### SLEEP .1 SECONDS TO BE NICE TO SCRYFALL

	cardColor= StringAllColors(cardData['colors'])
	cardCmc  = cardData['cmc']
	cardType = cardData['type_line']
	cardArtUrl = cardData['image_uris']['normal']
	cardMultID = cardData['multiverse_ids'][0]

	query = "INSERT INTO deckerator.cards (name, color, cmc, type, art_url, mult_id) VALUES (%s, %s, %s, %s, %s, %s)"
	params = (cardName, cardColor, cardCmc, cardType, cardArtUrl, cardMultID)
	fetchRecord(query, params)
	####### INSERT IT INTO MY DATABASE	












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
#Can only arrive here from newdeck.html.
@site.route('/submitdeck', methods=["POST"])
def submitDeck():
	#the decklist arrives, with each card name specified with a space
	deckRaw = request.form["deck"]
	name = request.form["name"]
	
	if deckRaw=="" or name=="":
		return "You can't leave the decklist or deck name blank. Go back and try again."
	
	#this block checks for duplicates based on its name. makes it possible to delete a deck later.
	
	query = "SELECT * FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, str(session['userid']))
	collision = fetchRecord(query, params)
	
	if collision != None:
		return render_template("error.html", back="/newdeck", name="Deck Name Error", error="A single user can't have two decks with the same name.")
	
	deckRawList = deckRaw.split("\r\n")
	
	deckdict = {}

	for cardRaw in deckRawList:

		cardRaw = cardRaw.strip()

		if cardRaw == "": continue #empty line
		
		# check if last 'word' is a parsable integer. 
		# if so, run the try block that many times with the rest of the line.
		# else, run it once with the whole line.

		try:
			count = int(cardRaw.split(" ")[0])
			cardName = dropCount(cardRaw)
		except ValueError:
			count = 1
			cardName = cardRaw

		try:
			deckdict[cardName] += count
		except KeyError:
			deckdict[cardName] = count

		query = "SELECT cardid FROM deckerator.cards WHERE name=%s"
		params = (cardName)
		
		if fetchRecord(query, params) == None:
			scryfallGetCard(cardName)
			
		# if this check failed, that means we have the card already, no worries fam


	deckdict = json.dumps(deckdict) #to make it into valid json

	query = "INSERT INTO deckerator.decks (code, name, userid) VALUES (%s, %s, %s)"
	params = (deckdict, name, session["userid"])
	fetchRecord(query, params) #nothing is fetched, dumb name, but it does insert

	# Now that the deck is uploaded, retrieve it with deckID

	query = "SELECT deckid FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, session["userid"])
	deckData = fetchRecord(query, params)

	deckid = deckData[0]

	return redirect("/deck/"+str(deckid))
	
#processing method for deck deletion. 405 triggers on GET.
@site.route('/deletedeck', methods=["POST"])
def deleteDeck():
	name = request.form["name"]
	deckOwner = int(request.form["deckOwner"]) #comes in as string

	if deckOwner != session['userid']:
		#user tried to delete a deck that doesnt belong to them 
		return "You are not the owner of this deck. Go back to the homepage. Please report this bug to eddie.lazar@yahoo.com." #failsafe
	
	query = "DELETE FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, session['userid'])
	fetchRecord(query, params)

	return render_template("deckdeleted.html")	

#processing method for deck updation.
@site.route('/editdeck', methods=["POST"])
def editDeck():

	if not loggedIn():
		return render_template("notloggedin.html")	

	name = request.form["name"]
	
	query = "SELECT code, deckid, userid FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, session['userid'])
	deckData = fetchRecord(query, params)

	if deckData == None:
		#deck with that name not found for this user AKA user tried to edit a deck that doesnt belong to them 
		return "You are not the owner of this deck. Go back to the homepage. Please report this bug to eddie.lazar@yahoo.com." #failsafe

	#deck is a tuple. First element is a string representation of a dict (lol)

	deck = eval(deckData[0]) #turn it into a dict
	deckid = deckData[1]

	deckString = json.dumps(deck)

	return render_template("editdeck.html", name=name, deck=deckString, deckid=deckid)

#processing method for deck reupload. 405 triggers on GET.
@site.route('/resubmitdeck', methods=["POST"])
def resubmitDeck():
	#the decklist arrives, with each card name specified with a space
	deckRaw = request.form["deck"]
	name = request.form["name"]
	deckid = request.form["deckid"]
	
	if deckRaw=="":
		return render_template("error.html", name="Deck Edit Error", back="/editdeck", error="You can't leave the decklist blank.")

	if name=="":
		return render_template("error.html", name="Deck Edit Error", back="/editdeck", error="You can't leave the deck name blank.")

	#this block checks for duplicates based on its name. makes it possible to delete a deck later.
	
	query = "SELECT * FROM deckerator.decks WHERE name=%s AND userid=%s AND deckid!=%s" #check for new name, this userid, NOT this deckid
	params = (name, str(session['userid']), deckid)
	collision = fetchRecord(query, params)
	
	if collision != None:
		return render_template("error.html", back="javascript:history.back()", name="Deck Edit Error", error="You can't have two decks with the same name.")

	deckRawList = deckRaw.split("\r\n")
	
	deckdict = {}

	for cardRaw in deckRawList:

		cardRaw = cardRaw.strip()
		
		if cardRaw == "": continue #empty line

		try:
			count = int(cardRaw.split(" ")[0])
			cardName = dropCount(cardRaw)
		except ValueError:
			count = 1
			cardName = cardRaw

		try:
			deckdict[cardName] += count
		except KeyError:
			deckdict[cardName] =  count

		query = "SELECT cardid FROM deckerator.cards WHERE name=%s"
		params = (cardName)
		
		if fetchRecord(query, params) == None: #if we dont already have the card in the DB
			scryfallGetCard(cardName)

	deckdict = json.dumps(deckdict) #to make it into valid json

	query = "UPDATE deckerator.decks SET code=%s, name=%s WHERE deckid=%s"
	params = (deckdict, name, deckid)
	fetchRecord(query, params)
	
	return redirect("/deck/" + str(deckid))

@site.route("/deck/<deckid>")
def deckview(deckid):

	#its ok if someone whos not logged in sees this, no need for the check

	# get decklist from server based on username and deckname.
	query = "SELECT name, code, userid FROM deckerator.decks WHERE deckid=%s"
	params = (deckid)
	deckData = fetchRecord(query, params)

	if deckData==None: #no such deck exists
		abort(404)

	#FOR EACH CARD NAME: GET ITS TYPE, COLOR, CMC, ART URL, SEND THAT TO CLIENT AS JSON. 

	cardInfoDict = {}

	for cardName in json.loads(deckData[1]):
		query = "SELECT name, color, cmc, type, art_url, mult_id FROM deckerator.cards WHERE name=%s"
		params = (cardName)
		cardData = fetchRecord(query, params)

		if cardData == None:
			scryfallGetCard(cardName) #inserts into db, try again now
			query = "SELECT name, color, cmc, type, art_url, mult_id FROM deckerator.cards WHERE name=%s"
			params = (cardName)
			cardData = fetchRecord(query, params)

		cardInfoDict[cardName] = cardData[1:]

	InfoPackage = json.dumps(cardInfoDict)

	return render_template("deck.html", name=deckData[0], deck=deckData[1], info=InfoPackage, deckOwner=deckData[2], owner=(deckData[2]==session['userid']))



#############   SETTINGS   ###############

@site.route("/changeusername", methods=["POST"])
def changeUsername():
	newUsername = request.form["newUsername"]
	oldUsername = session['username']

	#FIRST, CHECK FOR USERNAME TAKEN

	query = "SELECT username FROM deckerator.users WHERE username=%s"
	params = (newUsername)
	collision = fetchRecord(query, params)	

	if collision == None: #not found? good to go
		query = "UPDATE deckerator.users SET username=%s WHERE username=%s"
		params = (newUsername, oldUsername)
		fetchRecord(query, params)
		#success!
		session['username'] = newUsername #one last thing...
		return redirect("/settings")

	elif collision[0] == oldUsername: #found and its YOU?
		return render_template("error.html", back="javascript:history.back()", name="Username Error", error="Uh. That's the same name as before.")	

	else: #found and its someone else
		return render_template("error.html", back="javascript:history.back()", name="Username Error", error="That username is already taken. Sorry.")

@site.route("/changeemail", methods=["POST"])
def changeEmail():
	newEmail = request.form["newEmail"]
	oldEmail = session['email']

	#FIRST, CHECK FOR EMAIL TAKEN

	query = "SELECT email FROM deckerator.users WHERE email=%s"
	params = (newEmail)
	collision = fetchRecord(query, params)	

	if collision == None: #not found? good to go
		query = "UPDATE deckerator.users SET email=%s WHERE email=%s"
		params = (newEmail, oldEmail)
		fetchRecord(query, params)
		#success!
		session['email'] = newEmail #one last thing...
		return redirect("/settings")

	elif collision[0] == oldEmail: #found and its YOU?
		return render_template("error.html", back="javascript:history.back()", name="Email Error", error="Uh. That's the same email as before.")	

	else: #found and its someone else
		return render_template("error.html", back="javascript:history.back()", name="Email Error", error="That email address is already in use.")	

@site.route("/changepassword", methods=["POST"])
def changePassword():
	newPassword = request.form["newPassword"]

	secureNewPassword = password_hash(newPassword)
	
	query = "UPDATE deckerator.users SET password=%s WHERE userid=%s"
	params = (secureNewPassword, session['userid'])
	fetchRecord(query, params)
	
	return logout() #logs out and redirects to splash

	
@site.route("/deleteaccount", methods=["POST"])
def deleteAccount():
	email = request.form['email']
	password = request.form['password']

	#Check for correct credentials before deletion
	query = "SELECT userid FROM deckerator.users WHERE email=%s AND password=%s"
	params = (email, password_hash(password))

	collision = fetchRecord(query, params)
	
	if collision == None:
		#wrong credentials
		return render_template("error.html", back="javascript:history.back()", name="Deletion Error", error="Incorrect email or password for account deletion.")

	else: #sad to see you go
		query = "DELETE FROM deckerator.users WHERE email=%s AND password=%s"
		params = (email, password_hash(password))
		fetchRecord(query, params)

		query = "DELETE FROM deckerator.decks WHERE userid=%s" #deletes ALL decks from user
		params = (collision[0])
		fetchRecord(query, params)

		del session['userid']
		del session['username']
		del session['email']

		return render_template("accountdeleted.html")






































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

