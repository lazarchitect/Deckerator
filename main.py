from flask import Flask, render_template

site = Flask(__name__)

@site.route('/')
def main():
	return render_template("splash.html")

@site.route("/login")
def loginPage():
	return render_template("login.html")

@site.route("/loginprocess.php", methods = ['POST'])
def loginProcess():
	return render_template("loginprocess.php")

@site.route('/signup')
def signupPage():
	return "sdfsdf"

@site.route('/homepage.php')
def homepage():
	return "Welcome to the site!"

@site.route('/loginfail')
def loginfail():
	return render_template("loginfail.html")