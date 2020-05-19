import unittest
from api import CharField, ArgumentsField, EmailField, PhoneField, DateField, BirthDayField, GenderField, ClientIDsField
import datetime as dt
from utils import cases


class TestCharField(unittest.TestCase):

    @cases(["Whoops", "", u"123"])
    def test_valid_value(self, value):
        self.assertEqual(value, CharField().parse(value), msg="Value {0} throws error".format(value))

    @cases([0, None])
    def test_invalid_value(self, value):
        with self.assertRaises(ValueError):
            CharField().parse(value)


class TestArgumentsField(unittest.TestCase):

    @cases([{'test': 1}, dict()])
    def test_valid_value(self, value):
        self.assertEqual(value, ArgumentsField().parse(value))

    @cases([0, None])
    def test_invalid_value(self, value):
        with self.assertRaises(ValueError):
            ArgumentsField().parse(value)


class TestEmailField(unittest.TestCase):

    @cases(['user@example.com', "10lol@mail.sdi", "email@me.ru", "45@43.com"])
    def test_valid_email(self, value):
        self.assertEqual(value, EmailField().parse(value))

    @cases(['user', '', None, 123, '@', '@mail.ru', 'user@', '&@$@.#3$', 'user@@mail.ru'])
    def test_invalid_email(self, value):
        with self.assertRaises(ValueError):
            EmailField().parse(value)


class TestPhoneField(unittest.TestCase):

    @cases(['79991234567', 79991234567])
    def test_valid_phone_number(self, value):
        self.assertEqual(str(value), PhoneField().parse(str(value)))

    @cases([None, '', '+129384958212', '9991234567', 123456, '7abcdefghij'])
    def test_invalid_phone_number(self, value):
        with self.assertRaises(ValueError):
            PhoneField().parse(value)


class TestDateField(unittest.TestCase):

    @cases(['21.09.2018', '02.01.2001'])
    def test_valid_value(self, value):
        self.assertIsInstance(DateField().parse(value), dt.date)

    @cases([21092018,'12.03.19290', 123, "ier"])
    def test_invalid_value(self, value):
        with self.assertRaises(ValueError):
            DateField().parse(value)


class TestBirthDayField(unittest.TestCase):

    @cases(['12.03.1990'])
    def test_valid_date(self, value):
        self.assertIsNotNone(BirthDayField().parse(value))
        self.assertEqual(BirthDayField().parse(value).strftime('%d.%m.%Y'), value)

    @cases([dt.datetime.today().date()])
    def test_invalid_date(self, value):
        max_days = 365.25 * 71
        value = value - dt.timedelta(max_days)
        value = value.strftime('%d.%m.%Y')
        with self.assertRaises(ValueError):
            BirthDayField().parse(value)


class TestGenderField(unittest.TestCase):

    @cases([0, 1, 2])
    def test_valid_value(self, value):
        self.assertEqual(value, GenderField().parse(value))

    @cases(['0'])
    def test_invalid_value(self, value):
        with self.assertRaises(ValueError):
            GenderField().parse(value)


class TestClientIDsField(unittest.TestCase):

    @cases([[0, 1, 2]])
    def test_valid_value(self, value):
        self.assertEqual(value, ClientIDsField().parse(value))

    @cases([None, "123"])
    def test_invalid_value(self, value):
        with self.assertRaises(ValueError):
            ClientIDsField().parse(value)


if __name__ == "__main__":
    unittest.main()
