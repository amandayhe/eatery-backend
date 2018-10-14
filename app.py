# copy pasted from uplift-backend, might just keep it like this for now
from flask import Flask
from flask_graphql import GraphQLView
from graphene import Schema
import data
from schema import Query
from werkzeug.debug import DebuggedApplication

app = Flask(__name__)

schema = Schema(query=Query)

app.add_url_rule(
  '/',
  view_func=GraphQLView.as_view(
    'graphql',
    schema=schema,
    graphiql=True
    )
  )

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)
