from py2neo import Graph
def db_auth():
    user = 'neo4j'
    pword = 'password'
    graph = Graph("bolt://localhost:11003/chem/", username=user, password=pword, name='chem')
    return graph
