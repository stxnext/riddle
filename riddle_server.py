"""
Riddle server.

Start:
uwsgi --http 0.0.0.0:1337 --wsgi-file riddle_server.py \
      --master-fifo uwsgi_ctl --daemonize uwsgi.log

Stop:
echo 'q' > uwsgi_ctl
"""

import hashlib
import logging
import random
import string

from riddle_config import LENGTHS, DIGESTS


log = logging.getLogger('riddle')
log.setLevel(logging.DEBUG)
handler = logging.FileHandler('riddle.log')
formatter = logging.Formatter("%(asctime)s %(message)s")
handler.setFormatter(formatter)
log.addHandler(handler)


def get_digest(text):
    """Calculate digest from string."""
    return hashlib.sha256(text).hexdigest()


def get_client_address(environ):
    """Find client IP even if server is behind proxy."""
    try:
        return environ['HTTP_X_FORWARDED_FOR'].split(',')[-1].strip()
    except KeyError:
        return environ['REMOTE_ADDR']


def check_payload(payload):
    """Check every line in payload."""
    warnings = []
    for i, line in enumerate(payload):
        if len(line) < LENGTHS[i]:
            warnings.append('Line {} is too short.'.format(i+1))
        elif len(line) > LENGTHS[i]:
            warnings.append('Line {} is too long.'.format(i+1))
        elif get_digest(line) != DIGESTS[i]:
            warnings.append('Line {} have to be changed.'.format(i+1))

    return warnings


def application(environ, start_response):
    """Main WSGI application."""
    try:
        status = '200 OK'
        if environ['REQUEST_METHOD'] != 'PUT':
            output = 'You should *PUT* valid source code here!'
        elif environ['REQUEST_URI'] != 'here':
            output = 'You should PUT valid source code *here*!'
        elif environ.get('wsgi.input') is None:
            output = 'You should PUT valid source *code* here!'
        else:
            payload = environ['wsgi.input'].read().strip().splitlines()
            output = [
                'You should PUT *valid source code* here!\n',
                'Extract and prettify code from ASCII-art, '
                'make it pass pep8 and pylint, remove empty lines, '
                'send it as a PUT payload and follow the next instructions!\n',
            ]

            if len(payload) != len(LENGTHS):
                output.append(
                    'Payload should have {} lines.'.format(len(LENGTHS)+1)
                )
            else:
                warnings = check_payload(payload)
                addr = get_client_address(environ)
                if not warnings:
                    code = list(string.letters)
                    random.shuffle(code)
                    code = ''.join(code)
                    log.info('Winner! %s (IP: %s)', code, addr)
                    output = [
                        'Send {} to email-addr.pl to get reward!'.format(code)
                    ]
                else:
                    output.extend(warnings)
                    log.info(
                        'User %s have to fix %s lines', addr, len(warnings)
                    )

            output = '\n'.join(output).strip()

    except Exception:
        log.exception('Unexpected error!')
        status = '500 INTERNAL SERVER ERROR'
        output = 'Unexpected error!'

    response_headers = [
        ('Content-type', 'text/plain'),
        ('Content-Length', str(len(output))),
    ]
    start_response(status, response_headers)
    return [output]
