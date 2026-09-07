from enum import Enum


class ConfirmationTokenType(str, Enum):
    ACCOUNT_ACTIVATION = "ACCOUNT_ACTIVATION"
    PASSWORD_RESET = "PASSWORD_RESET"
