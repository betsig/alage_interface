# Web app for text-mined PubMed chemical relationships

This is a web app build using a Neo4j database, and the flask (python) web framework.

The database is built from text-mined relationships between entities from PubMed abstracts.
To build the database, the initial data and the script make_neo4j_db.py were used. This requires a user to setup Neo4J first, and have a blank database already running before you connect.

To run the web app, use
`python run.py`
which will run the app in debugging mode.

Files are organised in a typical flask project manner
views.py contains all the app.routes
models.py contains all functions
forms.py contains all custom Forms (wtforms) for input

html templates for displaying each page are in templates/
