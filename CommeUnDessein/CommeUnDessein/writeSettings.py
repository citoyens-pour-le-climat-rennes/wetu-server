import sys
import os
import json

with open("/data/settings.json", "w") as outfile:
    json.dump({'DEBUG':True, 'ACCOUNT_EMAIL_REQUIRED': False, 'ACCOUNT_EMAIL_VERIFICATION':'none', 'EMAIL_HOST_PASSWORD': 'PASSWORD', 'ALLOWED_HOSTS':[]}, outfile, indent=4)