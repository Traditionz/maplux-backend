class InvalidConfirmationTokenException(Exception):
    pass


class SendEmailException(Exception):
    pass


SendActivationEmailException = SendEmailException
