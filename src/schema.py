from datetime import datetime
from dateutil import parser

from graphene import Boolean, Field, Int, List, ObjectType, String
from graphene.types.datetime import Date
import pytz
import requests

from src.constants import *
from src.types import (
    AccountInfoType,
    EateryType,
    TransactionType,
)

class Data(object):
  eateries = {}

  @staticmethod
  def update_data(eateries):
    Data.eateries = eateries

class Query(ObjectType):
  eateries = List(
      EateryType,
      eatery_id=Int(name='id'),
      date=Date(),
      eatery_name=String(name='name'),
      campus_area=String(name='area'),
      is_open=Boolean()
  )
  account_info = Field(
      AccountInfoType,
      date=Date(),
      session_id=String(name='id')
  )

  def resolve_eateries(self, info, eatery_id=None):
    if eatery_id is None:
      return [eatery for eatery in Data.eateries.values()]
    eatery = Data.eateries.get(eatery_id)
    return [eatery] if eatery is not None else []

  def resolve_account_info(self, info, session_id=None):
    if session_id is None:
      return "Provide a valid session ID!"

    account_info = {}

    # Query 1: Get user id
    user_id = requests.post(
        GET_URL + '/user',
        json={
            'version': '1',
            'method': 'retrieve',
            'params': {
                'sessionId': session_id
            }
        }
    ).json()['response']['id']

    # Query 2: Get finance info
    accounts = requests.post(
        GET_URL + '/commerce',
        json={
            'version': '1',
            'method': 'retrieveAccountsByUser',
            'params': {
                'sessionId': session_id,
                'userId': user_id
            }
        }
    ).json()['response']['accounts']

    account_info['laundry'] = "0.00"  # initialize default
    for acct in accounts:
      if acct['accountDisplayName'] == ACCOUNT_NAMES['citybucks']:
        account_info['city_bucks'] = str("{0:.2f}".format(round(acct['balance'], 2)))
      elif acct['accountDisplayName'] == ACCOUNT_NAMES['laundry']:
        account_info['laundry'] = str("{0:.2f}".format(round(acct['balance'], 2)))
      elif acct['accountDisplayName'] == ACCOUNT_NAMES['brbs']:
        account_info['brbs'] = str("{0:.2f}".format(round(acct['balance'], 2)))
      # Need more research to implement swipes:
      # Each plan has a different accountDisplayName
      account_info['swipes'] = ''

    # Query 3: Get list of transactions
    CORNELL_INSTITUTION_ID = '73116ae4-22ad-4c71-8ffd-11ba015407b1'
    transactions = requests.post(
        GET_URL + '/commerce',
        json={
            'method': 'retrieveTransactionHistory',
            'params': {
                'paymentSystemType': 0,
                'queryCriteria': {
                    'accountId': None,
                    'endDate': str(datetime.now().date()),
                    'institutionId': CORNELL_INSTITUTION_ID,
                    'maxReturn': 100,
                    'startingReturnRow': None,
                    'userId': user_id
                },
                'sessionId': session_id
            },
            'version': '1'
        }
    ).json()['response']['transactions']

    account_info['history'] = []

    for t in transactions:
      dt_utc = parser.parse(t['actualDate']).astimezone(pytz.timezone('UTC'))
      dt_est = dt_utc.astimezone(pytz.timezone('US/Eastern'))
      new_transaction = {
          'name': t['locationName'],
          'timestamp': dt_est.strftime("%D at %I:%M %p")
      }
      account_info['history'].append(TransactionType(**new_transaction))

    return AccountInfoType(**account_info)
