import json
import requests

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
                  fail_silently=False):
    sg = sendgrid.SendGridClient(settings.SENDGRID_KEY, raise_errors=True)
    msg = sendgrid.Mail()
    msg.add_to(to_emails)
    msg.set_subject(subject)
    msg.set_from(from_email)
    msg.set_text(message)

    try:
        status, msg = sg.send(msg)
    except sendgrid.SendGridError:
        if not fail_silently:
            raise MailError('Error sending mail')


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
