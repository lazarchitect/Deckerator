from flask import Flask, render_template, request, redirect, session, abort
import pymysql.cursors
import hashlib
import requests

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
	try:
		with connection.cursor() as cursor:
			cursor.execute(query, params)
			connection.commit()
			return cursor.fetchone()
	
	except AttributeError:
		print("attribute error")

	return None	#exceptions hit this	


#given a query, returns a single row from the database that matches.
#this method will return () (an empty tuple) for INSERT statements
def fetchAllRecords(query, params):
	try:
		with connection.cursor() as cursor:
			cursor.execute(query, params)
			connection.commit()
			return cursor.fetchall() #the only difference is here
	
	except AttributeError:
		print("attribute error")

	return None	#exceptions hit this
















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
	return render_template("login.html")

#the action form for a login attempt. Checks with database for valid credentials.
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
	return render_template('/loginfail.html')

#signup screen. enter new account details here.
@site.route('/signup')
def signupPage():
	return render_template('signup.html')

#for new users, checks to see if the username/email they gave is already in use
def infoTaken(username, email):

	query = "SELECT * FROM deckerator.users WHERE username=%s OR email=%s"
	params = (username, email)
	row = fetchRecord(query, params)

	return row != None #meaning there is a match, and the info IS taken.

#the action form for signing up. 
#Sends email, username, and password to the database IF everything was filled out correctly.
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

	if infoTaken(username, email):
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
	
	query = "SELECT name FROM deckerator.decks WHERE userid=%s"
	params = (session['userid'])
	decks = fetchAllRecords(query, params)

	decksString = ""

	for deck in decks: #comes as tuple. need to turn into json
		decksString += deck[0] + DELIMITER #deckData at zero is the name.

	decksString = decksString[:-3] #drop final delimiter

	return render_template("homepage.html", decks=decksString) 

# when the user hits the logout button, this function happens. 
#then they are redirected back to the welcome page.
@site.route('/logout')
def logout():
	del session['email']
	del session['userid']
	del session['username']
	return redirect('/')

@site.route('/settings')
def settingsPage():
	return render_template("settings.html")	

@site.route('/newdeck')
def newDeckPage():
	return render_template("newdeck.html")

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
	
	deckJSON = "{"

	for card in deck:
		deckJSON += "\""+card+"\":1," #needs proper formatting from list to dict

	#TODO: actually count the cards and write in their counts, instead of having duplicates

	deckJSON = deckJSON[:-1] + "}"	#drop the trailing comma and close the dict.

	query = "INSERT INTO deckerator.decks (code, name, userid) VALUES (%s, %s, %s)"
	params = (deckJSON, name, session["userid"])
	fetchRecord(query, params) #nothing is fetched, dumb name, but it does insert
	
	return render_template("deck.html", name=name, deck=deck)

@site.route('/deletedeck', methods=["POST"])
def deleteDeck():
	name = request.form["name"]
	
	query = "DELETE FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, session['userid'])
	fetchRecord(query, params)

	return render_template("deckdeleted.html")	

@site.route('/editdeck', methods=["POST"])
def editDeck():
	name = request.form["name"]
	deck = None
	
	query = "SELECT code FROM deckerator.decks WHERE name=%s AND userid=%s"
	params = (name, session['userid'])
	deck = fetchRecord(query, params)

	if deck == None:
		return "deck is none?" #this could happen due to sql server down, or the deck was never uploaded?

	#deck is a tuple whos first element is a str representation of a dict (lol)

	deck = eval(deck[0]) #turn it into a dict

	deckString = ""

	for card in deck:
		deckString += card + DELIMITER

	deckString = deckString[:-3] #drop final delimiter	

	return render_template("editdeck.html", name=name, deck=deckString)


@site.route('/resubmitdeck', methods=["POST"])
def resubmitDeck():
	#the decklist arrives, with each card name specified with a space
	deck = request.form["deck"]
	name = request.form["name"]
	oldname = request.form["oldname"]
	
	if deck=="":
		return render_template("error.html", name="Deck Edit Error", back="/editdeck", error="You can't leave the decklist blank.")

	if name=="":
		return render_template("error.html", name="Name Edit Error", back="/editdeck", error="You can't leave the deck name blank.")

	deck = deck.split("\r\n")
	
	deckJSON = "{"

	for card in deck:
		deckJSON += "\""+card+"\":1," #needs proper formatting from list to dict

	#TODO: actually count the cards and write in their counts, instead of having duplicates

	deckJSON = deckJSON[:-1] + "}"	#drop the trailing comma and close the dict.

	query = "UPDATE deckerator.decks SET code=%s, name=%s WHERE name=%s AND userid=%s"
	params = (deckJSON, name, oldname, session["userid"])
	fetchRecord(query, params)
	
	return render_template("deck.html", name=name, deck=deck)

@site.route("/deck/<username>/<deckname>")
def deckview(username, deckname):

	# get decklist from server based on username and deckname.
	query = "SELECT code FROM deckerator.decks WHERE userid=%s AND name=%s"
	params = (session['userid'], deckname)
	deck = fetchRecord(query, params)

	if deck==None: #no such deck exists
		abort(404)

	return render_template("deck.html", deck=deck, name=deckname)

















##############################
#ERROR HANDLER FUNCTIONS
##############################

#404 error page not found.
@site.errorhandler(404)
def handle404(idk):
	return render_template("404error.html"), 404

#500 error server error. this one's my bad.
@site.errorhandler(500)
def handle500(idk):
	return render_template("500error.html"), 500

