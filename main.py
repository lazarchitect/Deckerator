from flask import Flask, render_template

site = Flask(__name__)

@site.route('/')
def main():
	return render_template("splash.html")

@site.route('/login')
def loginPage():
	return render_template("login.html")

@site.route('/signup')
def signupPage():
	return render_template("signup.html")

@site.route('/homepage')
def homepage():
	return "Welcome to the site!"