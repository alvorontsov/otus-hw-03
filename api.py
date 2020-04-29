#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import random
import json
from datetime import datetime
import logging
import hashlib
import uuid
from optparse import OptionParser
from abc import abstractmethod, ABCMeta
from store import RedisStorage, Storage
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}
AGE_LIMIT = 70

class BaseField(object):
    """
    This is a base class for all fields
    """
    __metaclass__ = ABCMeta

    def __init__(self, required=False, nullable=False):
        self.required = required
        self.nullable = nullable

    @abstractmethod
    def parse(self, value):
        """
        A base method to call for each subclass. Returns parsed value or throws error
        :param value: input str
        :return: parsed value
        """
        pass


class CharField(BaseField):

    def parse(self, value):
        if not isinstance(value, (str, unicode)):
            raise ValueError('Expected str value the for field')
        return value


class ArgumentsField(BaseField):

    def parse(self, value):
        if not isinstance(value, dict):
            raise ValueError('Expected dict value for the field')
        return value


class EmailField(CharField):

    def parse(self, value):
        if not re.match(r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)', str(value)):
            raise ValueError('Email validation failed')
        return value


class PhoneField(BaseField):

    def parse(self, value):
        if not re.match(r'(^7[\d]{10}$)', str(value)):
            raise ValueError('Phone number validation failed')
        return value


class DateField(BaseField):

    def parse(self, value):
        try:
            value = datetime.strptime(value, '%d.%m.%Y')
        except Exception:
            raise ValueError('Date validation failed')
        return value


class BirthDayField(DateField):

    def parse(self, value):
        value = super(BirthDayField, self).parse(value)
        current = datetime.now()
        if current.year - value.year > AGE_LIMIT:
            raise ValueError('Age limit validation failed. Maximum value is {} years.'.format(AGE_LIMIT))
        return value


class GenderField(BaseField):

    def parse(self, value):
        if value not in [UNKNOWN, MALE, FEMALE]:
            raise ValueError('Gender validation failed. Expected values: {}, {}, {} .'.format(UNKNOWN, MALE, FEMALE))
        return value


class ClientIDsField(BaseField):

    def parse(self, value):
        if not isinstance(value, list):
            raise ValueError('Expected list value for the field.')
        if not all(isinstance(item, int) for item in value):
            raise ValueError('Expected int values.')
        return value


class BaseMetaRequest(type):
    """Metaclass for request"""

    def __init__(cls, name, bases, attr_dict):
        super(BaseMetaRequest, cls).__init__(name, bases, attr_dict)
        cls.fields = []
        for key, attr in attr_dict.items():
            if isinstance(attr, BaseField):
                attr.name = key
                cls.fields.append(attr)


class BaseRequest(object):
    """Base class for request"""
    __metaclass__ = BaseMetaRequest

    empty_values = (None, '', [], {}, ())

    def __init__(self, request):
        self._errors = []
        self._has_errors = True
        self.request = request

    def clean(self):
        for field in self.fields:
            value = None
            try:
                value = self.request[field.name]
            except (KeyError, TypeError):
                if field.required:
                    self._errors.append(self.error_str(field, 'Field is required.'))
                    continue
            if value in self.empty_values and not field.nullable:
                self._errors.append(self.error_str(field, 'Field not be nullable.'))
            try:
                if value not in self.empty_values:
                    value = field.parse(value)
                    setattr(self, field.name, value)
            except ValueError as e:
                self._errors.append(self.error_str(field, e))
        return self._errors

    def is_valid(self):
        if self._has_errors:
            self._has_errors = not self.clean()
        return self._has_errors

    def error_message(self):
        return ', '.join(self._errors)

    def get_not_empty_fields(self):
        fields = []
        for field in self.fields:
            if field.name in self.request not in self.empty_values:
                fields.append(field.name)
        return fields

    @staticmethod
    def error_str(field, message):
        return '{}: {}'.format(field.name, message)


class ClientsInterestsBaseRequest(BaseRequest):
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreBaseRequest(BaseRequest):
    _pairs = (
        ('phone', 'email'),
        ('first_name', 'last_name'),
        ('gender', 'birthday'),
    )

    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def clean(self):
        self._errors = super(OnlineScoreBaseRequest, self).clean()
        not_empty_fields = set(self.get_not_empty_fields())
        result = any([not_empty_fields.issuperset(pair) for pair in self._pairs])
        if not result:
            self._errors.append('Pairs {} should be not empty'.format(' or '.join(str(pair) for pair in self._pairs)))
        return self._errors


class MethodBaseRequest(BaseRequest):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class AbstractRequestHandler(object):
    __metaclass__ = ABCMeta

    def __init__(self, request, ctx):
        self.request = request
        self.ctx = ctx

    @abstractmethod
    def init_request(self, data):
        """ Create request entity here """

    @abstractmethod
    def processing_handler(self, request_type):
        """ Logic of processing the request """

    def run_processing(self, data):
        request_type = self.init_request(data)
        if not request_type.is_valid():
            return request_type.error_message(), INVALID_REQUEST
        return self.processing_handler(request_type)


class OnlineScoreRequestHandler(AbstractRequestHandler):
    def init_request(self, data):
        return OnlineScoreBaseRequest(data)

    def processing_handler(self, request_type):
        self.ctx['has'] = request_type.get_not_empty_fields()
        if self.request.is_admin:
            return {'score': 42}, OK
        return {'score': random.randrange(0, 100)}, OK


class ClientsInterestsRequestHandler(AbstractRequestHandler):
    def init_request(self, data):
        return ClientsInterestsBaseRequest(data)

    def processing_handler(self, request_type):
        interests = {'books', 'hi-tech', 'pets', 'tv', 'travel', 'music', 'cinema', 'geek'}
        response = {i: random.sample(interests, 2) for i in request_type.client_ids}
        self.ctx['nclients'] = len(request_type.client_ids)
        return response, OK


def check_auth(request):
    if request.login == ADMIN_LOGIN:
        digest = hashlib.sha512(datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, settings):
    handlers = {
        'online_score': OnlineScoreRequestHandler,
        'clients_interests': ClientsInterestsRequestHandler
    }

    request = MethodBaseRequest(request['body'])

    if not request.is_valid():
        return request.error_message(), INVALID_REQUEST

    if not check_auth(request):
        return None, FORBIDDEN

    if not isinstance(request.arguments, dict):
        return 'Method arguments must be a dictionary', INVALID_REQUEST

    if request.method not in handlers:
        return None, NOT_FOUND

    return handlers[request.method](request, ctx).run_processing(request.arguments)


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
    }
    store = Storage(RedisStorage())

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception, e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
