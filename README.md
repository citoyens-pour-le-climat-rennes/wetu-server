# --- CommeUnDessein --- #

CommeUnDessein is a collaborative app.

# development

Requirements:

virtualenv CommeUnDesseinProject

pip install ...

 - Django==1.9.13
 - django-allauth
 - django-paypal
 - gevent-socketio
 - mongoengine


## Fix gevent-socketio

gevent-socketio is a bit out-of-date:

Replace

from django.utils.importlib import import_module

by



or 

from importlib import import_module

in

lib/python2.7/site-packages/socketio/sdjango.py (line 6)


## Migrate

`python manage.py migrate`


## Creating an admin user

`python manage.py createsuperuser`

## Create site

If the site does not exists, you will have the following error: `Site matching query does not exist`

in python shell:

`python manage.py shell`


`from django.contrib.sites.models import Site`

`new_site = Site.objects.create(domain='localhost:8000', name='localhost:8000')`
`print new_site.id`

Now set that site ID in your settings.py to SITE_ID

http://stackoverflow.com/questions/11814059/site-matching-query-does-not-exist


## Client:

Copy comme-un-dessein-client in `comme-un-dessein-server/CommeUnDessein/static/`

`git clone https://github.com/arthursw/comme-un-dessein-client.git`

beside CommeUnDessein root directory

## Collect static files

`python manage.py collectstatic`

This will move django admin static files AND comme-un-dessein static files into comme-un-dessein-server/CommeUnDessein/CommeUnDessein/static/

## Add social apps

Add Github, Facebook, Google keys at http://comme-un-dessein.space/admin/socialaccount/socialapp/

Update IDs:

https://console.developers.google.com/
