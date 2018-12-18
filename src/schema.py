from datetime import datetime
from dateutil import parser

from graphene import Field, Int, List, ObjectType, String
from graphene.types.datetime import Date
import pytz
import requests

from src.constants import (
    ACCOUNT_NAMES,
    CORNELL_INSTITUTION_ID,
    GET_URL,
)
from src.types import (
    AccountInfoType,
    CampusEateryType,
    CollegetownEateryType,
    TransactionType,
)

class Data(object):
  campus_eateries = {}
  collegetown_eateries = {}

  @staticmethod
  def update_data(campus_eateries):
    Data.campus_eateries = campus_eateries

  @staticmethod
  def update_collegetown_data(collegetown_eateries):
    Data.collegetown_eateries = collegetown_eateries


class Query(ObjectType):
  account_info = Field(
      AccountInfoType,
      date=Date(),
      session_id=String(name='id'),
  )
  campus_eateries = List(
      CampusEateryType,
      eatery_id=Int(name='id'),
  )
  collegetown_eateries = List(
      CollegetownEateryType,
      eatery_id=Int(name='id'),
  )
  eateries = List(
      CampusEateryType,
      eatery_id=Int(name='id'),
  )

  def get_eateries(eateries, eatery_id):
    if eatery_id is None:
      return list(eateries.values())
    eatery = eateries.get(eatery_id)
    return [eatery] if eatery is not None else []

  def resolve_campus_eateries(self, info, eatery_id=None):
    return Query.get_eateries(Data.campus_eateries, eatery_id)

  def resolve_collegetown_eateries(self, info, eatery_id=None):
    return Query.get_eateries(Data.collegetown_eateries, eatery_id)

  def resolve_eateries(self, info, eatery_id=None):
    return Query.get_eateries(Data.campus_eateries, eatery_id)

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

    # intialize default values
    account_info['brbs'] = '0.00'
    account_info['city_bucks'] = '0.00'
    account_info['laundry'] = '0.00'
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