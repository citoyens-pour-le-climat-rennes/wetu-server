import sys
import os
import json

with open("/data/settings.json", "w") as outfile:
    json.dump({'DEBUG':True, 'SITE_ID': 4, 'ACCOUNT_EMAIL_REQUIRED': False, 'ACCOUNT_EMAIL_VERIFICATION':'none', 'EMAIL_HOST_PASSWORD': 'PASSWORD', 'ALLOWED_HOSTS':[], 'EMAIL_BACKEND': 'django.core.mail.backends.console.EmailBackend'}, outfile, indent=4)