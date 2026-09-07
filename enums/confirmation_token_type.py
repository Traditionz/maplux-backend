from enum import StrEnum


class ConfirmationTokenType(StrEnum):
    ACCOUNT_ACTIVATION = "ACCOUNT_ACTIVATION"
    PASSWORD_RESET = "PASSWORD_RESET"
