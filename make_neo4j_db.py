import pandas as pd
from pandas import DataFrame
import numpy as np
from neo4j import GraphDatabase
from metapub import PubMedFetcher
import os.path

class Neo4jConnection:

    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)

    def close(self):
        if self.__driver is not None:
            self.__driver.close()

    def query(self, query, db=None):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.__driver.session(database=db) if db is not None else self.__driver.session()
            response = list(session.run(query))
        except Exception as e:
            print("Query failed:", e)
        finally:
            if session is not None:
                session.close()
        return response

# connect to the NEO4J database you have running
# localhost:11003 may change depending on your database
# user/password are the default neo4j values
conn = Neo4jConnection(uri="bolt://localhost:11003", user="neo4j", pwd="password")

# CAUTION: this will delete anythin in the database 'chem' if it already exists
conn.query("CREATE OR REPLACE DATABASE chem")

# read in chebi relations
chebi = pd.read_csv('relations.csv')

# format pubmed column
chebi['Pubmed'] = chebi['Pubmed'].replace(".txt","",regex=True)
chebi['citation'] = None

# make a copy of the pubmed ids, get unique values
pmids = chebi['Pubmed'].copy()
pmids = pmids.unique()

# make the pubmed id into a link
chebi['Pubmed_link'] = chebi['Pubmed'].apply(lambda x: "{}{}".format('https://pubmed.ncbi.nlm.nih.gov/', x))


def make_citation(article):
    n_authors = len(article.authors)
    year = article.year
    if n_authors == 1 or n_authors > 2:
        last_name = article.author1_last_fm
        last_name = last_name[:last_name.rindex(' ')]
        if n_authors > 2:
            last_name = last_name + ' et al.'
    else:
        last_name_0 = article.authors[0]
        last_name_1 = article.authors[1]

        last_name = last_name_0[:last_name_0.rindex(' ')] + " & " + last_name_1[:last_name_1.rindex(' ')]

    citation = "(" + last_name + ", " + year + ")"
    return(citation)

if os.path.exists('relations_citations.csv'):
    chebi = pd.read_csv('relations_citations.csv')
else:
    # add citation info for each associated publication
    fetch = PubMedFetcher()
    for pmid in pmids:
        article = fetch.article_by_pmid(pmid)
        citation = make_citation(article)
        chebi['citation'][chebi.Pubmed == pmid] = citation


# format realtionship
chebi['Relationship'] = chebi['Relationship'].str.upper()

# get list of unique entites
arg1 = chebi['Arg1']
arg2 = chebi['Arg2']
arg1 = (arg1.unique())
arg2 = (arg2.unique())
args = arg1.tolist() + arg2.tolist()
args = np.unique(np.array(args))

# create a neo4j node for each entity
for i in range(len(args)):

    if args[i] in arg1.tolist():
        # add in the entity 'type' e.g. Species, Metabolite, etc.
        arg_type = chebi[chebi['Arg1']==args[i]]['Arg1_type'].iloc[0].strip()
    elif args[i] in arg2.tolist():
        arg_type = chebi[chebi['Arg2']==args[i]]['Arg2_type'].iloc[0].strip()

    q_string = 'CREATE (:ARG1 {ID:"%s", type:"%s"})' % (args[i], arg_type)
    conn.query(q_string, db='chem')

# create a relationship between nodes
for i in range(len(chebi['Relationship'])):
    query_string = ""
    if (chebi['Relationship'][i] == "ASSOCIATED_WITH" or chebi['Relationship'][i] == "BINDS_WITH" or chebi['Relationship'][i] == "ISOLATED_FROM" or chebi['Relationship'][i] == "METABOLITE_OF"):
        q_string_1 = 'MATCH (a1:ARG1 {ID: "%s"}), (a2:ARG1 {ID: "%s"})' % (chebi['Arg1'][i], chebi['Arg2'][i])
        q_string_2 = 'MERGE (a1)-[:%s {Pubmed: "%s", citation: "%s"}]->(a2)' % (chebi['Relationship'][i], chebi['Pubmed'][i], chebi['citation'][i])
        query_string = q_string_1 + '\n' + q_string_2

        if (chebi['Relationship'][i] == "ASSOCIATED_WITH" or chebi['Relationship'][i] == "BINDS_WITH"):
            q_string_3 = 'MERGE (a2)-[:%s {Pubmed: "%s", citation: "%s"}]->(a1)' % (chebi['Relationship'][i], chebi['Pubmed'][i], chebi['citation'][i])
            query_string = query_string + '\n' + q_string_3
        if (chebi['Relationship'][i] == "ISOLATED_FROM"):
            q_string_4 = 'MERGE (a1)<-[:%s {Pubmed: "%s", citation: "%s"}]-(a2)' % ("PRODUCES", chebi['Pubmed'][i], chebi['citation'][i])
            query_string = query_string + '\n' + q_string_4
        if (chebi['Relationship'][i] == "METABOLITE_OF"):
            q_string_5 = 'MERGE (a1)<-[:%s {Pubmed: "%s", citation: "%s"}]-(a2)' % ("METABOLISES_TO", chebi['Pubmed'][i], chebi['citation'][i])
            query_string = query_string + '\n' + q_string_5

        conn.query(query_string, db='chem')
