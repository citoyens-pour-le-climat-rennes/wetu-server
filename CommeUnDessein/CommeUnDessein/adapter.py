from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError

class AccountAdapterCD(DefaultAccountAdapter):
    def clean_password(self, password, user):
        if len(password) > 2:
            return password
        else:
            raise ValidationError("The password is too short.")