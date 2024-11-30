import json
import requests
from urllib.error import HTTPError

from django.conf import settings

try:
    import sendgrid
except ImportError:
    sendgrid = None


class MailError(Exception):
    pass


def sendgrid_core_send(data):
    '''data can be a sendgrid.Mail object or a dict'''
    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_KEY)
    try:
        if isinstance(data, sendgrid.Mail):
            response = sg.send(data)
        else:
            response = sg.client.mail.send.post(request_body=data)
    except (HTTPError) as e:
        raise MailError('HTTPError: {}'.format(e.body))
    except Exception as e:
        raise MailError('Unknown Exception: {}'.format(e))

    if response.status_code % 100 != 2:  # not 2xx
        raise MailError("status={}, body={}".format(
            response.status_code, response.body))
    return response


def sendgrid_send(subject,
                  message,
                  from_email,
                  to_emails,
                  from_email_name="ReliScore Admin",
                  cc_emails=[],
                  bcc_emails=[]):

    # Validations
    to_emails = set(e.lower() for e in to_emails)
    if len(to_emails) + len(cc_emails) + len(bcc_emails) > 990:
        raise MailError('Too many to_emails: {}. Break into chunks'.format(
            len(to_emails)))
    for e in cc_emails + bcc_emails:
        if e.lower() in to_emails:
            raise MailError('Email {} in cc/bcc also in to'.format(e))

    data = {
        "personalizations": [
            {
                "to": [{"email": e} for e in set(to_emails)],
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

    return sendgrid_core_send(data)


def sendgrid_send_template(template_id,
                           contexts,
                           common_context, 
                           from_email=settings.DEFAULT_REGISTRATIONS_FROM_EMAIL,
                           from_email_name="ReliScore Registrations (do not reply)"):
    '''
    contexts is a list [[email, specific_context]] where specific_context is a dict
    common_context is context to be added to all of them
    
    So:
    contexts = [['navin@smriti.com', {'username': 'ngkabra'}], ['t@example.com', {'username': 'testuser1'}]]
    common_context = {'company_name': 'ReliScore', 'test_name': 'Software Engineer'}
    '''
    if len(contexts) > 990:
        raise MailError('Too many emails: {}. Break into chunks'.format(
            len(contexts)))
    
    personalizations = [
        {"to": [{"email": email}],
         "dynamic_template_data": {**specific_context, **common_context}}
         for email, specific_context in contexts]

    to_emails = [
        sendgrid.To(email=email,
                    dynamic_template_data={**specific_context, **common_context})
        for email, specific_context in contexts
    ]
    
    message = sendgrid.Mail(
        from_email=(from_email, from_email_name),
        to_emails=to_emails,
        subject="Generic Subject",
        is_multiple=True,
    )
    message.template_id = template_id
    
    return sendgrid_core_send(message)
    

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
