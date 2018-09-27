from flask import Flask, render_template, request, redirect, session
import pymysql.cursors
import hashlib

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
	return secure

#checks with the database to see if a given email and password exists
def valid_login(email, password):
	try:
		with connection.cursor() as cursor:
			query = "SELECT * FROM deckerator.users WHERE email=%s AND password=%s"
			password = password_hash(password)
			cursor.execute(query, (email, password))
			connection.commit()
			# connection.close()
			return cursor.fetchall() != [] 
	except AttributeError:
		return "Could not connect to database. Try again later."		

#self explanatory. checks to see if user is logged in. for pages like homepage/splash
def loggedIn():
	return 'email' in session

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
	if valid_login(request.form['email'], request.form['password']):
		session['email'] = request.form['email']
		return redirect('/homepage') #success
	else:
		return redirect('/loginfail') #failure

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
	try:
		with connection.cursor() as cursor:
				query = "SELECT * FROM deckerator.users WHERE username=%s AND email=%s"
				cursor.execute(query, (username, email))
				connection.commit()
				# connection.close()
				print(cursor.fetchall())
				return cursor.fetchall() != () # if there is a match in the database
	except AttributeError:
		return "Could not connect to database. Try again later."

#the action form for signing up. 
#Sends email, username, and password to the database IF everything was filled out correctly.
@site.route('/signupprocess', methods=['POST'])
def signupProcess():
	username = request.form['username']
	password = request.form['password']
	repeatpw = request.form['repeatpw']
	email = request.form['email']

	if username == "" or password == "" or email=="":
		return "No fields can be empty. <a href = \"/signup\">go back</a> and try again."

	if password != repeatpw:
		return "incorrect repeat password. <a href = \"/signup\">go back</a> and try again."
		
	if infoTaken(username, email):
		return "that username or email was already used. <a href = \"/signup\">go back</a> and try again."

	#success!
	try:
		with connection.cursor() as cursor:
			query = "INSERT INTO deckerator.users (username, email, password) VALUES (%s, %s, %s)"
			password = password_hash(password) #gotta hash the plaintext
			cursor.execute(query, (username, email, password))
			connection.commit()
		return render_template("signupSuccess.html") #send the user to the proper page.
	except AttributeError:
		return "Could not connect to database. Try again later." #possibly database downtime? idk

# the user's main page. view meaningful content here.
@site.route('/homepage')
def homepage():
	if loggedIn():
		return render_template("homepage.html", email=session['email'])
	return render_template("notloggedin.html") #how did you get here, you rascal?

# when the user hits the logout button, this function happens. 
#then they are redirected back to the welcome page.
@site.route('/logout')
def logout():
	del session['email']
	return redirect('/')

##############################
#ERROR HANDLER FUNCTIONS
##############################

#404 error page not found.
@site.errorhandler(404)
def handle404(idk):
	return render_template("404error.html")

#500 error server error. this one's my bad.
@site.errorhandler(500)
def handle500(idk):
	return render_template("500error.html")

