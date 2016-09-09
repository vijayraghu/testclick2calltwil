import unittest
import json
from mock import Mock
from mock import patch

from twilio.exceptions import TwilioException

from .context import app

app.config['TWILIO_ACCOUNT_SID'] = 'ACxxxxxx'
app.config['TWILIO_AUTH_TOKEN'] = 'yyyyyyyyy'
app.config['TWILIO_CALLER_ID'] = '+15558675309'

BASE_URI = "https://api.twilio.com/2010-04-01/Accounts/" \
           "{0}".format(app.config['TWILIO_ACCOUNT_SID'])
AUTH = (app.config['TWILIO_ACCOUNT_SID'], app.config['TWILIO_AUTH_TOKEN'])


class TwiMLTest(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def assertTwiML(self, response):
        app.logger.info(response.data)
        self.assertTrue(b"</Response>" in response.data, "Did not find "
                        "</Response>: {0}".format(response.data))
        self.assertEqual("200 OK", response.status)

    def sms(self, body, url='/sms', to=app.config['TWILIO_CALLER_ID'],
            from_='+15558675309', extra_params=None):
        params = {
            'SmsSid': 'SMtesting',
            'AccountSid': app.config['TWILIO_ACCOUNT_SID'],
            'To': to,
            'From': from_,
            'Body': body,
            'FromCity': 'BROOKLYN',
            'FromState': 'NY',
            'FromCountry': 'US',
            'FromZip': '55555'}
        if extra_params:
            params = dict(params.items() + extra_params.items())
        return self.app.post(url, data=params)

    def call(self, url='/voice', to=app.config['TWILIO_CALLER_ID'],
             from_='+15558675309', digits=None, extra_params=None):
        params = {
            'CallSid': 'CAtesting',
            'AccountSid': app.config['TWILIO_ACCOUNT_SID'],
            'To': to,
            'From': from_,
            'CallStatus': 'ringing',
            'Direction': 'inbound',
            'FromCity': 'BROOKLYN',
            'FromState': 'NY',
            'FromCountry': 'US',
            'FromZip': '55555'}
        if digits:
            params['Digits'] = digits
        if extra_params:
            params = dict(params.items() + extra_params.items())
        return self.app.post(url, data=params)


class ClickToCallTests(TwiMLTest):
    def test_index(self):
        response = self.app.get('/')
        self.assertEquals("200 OK", response.status)

    def test_outbound(self):
        response = self.call(url='/outbound')
        self.assertTwiML(response)

    @patch("twilio.rest.resources.base.make_request")
    def test_call(self, mock):
        expected_params = {'From': app.config['TWILIO_CALLER_ID'],
                           'To': '+15556667777',
                           'Url': 'http://localhost/outbound'}

        api_response = Mock()
        api_response.content = json.dumps(expected_params)
        api_response.status_code = 201
        mock.return_value = api_response

        response = self.app.post('/call',
                                 data={'phoneNumber': '+15556667777'})

        self.assertEquals("200 OK", response.status)

        self.assertTrue(mock.called, "Call was not made: "
                        "{0}".format(response.data))
        self.assertEquals(expected_params, mock.call_args[1]['data'],
                          "Did not get expected parameters: "
                          "{0}".format(mock.call_args))

    @patch("twilio.rest.resources.base.make_request")
    def test_call_error_handling(self, mock):
        mock.return_value = Mock()

        def raiseException(*args, **kwargs):
            raise TwilioException("Test error.")

        mock.side_effect = raiseException

        response = self.app.post('/call',
                                 data={'phoneNumber': '+15556667777'})

        self.assertEquals("200 OK", response.status)
        self.assertTrue(b"Test error" in response.data, "Could not "
                        "find error passed through to JSON result: "
                        "{0}".format(response.data))


class NoCredentialsTests(unittest.TestCase):
    def setUp(self):
        del(app.config['TWILIO_ACCOUNT_SID'])
        self.app = app.test_client()

    def test_call_without_twilio_credentials(self):
        response = self.app.post('/call',
                                 data={'phoneNumber': '+15556667777'})

        self.assertEquals("200 OK", response.status)
        self.assertTrue(b"Missing" in response.data, "Could not "
                        "find error for missing Twilio credentials: "
                        "{0}".format(response.data))
