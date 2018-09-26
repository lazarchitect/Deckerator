from flask import Flask, render_template, request, redirect, session
import pymysql.cursors
import hashlib

site = Flask(__name__)

f = open("environs.txt", "r")

site.secret_key = f.readline()[:-1]
host = f.readline()[:-1]
user = f.readline()[:-1]
password = f.readline()[:-1]
db = f.readline()

f.close()

connection = None

# try:
connection = pymysql.connect(
	host = host,
	user = user,
	password=password,
	db = db)
# except:
# 	print("sql connection failed. Undo try block for info")

def password_hash(unsecure_string):
	m = hashlib.sha256()
	m.update(unsecure_string.encode('utf-8'))
	print(m.hexdigest())
	return m.hexdigest()

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

def loggedIn():
	return 'email' in session

@site.route('/')
def main():
	if loggedIn():
		return redirect('/homepage')
	return render_template("splash.html")

@site.route("/login")
def loginPage():
	return render_template("login.html")

@site.route("/loginprocess", methods = ['POST'])
def loginProcess():
	if valid_login(request.form['email'], request.form['password']):
		session['email'] = request.form['email']
		return redirect('/homepage')
	else:
		return redirect('/loginfail')

@site.route('/loginfail')
def loginFail():
	return render_template('/loginfail.html')

@site.route('/signup')
def signupPage():
	return render_template('signup.html')

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
			password = password_hash(password)
			cursor.execute(query, (username, email, password))
			connection.commit()
			# connection.close()
		return render_template("signupSuccess.html")
	except AttributeError:
		return "Could not connect to database. Try again later."

@site.route('/homepage')
def homepage():
	if loggedIn():
		return render_template("homepage.html", email=session['email'])
	return render_template("notloggedin.html")

@site.route('/logout')
def logout():
	del session['email']
	return redirect('/')

@site.errorhandler(404)
def handle404(idk):
	return render_template("404error.html")

@site.errorhandler(500)
def handle500(idk):
	return render_template("500error.html")

