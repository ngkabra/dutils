import json
import requests
from urllib2 import HTTPError

from django.conf import settings

try:
    import sendgrid
except ImportError:
    sendgrid = None


class MailError(Exception):
    pass


def sendgrid_send(subject,
                  message,
                  from_email,
                  to_emails,
                  from_email_name="RSphinx Admin",
                  cc_emails=[],
                  bcc_emails=[]):

    sg = sendgrid.SendGridAPIClient(apikey=settings.SENDGRID_KEY)
    data = {
        "personalizations": [
            {
                "to": [{"email": e} for e in to_emails],
                "subject": subject,
            }
        ],
        "from": {
            "email": from_email,
            "name": from_email_name
        },
        "content": [
            {
                "type": "text/plain",
                "value": message
            }
        ]
    }

    if cc_emails:
        data['personalizations'][0]['cc'] = [{'email': e} for e in cc_emails]

    if bcc_emails:
        data['personalizations'][0]['bcc'] = [{'email': e} for e in bcc_emails]

    try:
        response = sg.client.mail.send.post(request_body=data)
    except HTTPError as e:
        raise MailError('HTTPError: {}'.format(e.read()))

    if response.status_code % 100 != 2:  # not 2xx
        raise MailError("status={}, body={}".format(
            response.status_code, response.body))


def mandrill_send(subject,
                  message,
                  from_email,
                  to_emails,
                  fail_silently=False):
    if len(to_emails) != 1:
        raise Exception('Cannot send multiple mails via mandrill')

    data = {
        'key': settings.MANDRILL_KEY,
        'message': {
            'text': message,
            'subject': subject,
            'from_email': from_email,
            'to': [
                {
                    'email': to_emails[0],
                    'type': 'to',
                },
            ],
            'headers': {
                'Reply-To': from_email,
            },
        },
    }
    res = requests.post('https://mandrillapp.com/api/1.0/messages/send.json',
                        data=json.dumps(data))
    # ignore errors
    # for now, ignore value of fail_silently