Deckerator is a web site for generating Magic: The Gathering playing card game decks. Users can create accounts to then build decks and share with friends and discuss the game.

Technical Stuff:
A user can have one account per valid email. Each account can have any number of decks. User accounts and decks are stored in a MySQL database. A deck can be modified while preserving its spot in the database. 


Main.py is where all the python is, that maintains the site links. When a user wants to access a page, a python function for the relevant page is called. After the page is prepared with all the relevant information, an HTML document (or 'template') is rendered for the user. Data can passed in as keyword arguments and accessed from the client side with Jinja2. Some pages are simply for processing user requests, and then redirect sfterwards.
