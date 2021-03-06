import json
from datetime import datetime
from msg_handler import logger
import requests
from msg_handler.models import Query, Response
from msg_handler import db
from msg_handler import app

ACCESS_TOKEN = app.config['ACCESS_TOKEN']
ACCOUNT_KEY = app.config['ACCOUNT_KEY']

class VumiMessage():
    # TODO: Use separate classes for USSD & SMS, and have them inherit from this class

    def __init__(self, msg_dict):
        # TODO: init an empy object, and populate it in separate methods
        if msg_dict.get('query_id'):
            try:
                qry = Query.query.get(msg_dict['query_id'])
                self.query_id = qry.query_id
                self.message_id = qry.vumi_message_id
                self.msg_type = "sms"
                self.content = qry.content
                self.conversation_key = qry.conversation_key
                self.from_addr = qry.from_addr
                self.timestamp = datetime.strftime(self.datetime, '%Y-%m-%d %H:%M:%S.%f')
                self.datetime = qry.datetime
            except Exception:
                logger.exception("Could not load specified Query record.")
        else:
            try:
                if msg_dict.get('message_id'):
                    self.message_id = msg_dict['message_id']
                if msg_dict.get('transport_type'):
                    self.msg_type = msg_dict['transport_type']  # either 'ussd' or 'sms'
                if msg_dict.get('content'):
                    self.content = msg_dict['content']
                else:
                    self.content = None
                if msg_dict.get('helper_metadata'):
                    self.conversation_key = msg_dict['helper_metadata']['go']['conversation_key']
                else:
                    self.conversation_key = app.config['CONVERSATION_KEY']
                if msg_dict.get('from_addr'):
                    self.from_addr = msg_dict['from_addr']
                if msg_dict.get('timestamp'):
                    self.timestamp = msg_dict['timestamp']  # e.g. "2013-12-02 06:28:07.430549"
                    self.datetime = datetime.strptime(self.timestamp, '%Y-%m-%d %H:%M:%S.%f')
            except Exception as e:
                logger.exception("Could not create VumiMessage instance.")
                raise
        return

    def send(self, to_addr):

        conversation_key = self.conversation_key
        message_url = 'http://go.vumi.org/api/v1/go/http_api/' + conversation_key + '/messages.json'
        payload = {
            "to_addr": to_addr,
            "content": self.content,
            }
        if not app.debug:
            r = requests.put(message_url, auth=(ACCOUNT_KEY, ACCESS_TOKEN),
                         data=json.dumps(payload))
            logger.debug(message_url)
            logger.debug("Status Code: " + str(r.status_code))
            try:
                tmp = json.loads(r.text)
                logger.debug(json.dumps(tmp, indent=4))
            except Exception:
                logger.debug(r.text)
                pass
            if not r.status_code == 200:
                logger.error("HTTP error encountered while trying to send message through VumiGo API.")
            return r.text
        else:
            logger.debug("MESSAGE SENT \n" + json.dumps(payload, indent=4))
            return

    def send_reply(self, content, session_event="resume", user=None):
        conversation_key = self.conversation_key
        message_url = 'http://go.vumi.org/api/v1/go/http_api/' + conversation_key + '/messages.json'
        payload = {
            "in_reply_to": self.message_id,
            "content": content,
            "session_event": session_event,
            }

        # log response to db if this is a reply to an SMS query
        if hasattr(self, 'query_id'):
            rsp = Response()
            rsp.query_id = self.query_id
            rsp.content = content
            if user:
                rsp.user = user
            db.session.add(rsp)
            db.session.commit()

        if not app.debug:
            r = requests.put(message_url, auth=(ACCOUNT_KEY, ACCESS_TOKEN),
                         data=json.dumps(payload))
            logger.debug("Response Status Code: " + str(r.status_code))
            try:
                tmp = json.loads(r.text)
                logger.debug(json.dumps(tmp, indent=4))
            except Exception:
                logger.debug(r.text)
                pass
            if not r.status_code == 200:
                logger.error("HTTP error encountered while trying to send message through VumiGo API.")
            return r.text
        else:
            logger.debug("REPLY \n" + json.dumps(payload, indent=4))
            return

    def save_query(self):

        qry = Query.query.filter(Query.vumi_message_id == self.message_id).first()
        if qry is None:
            qry = Query()
        qry.vumi_message_id = self.message_id
        qry.content = self.content
        qry.conversation_key = self.conversation_key
        qry.from_addr = self.from_addr
        qry.timestamp = self.timestamp
        qry.datetime = self.datetime
        db.session.add(qry)
        db.session.commit()
        self.query_id = qry.query_id
        return

    def __repr__(self):
        # TODO: ensure these variables have been instantiated
        tmp = {
            'msg_type': self.msg_type,
            'content': self.content,
            'message_id': self.message_id,
            'conversation_key': self.conversation_key,
            'from_addr': self.from_addr,
            'timestamp': self.timestamp,
        }
        return json.dumps(tmp, indent=4)