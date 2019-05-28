# -*- coding: utf-8 -*-

from binascii import a2b_base64
from threading import Timer, Thread
import datetime
import logging
import os
import shutil
import os.path
import errno
import json
import urllib
import urllib2

# from django.utils import json
# from dajaxice.decorators import dajaxice_register
from django.core import serializers
# from dajaxice.core import dajaxice_functions
from django.contrib.auth.models import User
from django.db.models import F
from django.core.mail import send_mail
from models import *
import ast
from pprint import pprint
from django.contrib.auth import authenticate, login, logout
from paypal.standard.ipn.signals import payment_was_successful, payment_was_flagged, payment_was_refunded, payment_was_reversed
from math import *
import random
import re
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import django.dispatch

from mongoengine import ValidationError
from mongoengine.queryset import Q
import time

from PIL import Image
import cStringIO
import StringIO
import traceback
import requests
from Wetu import settings
from allauth.socialaccount.models import SocialToken
# import collaboration

from allauth.account.signals import email_confirmed, email_confirmation_sent

import base64


# from github3 import authorize

# from wand.image import Image

import functools

debugMode = False
# positiveVoteThreshold = 10
# negativeVoteThreshold = 3
# positiveVoteThresholdTile = 5
# negativeVoteThresholdTile = 3
# voteValidationDelay = datetime.timedelta(minutes=1) 		# once the drawing gets positiveVoteThreshold votes, the duration before the drawing gets validated (the drawing is not immediately validated in case the user wants to cancel its vote)
# voteMinDuration = datetime.timedelta(hours=1)				# the minimum duration the vote will last (to make sure a good moderation happens)
drawingMaxSize = 1000

drawingModes = ['free', 'ortho', 'orthoDiag', 'pixel', 'image']

# drawingValidated = django.dispatch.Signal(providing_args=["drawingId", "status"])
drawingChanged = django.dispatch.Signal(providing_args=["drawingId", "status", "type", "city", "votes", "pk", "title", "description", "svg"])

def userAllowed(request, owner):
	return request.user.username == owner or isAdmin(request.user)

if settings.DEBUG:
	import pdb

	def checkDebug(func):
		@functools.wraps(func)
		def wrapper(*args, **kwargs):
			if debugMode:
				import pdb; pdb.Pdb(skip=['django.*', 'gevent.*']).set_trace()
			return func(*args, **kwargs)
		return wrapper
else:
	def checkDebug(func):
	    return func

def isAdmin(user):
	try:
		profile = UserProfile.objects.get(username=user.username)
		return profile.admin
	except UserProfile.DoesNotExist:
		return False
	return False

logger = logging.getLogger(__name__)

try:
	commeUnDesseinCity = City.objects.get(name='Wetu', owner='WetuOrg', public=True)
except City.DoesNotExist:
	commeUnDesseinCity = City(name='Wetu', owner='WetuOrg', public=True)
	commeUnDesseinCity.save()


logger = logging.getLogger(__name__)

with open('/data/wetu/secret_github.txt') as f:
	PASSWORD = base64.b64decode(f.read().strip())

with open('/data/wetu/secret_tipibot.txt') as f:
	TIPIBOT_PASSWORD = f.read().strip()

with open('/data/wetu/client_secret_github.txt') as f:
	CLIENT_SECRET = f.read().strip()

with open('/data/wetu/accesstoken_github.txt') as f:
	ACCESS_TOKEN = f.read().strip()

with open('/data/wetu/openaccesstoken_github.txt') as f:
	OPEN_ACCESS_TOKEN = f.read().strip()

with open('/data/wetu/settings.json') as f:
    localSettings = json.loads(f.read().strip())

# pprint(vars(object))
# import pdb; pdb.set_trace()
# import pudb; pu.db

import datetime

def unix_time(dt):
	epoch = datetime.datetime.utcfromtimestamp(0)
	delta = dt - epoch
	return delta.total_seconds()

def unix_time_millis(dt):
	return unix_time(dt) * 1000.0

def projectToGeoJSON(city, bounds):
	x = 360 * bounds['x'] / float(city.width)
	y = 180 * bounds['y'] / float(city.height)
	width = 360 * bounds['width'] / float(city.width)
	height = 180 * bounds['height'] / float(city.height)
	return { 'x': x, 'y': y, 'width': width, 'height': height }

def geoJSONToProject(city, bounds):
	x = float(city.width) * bounds['x'] / 360
	y = float(city.height) * bounds['y'] / 180
	width = float(city.width) * bounds['width'] / 360
	height = float(city.height) * bounds['height'] / 180
	return { 'x': x, 'y': y, 'width': width, 'height': height }

def makeBox(left, top, right, bottom):
	return { "type": "Polygon", "coordinates": [ [ [left, top], [right, top], [right, bottom], [left, bottom], [left, top] ] ] }

def makeBoxFromBounds(city, bounds):
	bounds = projectToGeoJSON(city, bounds)
	return makeBox(bounds['x'], bounds['y'], bounds['x'] + bounds['width'], bounds['y'] + bounds['height'])

def makeBoundsFromBox(city, box):
	left = box['coordinates'][0][0][0]
	top = box['coordinates'][0][0][1]
	right = box['coordinates'][0][1][0]
	bottom = box['coordinates'][0][2][1]
	return geoJSONToProject(city, { 'x': left, 'y': top, 'width': right - left, 'height': bottom - top })

def makeBoxFromPoints(box):
	if box is None:
		return None
	
	points = box['points']
	planetX = box['planet']['x']
	planetY = box['planet']['y']

	return makeBox(points[0][0], points[0][1], points[2][0], points[2][1])

userID = 0
isUpdatingRasters = False
# dummyArea = None
# defaultPathTools = ["Checkpoint", "EllipseShape", "FaceShape", "GeometricLines", "GridPath", "Meander", "PrecisePath", "RectangleShape", "ShapePath", "SpiralShape", "StarShape", "ThicknessPath"]
defaultPathTools = ["Precise path", "Thickness path", "Meander", "Grid path", "Geometric lines", "Shape path", "Rectangle", "Ellipse", "Star", "Spiral", "Face generator", "Checkpoint"]

# @dajaxice_register
def setDebugMode(request, debug):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})
	global debugMode
	debugMode = debug
	return json.dumps({"message": "success"})

def setDrawingMode(request, mode):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})
	global drawingMode
	drawingMode = mode
	return json.dumps({"message": "success"})

def getPositiveVoteThreshold(city):
	return city.positiveVoteThreshold if city else 10

def getNegativeVoteThreshold(city):
	return city.negativeVoteThreshold if city else 3

def getVoteMinDuration(city):
	return datetime.timedelta(seconds=city.voteMinDuration) if city else datetime.timedelta(minutes=60)

def setVoteThresholds(request, cityName, positiveVoteThreshold=10, negativeVoteThreshold=3, positiveVoteThresholdTile=5, negativeVoteThresholdTile=3):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})
	
	city = getCity(cityName)
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	city.positiveVoteThreshold = positiveVoteThreshold
	city.negativeVoteThreshold = negativeVoteThreshold
	city.positiveVoteThresholdTile = positiveVoteThresholdTile
	city.negativeVoteThresholdTile = negativeVoteThresholdTile

	city.save()
	return json.dumps({"message": "success"})

def recomputeDrawingStates(request):
	drawings = Drawing.objects.get(status__in=['pending', 'drawing', 'rejected'])
	
	for drawing in drawings:
		# send_mail('[Comme un dessein] recomputeDrawingStates', u'recomputeDrawingStates: updateDrawingState ' + str(drawing.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
		updateDrawingState(drawing.pk, drawing)

	return json.dumps({"message": "success"})

def setVoteValidationDelay(request, cityName, hours, minutes, seconds):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})
	
	city = getCity(cityName)
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	city.voteValidationDelay = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds()
	city.save()
	return json.dumps({"message": "success"})

def setVoteMinDuration(request, cityName, hours, minutes, seconds):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})

	city = getCity(cityName)
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	city.voteMinDuration = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds()
	city.save()
	return json.dumps({"message": "success"})

def setCityNextEventDateAndLocation(request, cityName, date, location):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})

	city = getCity(cityName)
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	city.eventDate = datetime.datetime.fromtimestamp(date/1000.0)
	city.eventLocation = location
	city.save()
	return json.dumps({"message": "success"})

def setCityDimensions(request, cityName, width, height, strokeWidth):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})

	city = getCity(cityName)
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	city.width = width
	city.height = height
	city.strokeWidth = strokeWidth
	city.save()
	return json.dumps({"message": "success"})

# allauth.account.signals.email_confirmed(request, email_address)
@receiver(email_confirmed)
@checkDebug
def on_email_confirmed(sender, email_address, request, **kwargs):
	# if kwargs is None or 'email_address' not in kwargs:
	# 	print("Error: no email_address in on_email_confirmed")
	# 	return

	# request = kwargs['request']
	# email_address = kwargs['email_address']
	
	print("on_email_confirmed")

	user = email_address.user
	
	try:
		userProfile = UserProfile.objects.get(username=user.username)
	except UserProfile.DoesNotExist:
		print("Error: the user profile who confirmed his email is not found")
		return

	try: 
		emailAddress = EmailAddress.objects.get(user=request.user)
		if not emailAddress.verified:
			emailAddress.verified = True
			emailAddress.save()
	except EmailAddress.DoesNotExist:
		print("Error: the email address which was confirmed his email is not found")
		return

	userProfile.emailConfirmed = True
	userProfile.save()

	drawings = Drawing.objects(owner=user.username, status='emailNotConfirmed')
	drawings.update(status='pending')
	Vote.objects(author=userProfile).update(emailConfirmed=True)
	Comment.objects(author=userProfile).update(emailConfirmed=True)

	for vote in userProfile.votes:
		if isinstance(vote, Vote):
			try:
				# send_mail('[Comme un dessein] on_email_confirmed', u'on_email_confirmed pending ' + str(drawing.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
				updateDrawingState(vote.drawing.pk, vote.drawing)
			except DoesNotExist:
				pass

	for drawing in drawings:
		cityName = 'Wetu'
		try:
			city = City.objects.get(pk=drawing.city)
			cityName = city.name
		except City.DoesNotExist:
			print('The city does not exist')
		drawingChanged.send(sender=None, type='new', drawingId=drawing.clientId, pk=str(drawing.pk), svg=drawing.svg, city=cityName, itemType='drawing')

	return

#allauth.account.signals.email_confirmation_sent(request, confirmation, signup)
@receiver(email_confirmation_sent)
def on_email_confirmation_sent(sender, request, confirmation, signup, **kwargs):
	send_mail('[Comme un dessein] New email confirmation sent', u'A new email confirmation was sent to ' + str(confirmation.email_address) + ', to confirm his email manually follow the link: https://commeundessein.co/accounts/confirm-email/' + confirmation.key , 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
	return

@checkDebug
def isEmailKnown(request, email):
	if len(email) <= 0:
		return json.dumps({ 'error': 'The email address is empty.' })

	emailIsKnown = True
	emailShortNameIsKnown = True
	usernameIsKnown = True
	try:
		user = User.objects.get(email=email)
	except User.DoesNotExist:
		emailIsKnown = False
		emailShortName = email[:email.find('@')]
		try:
			user = User.objects.get(username=emailShortName)
		except User.DoesNotExist:
			emailShortNameIsKnown = False
	try:
		user = User.objects.get(username=email)
	except User.DoesNotExist:
		usernameIsKnown = False
	return json.dumps({ 'emailIsKnown': emailIsKnown, 'usernameIsKnown': usernameIsKnown, 'emailShortNameIsKnown': emailShortNameIsKnown })

@checkDebug
def isUsernameKnown(request, username):
	try:
		user = User.objects.get(username=username)
	except User.DoesNotExist:
		return json.dumps({'usernameIsKnown': False})
	return json.dumps({'usernameIsKnown': True})

# @dajaxice_register
@checkDebug
def multipleCalls(request, functionsAndArguments):
	results = []
	for fa in functionsAndArguments:
		results.append(json.loads(globals()[fa['function']](request=request, **fa['arguments'])))
	return json.dumps(results)


## debug
@checkDebug
def debugDatabase(request):
	models = ['Path', 'Div', 'Box', 'Drawing']

	# for model in models:
	# 	objects = globals()[model].objects()
	# 	for obj in objects:
	# 		obj.clientId = obj.clientID
	# 		obj.save()
	return


# @checkDebug
# def deleteItems(request, itemsToDelete, confirm):
# 	if not isAdmin(request.user):
# 		return json.dumps( {'state': 'error', 'message': 'not admin' } )

# 	if confirm != 'confirm':
# 		return json.dumps( {'state': 'error', 'message': 'please confirm' } )
	
# 	for itemToDelete in itemsToDelete:
# 		itemType = itemToDelete['itemType']
# 		pks = itemToDelete['pks']
		
# 		if itemType not in ['Path', 'Div', 'Box', 'AreaToUpdate', 'Drawing']:
# 			return json.dumps({'state': 'error', 'message': 'Can only delete Paths, Divs, Boxs, AreaToUpdates or Drawings.'})

# 		itemsQuerySet = globals()[itemType].objects(pk__in=pks)
	
# 		itemsQuerySet.delete()

# 	return json.dumps( {'state': 'success', 'message': 'items successfully deleted' } )

# @checkDebug
# def deleteAllItems(request, confirm):
# 	if not isAdmin(request.user):
# 		return json.dumps( {'state': 'error', 'message': 'not admin' } )

# 	if confirm != 'confirm':
# 		return json.dumps( {'state': 'error', 'message': 'please confirm' } )

# 	for itemType in ['Path', 'Div', 'Box', 'AreaToUpdate', 'Drawing']:
		
# 		itemsQuerySet = globals()[itemType].objects()
	
# 		itemsQuerySet.delete()

# 	return json.dumps( {'state': 'success', 'message': 'items successfully deleted' } )

# @dajaxice_register
@checkDebug
def githubRequest(request, githubRequest, method='get', data=None, params=None, headers=None):
	token = ACCESS_TOKEN

	try:
		socialAccount = SocialAccount.objects.get(user_id=request.user.id, provider='github')
		userToken = SocialToken.objects.get(account_id=socialAccount.id, account__provider='github')
		if userToken:
			token = userToken
	except:
		pass
	if data:
		data = json.dumps(data)
	if not headers:
		headers = {}
	headers['Authorization'] = 'token ' + str(token)
	r = getattr(requests, method)(githubRequest, data=data, params=params, headers=headers)
	response = { 'content': r.json(), 'status': r.status_code }
	if 'link' in r.headers:
		response['headers'] = { 'link': r.headers['link'] }
	return json.dumps(response)

# r = requests.post(githubRequest, headers={'Authorization': 'token ' + ACCESS_TOKEN})

# @dajaxice_register
@checkDebug
def getGithubAuthToken(request):
	client_id = None
	try:
		socialAccount = SocialAccount.objects.get(user_id=request.user.id, provider='github')
		token = SocialToken.objects.get(account__user=socialAccount.id, account__provider='github')
		r = requests.put('https://api.github.com/authorizations/clients/'+str(client_id), params={'client_secret': CLIENT_SECRET})
	except:
		return json.dumps({"state": "error", "message": "success"})
	return



# @dajaxice_register
@checkDebug
def createCity(request, name, public=None):
	try:
		city = City.objects.get(name=name, owner=request.user.username)
		return json.dumps( { 'state': 'error', 'message': 'The city named ' + name + ' already exists.' } )
	except Exception:
		pass

	city = City(name=name, owner=request.user.username, public=public)
	city.save()

	return json.dumps( { 'state': 'succes', 'city': city.to_json() } )

# @dajaxice_register
@checkDebug
def deleteCity(request, name):
	try:
		city = City.objects.get(name=name, owner=request.user.username)
	except City.DoesNotExist:
		return json.dumps( { 'state': 'error', 'message': 'The city ' + name + ' for user ' + request.user.username + ' does not exist.' } )

	city.delete()

	models = ['Path', 'Div', 'Box', 'AreaToUpdate']

	for model in models:
		globals()[model].objects(city=city.pk).delete()

	try:
		shutil.rmtree('media/rasters/' + str(city.pk))
	except Exception:
		pass

	return json.dumps( { 'state': 'succes', 'cityPk': str(city.pk) } )

# @dajaxice_register
@checkDebug
def updateCity(request, pk, name, public=None):
	try:
		city = City.objects.get(name=name, owner=request.user.username)
		return json.dumps( { 'state': 'error', 'message': 'The city named ' + name + ' already exists.' } )
	except Exception:
		pass

	try:
		city = City.objects.get(pk=pk, owner=request.user.username)
		city.name = name
		if public:
			city.public = public
		city.save()
	except City.DoesNotExist:
		return json.dumps( { 'state': 'error', 'message': 'The city with id ' + pk + ' for user ' + request.user.username + ' does not exist.' } )

	return json.dumps( { 'state': 'succes', 'city': city.to_json() } )

# @dajaxice_register
@checkDebug
def loadCities(request):
	userCities = City.objects(owner=request.user.username)
	publicCities = City.objects(public=True)
	return json.dumps( { 'userCities': userCities.to_json(), 'publicCities': publicCities.to_json() } )

# @dajaxice_register
@checkDebug
def loadUserCities(request):
	userCities = City.objects(owner=request.user.username)
	return json.dumps( { 'userCities': userCities.to_json() } )

# @dajaxice_register
@checkDebug
def loadPublicCities(request):
	publicCities = City.objects(public=True)
	return json.dumps( { 'publicCities': publicCities.to_json() } )

# @dajaxice_register
@checkDebug
def loadCity(request, pk):
	try:
		city = City.objects.get(pk=pk, owner=request.user.username)
	except City.DoesNotExist:
		return json.dumps( { 'state': 'error', 'message': 'The city with id ' + pk + ' for user ' + request.user.username + ' does not exist.' } )
	return json.dumps( { 'state': 'succes', 'city': city.to_json() } )

def getCity(cityName=None):
	if not cityName:
		city = commeUnDesseinCity
	else:
		try:
			city = City.objects.get(name=cityName)
			if not city.public:
				return None
		except City.DoesNotExist:
			return None
	return city

# def checkAddItem(item, items, itemsDates=None, ignoreDrafts=False):
# 	if not item.pk in items:
# 		if ignoreDrafts:
# 			itemIsDraft = type(item) is Path and item.isDraft
# 			if not itemIsDraft:
# 				items[item.pk] = item.to_json()
# 		else:
# 			items[item.pk] = item.to_json()
# 	return

# def checkAddItemRasterizer(item, items, itemsDates, ignoreDrafts=False):
# 	pk = item.pk
# 	itemLastUpdate = unix_time_millis(item.lastUpdate)
# 	if not pk in items and (not pk in itemsDates or itemsDates[pk]<itemLastUpdate):
# 		items[pk] = item.to_json()
# 		if pk in itemsDates:
# 			del itemsDates[pk]
# 	return

# def getItems(models, areasToLoad, qZoom, city, checkAddItemFunction, itemDates=None, owner=None, loadDrafts=True):
# 	items = {}
# 	for area in areasToLoad:

# 		tlX = area['pos']['x']
# 		tlY = area['pos']['y']

# 		planetX = area['planet']['x']
# 		planetY = area['planet']['y']

# 		geometry = makeBox(tlX, tlY, tlX+qZoom, tlY+qZoom)

# 		for model in models:

# 			itemsQuerySet = globals()[model].objects(city=city, planetX=planetX, planetY=planetY, box__geo_intersects=geometry)

# 			for item in itemsQuerySet:
# 				checkAddItemFunction(item, items, itemDates, loadDrafts)

# 	if loadDrafts:
# 		# add drafts
# 		if owner is not None:
# 			drafts = Path.objects(city=city, isDraft=True, owner=owner)
# 			for draft in drafts:
# 				if not draft.pk in items:
# 					items[draft.pk] = draft.to_json()

# 	return items

# def getAllItems(models, city, checkAddItemFunction, itemDates=None, owner=None, loadDrafts=True):
# 	items = {}

# 	for model in models:
		
# 		if model == Path and loadDrafts:
# 			itemsQuerySet = globals()[model].objects(city=city, isDraft=False)
# 		else:
# 			itemsQuerySet = globals()[model].objects(city=city)

# 		for item in itemsQuerySet:
# 			if item.pk not in items:
# 				items[item.pk] = item.to_json()
# 		# checkAddItemFunction(item, items, itemDates, loadDrafts)

# 	if loadDrafts:
# 		# add drafts
# 		if owner is not None:
# 			drafts = Path.objects(city=city, isDraft=True, owner=owner)
# 			for draft in drafts:
# 				if not draft.pk in items:
# 					items[draft.pk] = draft.to_json()

# 	return items

@checkDebug
def loadAll(request, cityName=None):

	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})

	drawings = Drawing.objects()

	items = []
	for drawing in drawings:
		items.append(drawing.to_json())

	return json.dumps( { 'items': items, 'user': request.user.username } )

@checkDebug
def loadDraft(request, cityName=None):

	city = getCity(cityName)

	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	cityPk = str(city.pk)

	try:
		userProfile = UserProfile.objects.get(username=request.user.username)
		if not userProfile.emailConfirmed:
			emailConfirmed = EmailAddress.objects.filter(user=request.user, verified=True).exists()
			userProfile.emailConfirmed = emailConfirmed
			userProfile.save()
	except UserProfile.DoesNotExist:
		print('User does not exist')

	items = []
	drafts = Drawing.objects(city=cityPk, status='draft', owner=request.user.username).only('status', 'pk', 'clientId', 'owner', 'pathList', 'title')
	
	# if we could not find a draft and authenticated : create one
	if request.user.is_authenticated() and len(drafts) == 0:
		try:
			clientId = '' + str(datetime.datetime.now()) + str(random.random())
			d = Drawing(clientId=clientId, city=cityPk, planetX=0, planetY=0, owner=request.user.username, date=datetime.datetime.now(), status='draft')
			d.save()
			drafts = [d]
		except NotUniqueError:
			pass

	if len(drafts) > 0:
		items.append(drafts[0].to_json())

	flaggedDrawings = Drawing.objects(city=cityPk, status='flagged_pending').only('svg', 'status', 'pk', 'clientId', 'owner', 'title', 'box')
	
	for drawing in flaggedDrawings:
		items.append(drawing.to_json())

	# return json.dumps( { 'paths': paths, 'boxes': boxes, 'divs': divs, 'user': user, 'rasters': rasters, 'areasToUpdate': areas, 'zoom': zoom } )
	return json.dumps( { 'items': items, 'user': request.user.username } )

# @checkDebug
# def loadDrawingsFromBounds(request, xMin, yMin, xMax, yMax, city):

# 	start = time.time()

# 	(cityPk, cityFinished) = getCity(request, city)
# 	if not cityPk:
# 		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

# 	statusToLoad = ['pending', 'drawing', 'drawn', 'rejected']

# 	if isAdmin(request.user):
# 		statusToLoad.append('emailNotConfirmed')
# 		statusToLoad.append('notConfirmed')
# 		statusToLoad.append('flagged')
# 		statusToLoad.append('test')

# 	# drawings = Drawing.objects(city=cityPk, left__in=range(xMin, xMax), top__in=range(yMin, yMax), status__in=statusToLoad).only('status', 'pk', 'clientId', 'title', 'owner', 'bounds', 'date')
# 	drawings = Drawing.objects(city=cityPk, left__gte=xMin, left__lt=xMax, top__gte=yMin, top__lt=yMax, status__in=statusToLoad).only('status', 'pk', 'clientId', 'title', 'owner', 'bounds', 'date')

# 	items = []
# 	for drawing in drawings:
# 		items.append(drawing.to_json())

# 	return json.dumps( { 'items': items, 'user': request.user.username } )

# @checkDebug
# def loadTilesFromBounds(request, xMin, yMin, xMax, yMax, city=None):

# 	(cityPk, cityFinished) = getCity(request, city)
# 	if not cityPk:
# 		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

# 	# tiles = Tile.objects(city=cityPk, x__in=range(xMin, xMax), y__in=range(yMin, yMax))
# 	tiles = Tile.objects(city=cityPk, x__gte=xMin, x__lt=xMax, y__gte=yMin, y__lt=yMax).only('status', 'pk', 'x', 'y')

# 	return json.dumps( { 'tiles': tiles.to_json(), 'user': request.user.username } )

@checkDebug
def loadDrawingsAndTilesFromBounds(request, bounds, cityName=None, drawingsToIgnore=None, tilesToIgnore=None, rejected=False):

	city = getCity(cityName)
	
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	cityPk = str(city.pk)

	statusToLoad = ['pending', 'drawing', 'drawn']

	if isAdmin(request.user):
		statusToLoad.append('emailNotConfirmed')
		statusToLoad.append('notConfirmed')
		statusToLoad.append('test')

	if rejected:
		statusToLoad.append('rejected')

	box = makeBoxFromBounds(city, bounds)

	drawings = None
	if drawingsToIgnore is None:
		# drawings = Drawing.objects(city=cityPk, left__in=range(xMin, xMax), top__in=range(yMin, yMax), status__in=statusToLoad).only('status', 'pk', 'clientId', 'title', 'owner', 'bounds', 'date')
		# drawings = Drawing.objects(city=cityPk, left__gte=xMin-1, left__lt=xMax, top__gte=yMin-1, top__lt=yMax, status__in=statusToLoad).only('status', 'pk', 'clientId', 'title', 'owner', 'bounds', 'date')
		drawings = Drawing.objects(city=cityPk, box__geo_intersects=box, status__in=statusToLoad).only('status', 'pk', 'clientId', 'title', 'owner', 'date', 'box')
	else:
		drawings = Drawing.objects(city=cityPk, box__geo_intersects=box, status__in=statusToLoad, pk__nin=drawingsToIgnore).only('status', 'pk', 'clientId', 'title', 'owner', 'date', 'box')

	items = []
	for drawing in drawings:
		items.append(drawing.to_json())

	tiles = None
	if tilesToIgnore is None:
		# tiles = Tile.objects(city=cityPk, x__in=range(xMin, xMax), y__in=range(yMin, yMax))
		# tiles = Tile.objects(city=cityPk, left__gte=xMin-1, left__lt=xMax, top__gte=yMin-1, top__lt=yMax).only('status', 'owner', 'pk', 'x', 'y', 'clientId', 'photoURL')
		tiles = Tile.objects(city=cityPk, box__geo_intersects=box).only('status', 'owner', 'pk', 'x', 'y', 'clientId', 'photoURL')
	else:
		tiles = Tile.objects(city=cityPk, box__geo_intersects=box, pk__nin=tilesToIgnore).only('status', 'owner', 'pk', 'x', 'y', 'clientId', 'photoURL')

	return json.dumps( { 'tiles': tiles.to_json(), 'items': items, 'user': request.user.username } )


# @checkDebug
# def loadBounds(request, city=None):

# 	start = time.time()

# 	(cityPk, cityFinished) = getCity(request, city)
# 	if not cityPk:
# 		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

# 	try:
# 		userProfile = UserProfile.objects.get(username=request.user.username)
# 		if not userProfile.emailConfirmed:
# 			emailConfirmed = EmailAddress.objects.filter(user=request.user, verified=True).exists()
# 			userProfile.emailConfirmed = emailConfirmed
# 			userProfile.save()
# 	except UserProfile.DoesNotExist:
# 		print('User does not exist')


# 	statusToLoad = ['pending', 'drawing', 'drawn', 'rejected']

# 	if isAdmin(request.user):
# 		statusToLoad.append('emailNotConfirmed')
# 		statusToLoad.append('notConfirmed')
# 		statusToLoad.append('flagged')
# 		statusToLoad.append('test')

# 	# drawings = Drawing.objects(city=cityPk, status__in=statusToLoad).only('svg', 'status', 'pk', 'clientId', 'title', 'owner', 'bounds')
# 	drawings = Drawing.objects(city=cityPk, status__in=statusToLoad).only('status', 'pk', 'clientId', 'title', 'owner', 'bounds', 'date')

# 	items = []
# 	for drawing in drawings:
# 		items.append(drawing.to_json())

# 	# emailNotConfirmed and notConfirmed are out of date

# 	# draftsAndNotConfirmed = Drawing.objects(city=cityPk, status__in=['draft', 'emailNotConfirmed', 'notConfirmed'], owner=request.user.username).only('svg', 'status', 'pk', 'clientId', 'owner', 'pathList', 'title', 'date')
# 	drafts = Drawing.objects(city=cityPk, status='draft', owner=request.user.username).only('svg', 'status', 'pk', 'clientId', 'owner', 'pathList', 'title')
	
# 	# if we could not find a draft and authenticated : create one
# 	if request.user.is_authenticated() and len(drafts) == 0:
# 		try:
# 			clientId = '' + str(datetime.datetime.now()) + str(random.random())
# 			d = Drawing(clientId=clientId, city=cityPk, planetX=0, planetY=0, owner=request.user.username, date=datetime.datetime.now(), status='draft')
# 			d.save()
# 			drafts = [d]
# 		except NotUniqueError:
# 			pass

# 	if len(drafts) > 0:
# 		items.append(drafts[0].to_json())

# 	# return json.dumps( { 'paths': paths, 'boxes': boxes, 'divs': divs, 'user': user, 'rasters': rasters, 'areasToUpdate': areas, 'zoom': zoom } )
# 	return json.dumps( { 'items': items, 'user': request.user.username } )

def emailIsConfirmed(request, userProfile=None):
	if not userProfile:
		userProfile = UserProfile.objects.get(username=request.user.username)
	if not userProfile.emailConfirmed:
		emailConfirmed = EmailAddress.objects.filter(user=request.user, verified=True).exists()
		userProfile.emailConfirmed = emailConfirmed
		userProfile.save()
		return emailConfirmed
	return userProfile.emailConfirmed

# @checkDebug
# def loadAllSVG(request, city=None):

# 	start = time.time()

# 	(cityPk, cityFinished) = getCity(request, city)
# 	if not cityPk:
# 		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

# 	try:
# 		userProfile = UserProfile.objects.get(username=request.user.username)
# 		if not userProfile.emailConfirmed:
# 			emailConfirmed = EmailAddress.objects.filter(user=request.user, verified=True).exists()
# 			userProfile.emailConfirmed = emailConfirmed
# 			userProfile.save()
# 	except UserProfile.DoesNotExist:
# 		print('User does not exist')


# 	statusToLoad = ['pending', 'drawing', 'drawn', 'rejected']

# 	if isAdmin(request.user):
# 		statusToLoad.append('emailNotConfirmed')
# 		statusToLoad.append('notConfirmed')
# 		statusToLoad.append('flagged')

# 	# drawings = Drawing.objects(city=cityPk, status__in=statusToLoad).only('svg', 'status', 'pk', 'clientId', 'title', 'owner', 'bounds')
# 	drawings = Drawing.objects(city=cityPk, status__in=statusToLoad).only('status', 'pk', 'clientId', 'title', 'owner', 'bounds')

# 	items = []
# 	for drawing in drawings:
# 		items.append(drawing.to_json())

# 	# emailNotConfirmed and notConfirmed are are out of date

# 	# draftsAndNotConfirmed = Drawing.objects(city=cityPk, status__in=['draft', 'emailNotConfirmed', 'notConfirmed'], owner=request.user.username).only('svg', 'status', 'pk', 'clientId', 'owner', 'pathList', 'title')
# 	drafts = Drawing.objects(city=cityPk, status='draft', owner=request.user.username).only('svg', 'status', 'pk', 'clientId', 'owner', 'pathList', 'title')
	
# 	# if we could not find a draft and authenticated : create one
# 	if request.user.is_authenticated() and len(drafts) == 0:
# 		try:
# 			clientId = '' + str(datetime.datetime.now()) + str(random.random())
# 			d = Drawing(clientId=clientId, city=cityPk, planetX=0, planetY=0, owner=request.user.username, date=datetime.datetime.now(), status='draft')
# 			d.save()
# 			drafts = [d]
# 		except NotUniqueError:
# 			pass

# 	if len(drafts) > 0:
# 		items.append(drafts[0].to_json())

# 	# return json.dumps( { 'paths': paths, 'boxes': boxes, 'divs': divs, 'user': user, 'rasters': rasters, 'areasToUpdate': areas, 'zoom': zoom } )
# 	return json.dumps( { 'items': items, 'user': request.user.username } )

@checkDebug
def loadVotes(request, cityName=None):

	try:
		userVotes = UserProfile.objects.only('votes').get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps( { 'state': 'fail_silently', 'message': 'User does not exist.' } )

	votes = []
	for vote in userVotes.votes:
		if isinstance(vote, Vote):
			try:
				votes.append({ 'pk': str(vote.drawing.clientId), 'positive': vote.positive, 'emailConfirmed': vote.author.emailConfirmed } )
			except DoesNotExist:
				pass

	return json.dumps( { 'votes': votes } )

# # @dajaxice_register
# @checkDebug
# def loadRasterizer(request, areasToLoad, itemsDates, city):

# 	start = time.time()

# 	(city, cityFinished) = getCity(request, city)
# 	if not city:
# 		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.' } )

# 	models = ['Path', 'Box']
# 	items = getItems(models, areasToLoad, 1, city, checkAddItemRasterizer, itemsDates)

# 	# add items to update which are not on the loading area (to update items which have been moved out of the area to load)
# 	for model in models:
# 		itemsQuerySet = globals()[model].objects(pk__in=itemsDates.keys())
# 		for item in itemsQuerySet:
# 			pk = str(item.pk)
# 			itemLastUpdate = unix_time_millis(item.lastUpdate)
# 			if not pk in items and itemsDates[pk]<itemLastUpdate:
# 				items[pk] = item.to_json()
# 			del itemsDates[pk]


# 	end = time.time()
# 	print "Time elapsed: " + str(end - start)

# 	return json.dumps( { 'items': items.values(), 'deletedItems': itemsDates } )

# # @return [Array<{x: x, y: y}>] the list of areas on which the bounds lie
# def getAreas(bounds):
# 	areas = {}
# 	scale = 1000
# 	l = int(floor(bounds['x'] / scale))
# 	t = int(floor(bounds['y'] / scale))
# 	r = int(floor((bounds['x']+bounds['width']) / scale))
# 	b = int(floor((bounds['y']+bounds['height']) / scale))

# 	areas = {}
# 	for x in range(l, r+1):
# 		for y in range(t, b+1):
# 			if not x in areas:
# 				areas[x] = {}
# 			areas[x][y] = True
# 	return areas

# --- Drawings --- #

# @dajaxice_register
@checkDebug
def saveDrawing(request, clientId, cityName, date, title, description=None, points=None):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	city = getCity(cityName)
	
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	cityPk = str(city.pk)

	if city.finished:
		return json.dumps({'state': 'info', 'message': "The installation is over"})

	paths = []
	if points:
		paths.append(json.dumps(points))

	drafts = Drawing.objects(city=cityPk, owner=request.user.username, status='draft')
	
	if drafts is not None and len(drafts) > 0:
		for draft in drafts:
			# paths += draft.pathList
			draft.delete()

	try:
		d = Drawing(clientId=clientId, city=cityPk, planetX=0, planetY=0, owner=request.user.username, pathList=paths, date=datetime.datetime.fromtimestamp(date/1000.0), title=title, description=description, status='draft')
		d.save()
	except NotUniqueError:
		return json.dumps({'state': 'error', 'message': 'A drawing with this id already exists.'})

	return json.dumps( {'state': 'success', 'owner': request.user.username, 'pk':str(d.pk), 'negativeVoteThreshold': city.negativeVoteThreshold, 'positiveVoteThreshold': city.positiveVoteThreshold, 'voteMinDuration': city.voteMinDuration } )

# @checkDebug
# def saveDrawing2(request, clientId, date, pathPks, title, description):
# 	if not request.user.is_authenticated():
# 		return json.dumps({'state': 'not_logged_in'})

# 	paths = []

# 	xMin = None
# 	xMax = None
# 	yMin = None
# 	yMax = None

# 	city = None
# 	planetX = None
# 	planetY = None

# 	for pathPk in pathPks:
# 		try:
# 			path = Path.objects.get(pk=pathPk)

# 			if path.drawing:
# 				return json.dumps({'state': 'error', 'message': 'One path is already part of a drawing.'})

# 			if not userAllowed(request, path.owner):
# 				return json.dumps({'state': 'error', 'message': 'One path is not property of user.'})

# 			if city != None and path.city != city or planetX != None and path.planetX != planetX or planetY != None and path.planetY != planetY:
# 				return json.dumps({'state': 'error', 'message': 'One path is from a different city or planet.'})

# 			city = path.city
# 			planetX = path.planetX
# 			planetY = path.planetY

# 			cbox = path.box['coordinates'][0]
# 			cleft = cbox[0][0]
# 			ctop = cbox[0][1]
# 			cright = cbox[2][0]
# 			cbottom = cbox[2][1]

# 			if not xMin or cleft < xMin:
# 				xMin = cleft
# 			if not xMax or cright > xMax:
# 				xMax = cright
# 			if not yMin or ctop < yMin:
# 				yMin = ctop
# 			if not yMax or cbottom > yMax:
# 				yMax = cbottom

# 			paths.append(path)
# 		except Path.DoesNotExist:
# 			return json.dumps({'state': 'error', 'message': 'Element does not exist for this user.'})

# 	points = [ [xMin, yMin], [xMax, yMin], [xMax, yMax], [xMin, yMax], [xMin, yMin] ]

# 	try:
# 		d = Drawing(clientId=clientId, city=city, planetX=planetX, planetY=planetY, box=[points], owner=request.user.username, paths=paths, date=datetime.datetime.fromtimestamp(date/1000.0), title=title, description=description)
# 		d.save()
# 	except NotUniqueError:
# 		return json.dumps({'state': 'error', 'message': 'A drawing with this name already exists.'})

# 	pathPks = []
# 	for path in paths:
# 		path.drawing = d
# 		path.isDraft = False
# 		path.save()
# 		pathPks.append(str(path.pk))

# 	return json.dumps( {'state': 'success', 'owner': request.user.username, 'pk':str(d.pk), 'pathPks': pathPks, 'negativeVoteThreshold': negativeVoteThreshold, 'positiveVoteThreshold': positiveVoteThreshold, 'voteMinDuration': voteMinDuration.total_seconds() } )

@checkDebug
def submitDrawing(request, pk, clientId, svg, date, bounds, title=None, description=None, png=None):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})
	
	try:
		userProfile = UserProfile.objects.get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps( { 'status': 'error', 'message': 'The user profile does not exist.' } )
	
	if userProfile.banned:
		return json.dumps({'state': 'error', 'message': 'User is banned.'})

	if not emailIsConfirmed(request, userProfile):
		return json.dumps({'state': 'error', 'message': 'Please confirm your email'})

	d = getDrawing(pk, clientId)

	if d is None:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})
	
	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The city is finished"})
	except City.DoesNotExist:
		return json.dumps({'state': 'info', 'message': "The city is does not exist"})

	d.svg = svg
	d.date = datetime.datetime.fromtimestamp(date/1000.0)

	d.status = 'pending'
	d.title = title
	d.description = description

	d.box = makeBoxFromBounds(city, bounds)
	# d.bounds = json.dumps(bounds)
	# d.left = int(floor(bounds['x'] / 1000))
	# d.top = int(floor(bounds['y'] / 1000))
	
	# send_mail('[Comme un dessein] submitDrawing pending', u'submitDrawing pending ' + str(d.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

	try:
		d.save()
	except NotUniqueError:
		return json.dumps({'state': 'error', 'message': 'A drawing with this name already exists.'})

	# import pdb; pdb.set_trace()
	
	# Save image
	imgstr = re.search(r'base64,(.*)', png).group(1)
	output = open('Wetu/static/drawings/'+pk+'.png', 'wb')
	imageData = imgstr.decode('base64')
	output.write(imageData)
	output.close()

	updateRasters(imageData, bounds)

	svgFile = open('Wetu/static/drawings/'+pk+'.svg', 'wb')
	svgFile.write(svg)
	svgFile.close()

	drawingChanged.send(sender=None, type='new', drawingId=d.clientId, pk=str(d.pk), svg=d.svg, city=city.name, itemType='drawing')

	send_mail('[Espero] New drawing', u'A new drawing has been submitted: https://commeundessein.co/drawing-'+str(d.pk) + u'\nsee thumbnail at: https://commeundessein.co/static/drawings/'+str(d.pk)+u'.png', 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

	thread = Thread(target = createDrawingDiscussion, args = (d,))
	thread.start()
	thread.join()

	return json.dumps( {'state': 'success', 'owner': request.user.username, 'pk':str(d.pk), 'status': d.status, 'negativeVoteThreshold': city.negativeVoteThreshold, 'positiveVoteThreshold': city.positiveVoteThreshold, 'voteMinDuration': city.voteMinDuration } )

@checkDebug
def submitTile(request, number, x, y, bounds, clientId, cityName):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})
	
	try:
		userProfile = UserProfile.objects.get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps( { 'status': 'error', 'message': 'The user profile does not exist.' } )
	
	if userProfile.banned:
		return json.dumps({'state': 'error', 'message': 'User is banned.'})

	if not emailIsConfirmed(request, userProfile):
		return json.dumps({'state': 'error', 'message': 'Please confirm your email'})


	city = getCity(cityName)
	
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	cityPk = str(city.pk)

	try:
		existingTile = Tile.objects.get(city=cityPk, x=x, y=y)
		return json.dumps({'state': 'error', 'message': 'A tile with this position already exists'})
	except Tile.DoesNotExist:
		pass

	tile = Tile(author=userProfile, owner=userProfile.username, city=cityPk, number=number, x=x, y=y, box=makeBoxFromBounds(city, bounds), clientId=clientId, dueDate=city.eventDate, placementDate=datetime.datetime.now() + datetime.timedelta(hours=24))

	try:
		tile.save()
	except NotUniqueError:
		return json.dumps({'state': 'error', 'message': 'A tile with this client id already exists'})

	# drawingChanged.send(sender=None, type='new', drawingId=d.clientId, pk=str(d.pk), svg=d.svg, city=cityName)

	# send_mail('[Espero] New drawing', u'A new drawing has been submitted: https://commeundessein.co/drawing-'+str(d.pk) + u'\nsee thumbnail at: https://commeundessein.co/static/drawings/'+str(d.pk)+u'.png', 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

	# thread = Thread(target = createDrawingDiscussion, args = (d,))
	# thread.start()
	# thread.join()

	return json.dumps( {'state': 'success', 'votes': [], 'tile': tile.to_json(), 'tile_author': tile.author.username } )

def createDrawingDiscussion(drawing):
	values = { 'title': drawing.title, 'raw': u'Discussion à propos de ' + drawing.title + u'.\n\nhttps://commeundessein.co/drawing-'+str(drawing.pk)+'\n\nhttps://commeundessein.co/static/drawings/'+str(drawing.pk)+'.png', 'category': 'dessins', 'api_username': localSettings['DISCOURSE_USERNAME'], 'api_key': localSettings['DISCOURSE_API_KEY'] }

	values_data = {}
	for k, v in values.iteritems():
		values_data[k] = unicode(v).encode('utf-8')
	data = urllib.urlencode(values_data)

	try:
		url = 'http://discussion.commeundessein.co/posts'
		req = urllib2.Request(url, data)
		response = urllib2.urlopen(req)
		resultJson = response.read()
		result = json.loads(resultJson)
		drawing.discussionId = result['topic_id']
	except:
		pass
	drawing.save()
	return

# @checkDebug
# def validateDrawing(request, pk):

# 	if not isAdmin(request.user):
# 		return json.dumps({"status": "error", "message": "not_admin"})
# 	else:
# 		return json.dumps({"status": "error", "message": "deprecated function: no need to validate drawings anymore."})

# 	d = getDrawing(pk, None)

# 	if d is None:
# 		return json.dumps({'state': 'error', 'message': 'Drawing does not exist'})

# 	if d.status != 'notConfirmed':
# 		return json.dumps({'state': 'error', 'message': 'Drawing status is not notConfirmed: ' + d.status })

# 	try:
# 		userProfile = UserProfile.objects.get(username=d.owner)
# 	except userProfile.DoesNotExist:
# 		return json.dumps( { 'status': 'error', 'message': 'The user profile does not exist.' } )

# 	if userProfile.emailConfirmed:
# 		d.status = 'pending'
# 		# send_mail('[Comme un dessein] validateDrawing', u'validateDrawing pending ' + str(d.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
# 		cityName = 'Wetu'
# 		try:
# 			city = City.objects.get(pk=d.city)
# 			cityName = city.name
# 		except City.DoesNotExist:
# 			print('The city does not exist')
# 		drawingChanged.send(sender=None, type='new', drawingId=d.clientId, pk=str(d.pk), svg=d.svg, city=cityName)
# 	else:
# 		# send_mail('[Comme un dessein] validateDrawing', u'validateDrawing emailNotConfirmed ' + str(d.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
# 		d.status = 'emailNotConfirmed'

# 	d.save()
# 	return json.dumps( {'state': 'success'} )

@checkDebug
def bannUser(request, username, removeDrawings=False, removeVotes=False, removeComments=False):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})
	try:
		userProfile = UserProfile.objects.get(username=username)
	except UserProfile.DoesNotExist:
		return json.dumps({"status": "error", "message": "The user does not exists."})

	userProfile.banned = True

	if removeDrawings:
		drawings = Drawing.objects(owner=userProfile.username)
		for drawing in drawings:
			drawing.delete()

	if removeVotes:
		for vote in userProfile.votes:
			if isinstance(vote, Vote):
				try:
					vote.author.votes.remove(vote)
				except DoesNotExist:
					pass
				try:
					vote.drawing.votes.remove(vote)
				except DoesNotExist:
					pass
				vote.delete()
	
	if removeComments:
		for comment in userProfile.comments:
			if isinstance(comment, Comment):
				try:
					comment.author.votes.remove(vote)
				except DoesNotExist:
					pass
				try:
					comment.drawing.votes.remove(vote)
				except DoesNotExist:
					pass
				comment.delete()

	return json.dumps( {'state': 'success'} )

@checkDebug
def createUsers(request, logins):

	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})
	
	for login in logins:
		print('user: ' + login['username'])
		try:
			user = User.objects.create_user(username=''+login['username'])
			user.set_password(''+login['password'])
			user.save()
			userProfile = UserProfile(username=''+login['username'], emailConfirmed=True)
			userProfile.save()
			print('created ' + userProfile.username)
			try:
				userTest = User.objects.get(username=''+login['username'])
			except Exception as e:
				print('could not get User')
				print(e)
			try:
				userProfileTest = UserProfile.objects.get(username=''+login['username'])
			except Exception as e:
				print('could not get UserProfile')
				print(e)
		except Exception as e:
			print(e)
  			pass

	return json.dumps( {'state': 'success'} )

@checkDebug
def reportAbuse(request, pk, itemType='drawing'):

	try:
		userProfile = UserProfile.objects.get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps({"status": "error", "message": "The user does not exists."})

	if not emailIsConfirmed(request, userProfile):
		return json.dumps({'state': 'error', 'message': 'Please confirm your email'})

	if not userProfile.emailConfirmed:
		return json.dumps({"status": "error", "message": "Your email must be confirmed to report an abuse."})

	if itemType == 'drawing':
		try:
			d = Drawing.objects.get(pk=pk)
		except Drawing.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Element does not exist'})
	else:
		try:
			d = Tile.objects.get(pk=pk)
		except Tile.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The installation is over"})
	except City.DoesNotExist:
		pass

	wasFlaggedPending = d.status == 'flagged_pending'
	
	if userProfile.admin:
		d.status = 'flagged'
		try:
			drawingOwner = UserProfile.objects.get(username=d.owner)
			drawingOwner.nAbuses += 1
			drawingOwner.save()
		except UserProfile.DoesNotExist:
			pass
	else:
		d.status = 'flagged_pending'
	# send_mail('[Comme un dessein] reportAbuse', u'reportAbuse flagged ' + str(d.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
	d.abuseReporter = request.user.username
	d.save()

	if itemType == 'drawing' and not wasFlaggedPending: 	# if status was flagged_pending: the drawing was removed when the user flagged it
		removeDrawingFromRasters(city, d)
	
	emailOfDrawingOwner = ''
	try:
		ownerOfDrawing = User.objects.get(username=d.owner)
		emailOfDrawingOwner = ownerOfDrawing.email
	except User.DoesNotExist:
		print('OwnerOfDrawing does not exist.')

	if itemType == 'drawing':
		send_mail('[Espero] Abuse report !', u'The drawing \"' + d.title + u'\" has been reported on Comme un Dessein !\n\nVerify it on https://commeundessein.co/drawing-'+str(d.pk)+u'\nAuthor of the report: ' + request.user.username + u', email: ' + request.user.email + u'\nAuthor of the flagged drawing: ' + d.owner + ', email: ' + emailOfDrawingOwner, 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
	else:
		send_mail('[Espero] Abuse report !', u'The tile \"' + str(d.number) + u'\" has been reported on Comme un Dessein !\n\nVerify it on https://commeundessein.co/drawing-'+str(d.pk)+u'\nAuthor of the report: ' + request.user.username + u', email: ' + request.user.email + u'\nAuthor of the flagged drawing: ' + d.owner + ', email: ' + emailOfDrawingOwner, 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

	drawingChanged.send(sender=None, type='status', drawingId=d.clientId, status=d.status, pk=str(d.pk), itemType=itemType)

	return json.dumps( {'state': 'success'} )

@checkDebug
def cancelAbuse(request, pk, itemType='drawing'):

	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})

	# send_mail('[Comme un dessein] validateDrawing', u'validateDrawing pending ' + pk, 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

	if itemType == 'drawing':
		try:
			drawing = Drawing.objects.get(pk=pk)
		except Drawing.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Element does not exist'})

		updateDrawingState(None, drawing, True)
		
		city = None
		try:
			city = City.objects.get(pk=drawing.city)
			if city.finished:
				return json.dumps({'state': 'info', 'message': "The installation is over"})
		except City.DoesNotExist:
			return json.dumps({'state': 'error', 'message': "The city does not exist"})

		updateRastersFromDrawing(city, drawing)

		reporter = None
		try:
			reporter = UserProfile.objects.get(username=drawing.abuseReporter)
		except UserProfile.DoesNotExist:
			return json.dumps({"status": "error", "message": "The abuse reporter does not exists."})

		reporter.nFalseReport += 1
		reporter.save()
	else:
		try:
			tile = Tile.objects.get(pk=pk)
		except Tile.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Element does not exist'})
		
		if tile.status == 'flagged' or tile.status == 'flagged_pending':
			tile.status = 'created'
			tile.save()

	return json.dumps( {'state': 'success'} )

@checkDebug
def deleteUsers(request, logins):
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})
	
	for login in logins:
		print('user: ' + login['username'])
		try:
			user = User.objects.get(username=login['username'])
			user.delete()
			userProfile = UserProfile.objects.get(username=login['username'])
			userProfile.delete()
			print('deleted ' + login['username'])
			try:
				userTest = User.objects.get(username=''+login['username'])
				print('could get User')
			except Exception as e:
				print('could not get User')
				print(e)
			try:
				userProfileTest = UserProfile.objects.get(username=''+login['username'])
				print('could get UserProfile')
			except Exception as e:
				print('could not get UserProfile')
				print(e)

		except Exception as e:
			print(e)
  			pass
	return json.dumps( {'state': 'success'} )

@checkDebug
def createDrawingThumbnail(request, pk, png=None):
	
	if not isAdmin(request.user):
		return json.dumps({"status": "error", "message": "not_admin"})

	imgstr = re.search(r'base64,(.*)', png).group(1)
	output = open('Wetu/static/drawings/'+pk+'.png', 'wb')
	output.write(imgstr.decode('base64'))
	output.close()
	return

# @dajaxice_register
@checkDebug
def loadDrawing(request, pk, loadSVG=False, loadVotes=True, svgOnly=False, loadPathList=False):
	try:
		drawingSet = Drawing.objects.only('pk')
		if not svgOnly:
			drawingSet = drawingSet.only('status', 'clientId', 'title', 'owner', 'discussionId', 'box')
		if loadSVG or svgOnly:
			drawingSet = drawingSet.only('svg')
		if loadVotes:
			drawingSet = drawingSet.only('votes')
		if loadPathList:
			drawingSet = drawingSet.only('pathList')
		d = drawingSet.get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})
	
	votes = []
	
	if loadVotes:
		for vote in d.votes:
			if isinstance(vote, Vote):
				try:
					votes.append( { 'vote': vote.to_json(), 'author': vote.author.username, 'authorPk': str(vote.author.pk), 'emailConfirmed': vote.author.emailConfirmed } )
				except DoesNotExist:
					pass

	return json.dumps( {'state': 'success', 'votes': votes, 'drawing': d.to_json() } )

@checkDebug
def loadTile(request, pk, loadVotes=True):
	try:
		tileSet = Tile.objects.only('pk', 'clientId', 'author', 'number', 'x', 'y', 'status', 'photoURL', 'dueDate', 'placementDate')

		if loadVotes:
			tileSet = tileSet.only('votes')

		tile = tileSet.get(pk=pk)
	except Tile.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})
	
	votes = []
	
	if loadVotes:
		for vote in tile.votes:
			if isinstance(vote, Vote):
				try:
					votes.append( { 'vote': vote.to_json(), 'author': vote.author.username, 'authorPk': str(vote.author.pk), 'emailConfirmed': vote.author.emailConfirmed } )
				except DoesNotExist:
					pass

	return json.dumps( {'state': 'success', 'votes': votes, 'tile': tile.to_json(), 'tile_author': tile.author.username } )

@checkDebug
def loadTimelapse(request, pks):
	
	drawings = Drawing.objects(pk__in=pks, status__in=['rejected', 'drawn', 'drawing', 'pending']).only('pk', 'status', 'votes')

	results = []
	
	for d in drawings:
		votes = []
		for vote in d.votes:
			if isinstance(vote, Vote):
				try:
					votes.append( { 'vote': vote.to_json(), 'author': vote.author.username, 'authorPk': str(vote.author.pk), 'emailConfirmed': vote.author.emailConfirmed } )
				except DoesNotExist:
					pass
		result = { 'pk': str(d.pk), 'votes': votes, 'status': d.status }
		results.append(result)

	# file = json.dumps( {'state': 'success', 'results': results }, indent=4 )
	# output = open('timelapse.json', 'wb')
	# output.write(file)
	# output.close()

	return json.dumps( {'state': 'success', 'results': results } )

@checkDebug
def getDrawingDiscussionId(request, pk):
	try:
		drawing = Drawing.objects.only('discussionId').get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	return  json.dumps( {'state': 'success', 'drawing': drawing.to_json() } )

@checkDebug
def loadComments(request, drawingPk, commentType='drawing'):
	
	if commentType == 'tile':
		try:
			drawing = Tile.objects.only('comments').get(pk=drawingPk)
		except Tile.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Tile does not exist'})
	else:
		try:
			drawing = Drawing.objects.only('comments').get(pk=drawingPk)
		except Drawing.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Drawing does not exist'})
	
	comments = []
	if drawing.comments:
		for comment in drawing.comments:
			if isinstance(comment, Comment):
				try:
					comments.append( { 'comment': comment.to_json(), 'author': comment.author.username, 'authorPk': str(comment.author.pk), 'emailConfirmed': comment.author.emailConfirmed } )
				except DoesNotExist:
					pass

	return json.dumps( {'state': 'success', 'comments': comments } )

@checkDebug
def loadDrawings(request, pks, loadSVG=False):
	try:
		drawings = Drawing.objects(pk__in=pks).only('status', 'pk', 'clientId', 'title', 'owner', 'votes')
		if loadSVG:
			d = d.only('svg')
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	items = []
	for drawing in drawings:
		userVoteJson = None
		try:
			userVote = Vote.objects.only('positive', 'emailConfirmed').get(drawing=drawing.pk, author=request.user.username)
			userVoteJson = userVote.to_json()
		except Vote.DoesNotExist:
			pass
		items.append({'drawing':drawing.to_json(), 'userVote': userVoteJson })
	
	return json.dumps( { 'items': items } )

# @dajaxice_register
@checkDebug
def updateDrawing(request, pk, title, description=None):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	try:
		user = UserProfile.objects.get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'The user profile does not exist.'})
	
	if user.banned:
		return json.dumps({'state': 'error', 'message': 'User is banned.'})

	try:
		d = Drawing.objects.get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The installation is over"})
	except City.DoesNotExist:
		pass

	if not userAllowed(request, d.owner):
		return json.dumps({'state': 'error', 'message': 'Not owner of drawing'})
	
	if isDrawingStatusValidated(d):
		return json.dumps({'state': 'error', 'message': 'The drawing is already validated, it cannot be modified anymore.'})

	d.title = title
	
	if description:
		d.description = description

	try:
		d.save()
	except NotUniqueError:
		return json.dumps({'state': 'error', 'message': 'A drawing with this name already exists.'})

	drawingChanged.send(sender=None, type='title', drawingId=d.clientId, title=title, description=description, itemType='drawing')

	return json.dumps( {'state': 'success' } )

def getDrawing(pk=None, clientId=None):

	if pk is None and clientId is None:
		return None

	d = None

	if pk:
		try:
			d = Drawing.objects.get(pk=pk)
		except Drawing.DoesNotExist:
			if not clientId:
				return None
	
	if d is None and clientId:
		try:
			d = Drawing.objects.get(clientId=clientId)
		except Drawing.DoesNotExist:
			return None

	return d

# @dajaxice_register
@checkDebug
def addPathToDrawing(request, points, data, bounds, pk=None, clientId=None):
	
	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	d = getDrawing(pk, clientId)

	if d is None:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	if not userAllowed(request, d.owner):
		return json.dumps({'state': 'error', 'message': 'Not owner of drawing'})

	if d.status != 'draft':
		return json.dumps({'state': 'error', 'message': 'The drawing is not a draft, it cannot be modified anymore.'})

	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The installation is over"})
	except City.DoesNotExist:
		pass

	d.pathList.append(json.dumps({ 'points': points, 'data': data }))
	
	d.box = makeBoxFromBounds(city, bounds)

	d.save()

	return json.dumps( {'state': 'success' } )

@checkDebug
def addPathsToDrawing(request, pointLists, bounds, pk=None, clientId=None):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	if pk is None and clientId is None:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	d = getDrawing(pk, clientId)

	if d is None:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "This installation is over"})
	except City.DoesNotExist:
		pass

	if not userAllowed(request, d.owner):
		return json.dumps({'state': 'error', 'message': 'Not owner of drawing'})

	if d.status != 'draft':
		return json.dumps({'state': 'error', 'message': 'The drawing is not a draft, it cannot be modified anymore.'})

	for p in pointLists:
		d.pathList.append(json.dumps({ 'points': p['points'], 'data': p['data'] }))

	d.box = makeBoxFromBounds(city, bounds)

	d.save()

	return json.dumps( {'state': 'success' } )

@checkDebug
def setPathsToDrawing(request, pointLists, bounds, pk=None, clientId=None):
	
	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	if pk is None and clientId is None:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	d = getDrawing(pk, clientId)

	if d is None:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The installation is over"})
	except City.DoesNotExist:
		return json.dumps({'state': 'error', 'message': "The city does not exist"})

	if not userAllowed(request, d.owner):
		return json.dumps({'state': 'error', 'message': 'Not owner of drawing'})

	if d.status != 'draft':
		return json.dumps({'state': 'error', 'message': 'The drawing is not a draft, it cannot be modified anymore.'})

	d.pathList = []

	for p in pointLists:
		d.pathList.append(json.dumps({ 'points': p['points'], 'data': p['data'] }))

	if bounds:
		d.box = makeBoxFromBounds(city, bounds)

	d.box = None

	d.save()

	return json.dumps( {'state': 'success' } )

@checkDebug
def updateDrawings(request):
	if not isAdmin(request.user):
		return json.dumps( { 'state': 'error', 'message': 'You must be administrator to update drawings.' } )

	drawings = Drawing.objects()
	for drawing in drawings:
		drawing.pathList = []
		for path in drawing.paths:
			data = json.loads(path.data)
			points = json.dumps({ 'points': data['points'], 'data': data['data'] })
			drawing.pathList.append(points)
		drawing.save()
	return json.dumps( {'state': 'success' } )

@checkDebug
def updateDrawingBounds(request, pk, bounds, svg):
	if not isAdmin(request.user):
		return json.dumps( { 'state': 'error', 'message': 'You must be administrator to update drawings.' } )
	
	try:
		d = Drawing.objects.get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The city is finished"})
	except City.DoesNotExist:
		return json.dumps({'state': 'error', 'message': "The city does not exist"})

	d.box = makeBoxFromBounds(city, bounds)
	d.save()

	svgFile = open('Wetu/static/drawings/'+pk+'.svg', 'wb')
	svgFile.write(svg)
	svgFile.close()

	return json.dumps( {'state': 'success' } )

@checkDebug
def updateDrawingSVG(request, pk, svg):
	if not isAdmin(request.user):
		return json.dumps( { 'state': 'error', 'message': 'You must be administrator to update drawings.' } )
	try:
		d = Drawing.objects.get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	d.svg = svg
	d.save()

	return json.dumps( {'state': 'success' } )

# @dajaxice_register
@checkDebug
def deleteDrawing(request, pk):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	try:
		d = Drawing.objects.get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist for this user.'})

	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The installation is over"})
	except City.DoesNotExist:
		return json.dumps({'state': 'error', 'message': "The city does not exist"})


	if not userAllowed(request, d.owner):
		return json.dumps({'state': 'error', 'message': 'Not owner of drawing'})

	if isDrawingStatusValidated(d):
		return json.dumps({'state': 'error', 'message': 'The drawing is already validated, it cannot be cancelled anymore.'})

	d.delete()

	drawingChanged.send(sender=None, type='delete', drawingId=d.clientId, pk=str(d.pk), itemType='drawing')

	return json.dumps( { 'state': 'success', 'pk': pk } )

@checkDebug
def cancelDrawing(request, pk):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	try:
		d = Drawing.objects.get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist for this user.'})

	if not userAllowed(request, d.owner):
		return json.dumps({'state': 'error', 'message': 'Not owner of drawing'})
	
	try:
		city = City.objects.get(pk=d.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The installation is over"})
	except City.DoesNotExist:
		return json.dumps({'state': 'error', 'message': "The city does not exist"})

	if isDrawingStatusValidated(d):
		return json.dumps({'state': 'error', 'message': 'The drawing is already validated, it cannot be cancelled anymore.'})

	d.status = 'draft'
	# send_mail('[Comme un dessein] cancelDrawing', u'cancelDrawing draft ' + str(d.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
	d.svg = None
	d.title = None
	
	try:
		drafts = Drawing.objects(city=d.city, status=['draft'], owner=request.user.username)
	except Drawing.DoesNotExist:
		print("No drafts")

	for draft in drafts:
		d.pathList += draft.pathList

	d.save()

	removeDrawingFromRasters(city, d)

	drawingChanged.send(sender=None, type='cancel', drawingId=d.clientId, pk=str(d.pk), itemType='drawing')

	return json.dumps( { 'state': 'success', 'pk': pk, 'status': d.status, 'pathList': d.pathList } )

@checkDebug
def cancelTile(request, pk):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	try:
		tile = Tile.objects.get(pk=pk)
	except Tile.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist for this user.'})

	if not userAllowed(request, tile.author.username):
		return json.dumps({'state': 'error', 'message': 'Not owner of tile'})
	
	try:
		city = City.objects.get(pk=tile.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The installation is over"})
	except City.DoesNotExist:
		return json.dumps({'state': 'error', 'message': "The city does not exist"})

	tile.delete()

	drawingChanged.send(sender=None, type='cancel', pk=str(tile.pk), itemType='tile')

	return json.dumps( { 'state': 'success', 'tile': tile.to_json() } )

@checkDebug
def deleteDrawings(request, drawingsToDelete, confirm=None):
	if not isAdmin(request.user):
		return json.dumps( {'state': 'error', 'message': 'not admin' } )

	if confirm != 'confirm':
		return json.dumps( {'state': 'error', 'message': 'please confirm' } )
	
	drawings = Drawing.objects(pk__in=drawingsToDelete)
	
	for drawing in drawings:
		drawing.delete()

		try:
			city = City.objects.get(pk=drawing.city)
			removeDrawingFromRasters(city, drawing)
		except City.DoesNotExist:
			pass

		drawingChanged.send(sender=None, type='delete', drawingId=drawing.clientId, pk=str(drawing.pk), itemType='drawing')

	return json.dumps( { 'state': 'success', 'pks': drawingsToDelete } )

# --- get drafts --- #

@checkDebug
def removeDeadReferences(request):

	if not isAdmin(request.user):
		return json.dumps( {'state': 'error', 'message': 'not admin' } )

	users = UserProfile.objects()
	for user in users:
		modified = False
		for vote in user.votes[:]:
			if not isinstance(vote, Vote):
				user.votes.remove(vote)
				modified = True
		for comment in user.comments[:]:
			if not isinstance(comment, Comment):
				user.comments.remove(comment)
				modified = True
		if modified:
			user.save()

	# votes = Vote.objects()
	# for vote in votes:
	# 	if not isinstance(vote.author, UserProfile) or not isinstance(vote.drawing, Drawing):
	# 		vote.delete()
	
	# comments = Comment.objects()
	# for comment in comments:
	# 	if not isinstance(comment.author, UserProfile) or not isinstance(comment.drawing, Drawing):
	# 		comment.delete()

	drawings = Drawing.objects()
	for drawing in drawings:
		modified = False
		for vote in drawing.votes[:]:
			if not isinstance(vote, Vote):
				drawing.votes.remove(vote)
				modified = True
		for comment in drawing.comments[:]:
			if not isinstance(comment, Comment):
				drawing.comments.remove(comment)
				modified = True
		if modified:
			drawing.save()

	return json.dumps( { 'state': 'success' } )

@checkDebug
def getDrafts(request, cityName=None):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	city = getCity(cityName)
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	paths = Path.objects(owner=request.user.username, isDraft=True, city=str(city.pk))
	items = []

	for path in paths:
		items.append(path.to_json())

	return  json.dumps( {'state': 'success', 'items': items } )

# --- votes --- #

def computeVotes(drawing):
	nPositiveVotes = 0
	nNegativeVotes = 0
	for vote in drawing.votes:
		if isinstance(vote, Vote) and vote.author.emailConfirmed:
			if vote.positive:
				nPositiveVotes += 1
			else:
				nNegativeVotes += 1
	return (nPositiveVotes, nNegativeVotes)

def isDrawingValidated(city, nPositiveVotes, nNegativeVotes):
	return nPositiveVotes >= city.positiveVoteThreshold and nNegativeVotes < city.negativeVoteThreshold

def isDrawingRejected(city, nNegativeVotes):
	return nNegativeVotes >= city.negativeVoteThreshold

def isTileValidated(city, nPositiveVotes, nNegativeVotes):
	return nPositiveVotes >= city.positiveVoteThresholdTile and nNegativeVotes < city.negativeVoteThresholdTile

def isTileRejected(city, nNegativeVotes):
	return nNegativeVotes >= city.negativeVoteThresholdTile

def updateDrawingState(drawingPk=None, drawing=None, unflag=False):
	if not drawing and not drawingPk:
		return

	if not drawing:
		try:
			drawing = Drawing.objects.get(pk=drawingPk)
		except Drawing.DoesNotExist:
			return

	city = None
	try:
		city = City.objects.get(pk=drawing.city)
		if city.finished:
			return
	except City.DoesNotExist:
		return

	if isDrawingStatusValidated(drawing):
		# send_mail('[Comme un dessein] WARNING updateDrawingState', u'updateDrawingState trying to update status while validated ' + str(drawing.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
		return

	(nPositiveVotes, nNegativeVotes) = computeVotes(drawing)

	if isDrawingValidated(city, nPositiveVotes, nNegativeVotes):
		drawing.status = 'drawing'
		drawing.save()
	elif isDrawingRejected(city, nNegativeVotes):
		drawing.status = 'rejected'
		drawing.save()
		removeDrawingFromRasters(city, drawing)
		updateRastersFromDrawing(city, drawing, 'inactive')
	elif (drawing.status == 'flagged' or drawing.status == 'flagged_pending') and unflag: 	# not accepted nor rejected: it was pending
		drawing.status = 'pending'
		drawing.save()

	# send_mail('[Comme un dessein] updateDrawingState', u'updateDrawingState ' + drawing.status + ' ' + str(drawing.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

	# drawingValidated.send(sender=None, drawingId=drawing.clientId, status=drawing.status)
	drawingChanged.send(sender=None, type='status', drawingId=drawing.clientId, status=drawing.status, pk=str(drawing.pk), itemType='drawing')

	return drawing

def updateTileState(tilePk=None, tile=None, unflag=False):
	if not tile and not tilePk:
		return

	if not tile:
		try:
			tile = Tile.objects.get(pk=tilePk)
		except Tile.DoesNotExist:
			return

	city = None
	try:
		city = City.objects.get(pk=drawing.city)
		if city.finished:
			return
	except City.DoesNotExist:
		return

	(nPositiveVotes, nNegativeVotes) = computeVotes(tile)

	if isTileValidated(city, nPositiveVotes, nNegativeVotes):
		tile.status = 'validated'
		tile.save()
	elif isTileRejected(city, nNegativeVotes):
		tile.delete()
		return tile
	elif (tile.status == 'flagged' or tile.status == 'flagged_pending') and unflag: 	# not accepted nor rejected: it was pending
		tile.status = 'pending'
		tile.save()

	# send_mail('[Comme un dessein] updateDrawingState', u'updateDrawingState ' + tile.status + ' ' + str(tile.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

	# tileValidated.send(sender=None, tileId=tile.clientId, status=tile.status)
	drawingChanged.send(sender=None, type='status', drawingId=tile.clientId, status=tile.status, pk=str(tile.pk), itemType='tile')

	return tile

def isDrawingStatusValidated(drawing):
	return drawing.status == 'drawing' or drawing.status == 'drawn'

def hasOwnerDisabledEmail(owner):
	return hasattr(owner, 'disableEmail') and owner.disableEmail


@checkDebug
def vote(request, pk, date, positive, itemType='drawing'):

	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	try:
		user = UserProfile.objects.get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'The user does not exist'})

	if user.banned:
		return json.dumps({'state': 'error', 'message': 'User is banned.'})

	if not emailIsConfirmed(request, user):
		return json.dumps({'state': 'error', 'message': 'Please confirm your email'})

	drawing = None
	if itemType == 'drawing':
		try:
			drawing = Drawing.objects.get(pk=pk)
		except Drawing.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Drawing does not exist', 'pk': pk})
	else:
		try:
			drawing = Tile.objects.get(pk=pk)
		except Drawing.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Tile does not exist', 'pk': pk})

	try:
		city = City.objects.get(pk=drawing.city)
		if city.finished:
			return json.dumps({'state': 'info', 'message': "The installation is over"})
	except City.DoesNotExist:
		return json.dumps({'state': 'error', 'message': "The city does not exist"})

	if drawing.owner == request.user.username:
		return json.dumps({'state': 'error', 'message': 'You cannot vote for your own ' + itemType})

	if itemType == 'drawing' and isDrawingStatusValidated(drawing):
		return json.dumps({'state': 'error', 'message': 'The drawing is already validated.'})

	# if drawing.status == 'emailNotConfirmed':
	# 	return json.dumps({'state': 'error', 'message': 'The owner of the drawing has not validated his account.'})
	
	if drawing.status == 'notConfirmed':
		return json.dumps({'state': 'error', 'message': 'The drawing has not been confirmed'})

	for vote in drawing.votes:
		try:
			if isinstance(vote, Vote) and vote.author.username == request.user.username:
				if vote.positive == positive:
					if datetime.datetime.now() - vote.date < datetime.timedelta(seconds=city.voteValidationDelay):
						return json.dumps({'state': 'error', 'message': 'You must wait before cancelling your vote', 'cancelled': False, 'voteValidationDelay': city.voteValidationDelay, 'messageOptions': ['voteValidationDelay'] })
					# cancel vote: delete vote and return:
					vote.author.votes.remove(vote)
					drawing.votes.remove(vote)
					vote.delete()
					return json.dumps({'state': 'success', 'message': 'Your vote was cancelled', 'cancelled': True })
				else:
					# votes are different: delete vote and break (create a new one):
					vote.author.votes.remove(vote)
					drawing.votes.remove(vote)
					vote.delete()
					break
		except DoesNotExist:
			pass

	# emailConfirmed = EmailAddress.objects.filter(user=request.user, verified=True).exists()
	# user.emailConfirmed = emailConfirmed

	vote = None
	if itemType == 'drawing':
		vote = Vote(author=user, drawing=drawing, positive=positive, date=datetime.datetime.fromtimestamp(date/1000.0))
	else:
		vote = Vote(author=user, tile=drawing, positive=positive, date=datetime.datetime.fromtimestamp(date/1000.0))

	vote.save()

	drawing.votes.append(vote)
	drawing.save()

	user.votes.append(vote)
	user.save()

	(nPositiveVotes, nNegativeVotes) = computeVotes(drawing)

	validates = None
	rejects = None

	if itemType == 'drawing':
		validates = isDrawingValidated(city, nPositiveVotes, nNegativeVotes)
		rejects = isDrawingRejected(city, nNegativeVotes)
	else:
		validates = isTileValidated(city, nPositiveVotes, nNegativeVotes)
		rejects = isTileRejected(city, nNegativeVotes)

	delay = city.voteValidationDelay

	votes = []
	for vote in drawing.votes:
		if isinstance(vote, Vote):
			try:
				votes.append( { 'vote': vote.to_json(), 'author': vote.author.username, 'authorPk': str(vote.author.pk), 'emailConfirmed': vote.author.emailConfirmed } )
			except DoesNotExist:
				pass

	title = drawing.title if itemType == 'drawing' else str(drawing.number)
	drawingChanged.send(sender=None, type='votes', itemType=itemType, drawingId=drawing.clientId, status=drawing.status, votes=votes, positive=positive, author=vote.author.username, title=title)

	if validates or rejects:

		voteMinDurationDelta = datetime.timedelta(seconds=city.voteMinDuration)
		if datetime.datetime.now() - drawing.date < voteMinDurationDelta:
			delay = (drawing.date + voteMinDurationDelta - datetime.datetime.now()).total_seconds()

		t = None
		
		if itemType == 'drawing':
			t = Timer(delay, updateDrawingState, args=[pk])
		else:
			t = Timer(delay, updateTileState, args=[pk])

		t.start()
	
	owner = None
	try:
		owner = User.objects.get(username=drawing.owner)
	except User.DoesNotExist:
		print("Owner not found")
	
	if owner and not hasOwnerDisabledEmail(owner):
		forAgainst = 'pour'
		if not positive:
			forAgainst = 'contre'
		# send_mail('[Espero]' + request.user.username + u' a voté ' + forAgainst + u' votre dessin !', request.user.username + u' a voté ' + forAgainst + u' votre dessin \"' + drawing.title + u'\" sur Comme un Dessein !\n\nVisitez le resultat sur https://commeundessein.co/drawing-'+str(drawing.pk)+u'\nMerci d\'avoir participé à Comme un Dessein,\n\nPour ne plus recevoir de notifications, allez sur https://commeundessein.co/email/desactivation/\n\nLe collectif Indien dans la ville\nhttp://idlv.co/\nidlv.contact@gmail.com', 'contact@commeundessein.co', [owner.email], fail_silently=True)
		send_mail(u'[Espero] Quelqu\'un a voté ' + forAgainst + u' votre dessin !', u'Quelqu\'un a voté ' + forAgainst + u' votre dessin \"' + drawing.title + u'\" sur Comme un Dessein !\n\nVisitez le resultat sur https://commeundessein.co/drawing-'+str(drawing.pk)+u'\nMerci d\'avoir participé à Comme un Dessein,\n\nPour ne plus recevoir de notifications, allez sur https://commeundessein.co/email/desactivation/\n\nLe collectif Indien dans la ville\nhttp://idlv.co/\nidlv.contact@gmail.com', 'contact@commeundessein.co', [owner.email], fail_silently=True)

	return json.dumps( {'state': 'success', 'owner': request.user.username, 'drawingPk':str(drawing.pk), 'votePk':str(vote.pk), 'positive': vote.positive, 'validates': validates, 'rejects': rejects, 'votes': votes, 'delay': delay, 'emailConfirmed': user.emailConfirmed } )

# --- Get Next Drawing To Be Drawn / Set Drawing Drawn --- #

# @checkDebug
# def loadItems(request, itemType, pks):

# 	if itemType not in ['Path', 'Div', 'Box', 'AreaToUpdate', 'Drawing']:
# 		return json.dumps({'state': 'error', 'message': 'Can only load Paths, Divs, Boxs, AreaToUpdates or Drawings.'})

# 	itemsQuerySet = globals()[itemType].objects(pk__in=pks)

# 	items = []
# 	for item in itemsQuerySet:
# 		items.append(item.to_json())

# 	return json.dumps( {'state': 'success', 'items': items } )

@checkDebug
def addComment(request, drawingPk, comment, date, itemType):
	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	if not emailIsConfirmed(request):
		return json.dumps({'state': 'error', 'message': 'Please confirm your email'})

	drawing = None
	if itemType == 'drawing':
		try:
			drawing = Drawing.objects.get(pk=drawingPk)
		except Drawing.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Drawing does not exist.', 'pk': drawingPk})

		if drawing.status == 'draft' or drawing.status == 'emailNotConfirmed' or drawing.status == 'notConfirmed':
			return json.dumps({'state': 'error', 'message': 'Cannot comment on this drawing.'})
	else:
		try:
			drawing = Tile.objects.get(pk=drawingPk)
		except Tile.DoesNotExist:
			return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	user = None

	try:
		user = UserProfile.objects.get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'The user profile does not exist.'})
	
	if user.banned:
		return json.dumps({'state': 'error', 'message': 'User is banned.'})

	emailConfirmed = EmailAddress.objects.filter(user=request.user, verified=True).exists()
	user.emailConfirmed = emailConfirmed

	if itemType == 'drawing':
		c = Comment(author=user, drawing=drawing, text=comment, date=datetime.datetime.fromtimestamp(date/1000.0))
	else:
		c = Comment(author=user, tile=drawing, text=comment, date=datetime.datetime.fromtimestamp(date/1000.0))
	c.save()

	drawing.comments.append(c)
	drawing.save()

	user.comments.append(c)
	user.save()
	
	owner = None
	try:
		owner = User.objects.get(username=drawing.owner)
	except User.DoesNotExist:
		print("Owner not found")
	if owner and not hasOwnerDisabledEmail(owner):
		if itemType == 'drawing':
			send_mail('[Espero] ' + request.user.username + u' a commenté votre dessin !', request.user.username + u' a commenté votre dessin \"' + drawing.title + u'\" sur Comme un Dessein !\n\nVisitez le resultat sur https://commeundessein.co/drawing-'+str(drawing.pk)+u'\nMerci d\'avoir participé à Espero,\nLe collectif Indien dans la ville\nhttp://idlv.co/\nidlv.contact@gmail.com', 'contact@commeundessein.co', [owner.email], fail_silently=True)
		else:
			send_mail('[Espero] ' + request.user.username + u' a commenté votre case !', request.user.username + u' a commenté votre case \"' + str(drawing.number) + u'\" sur Comme un Dessein !\n\nVisitez le resultat sur https://commeundessein.co/drawing-'+str(drawing.pk)+u'\nMerci d\'avoir participé à Espero,\nLe collectif Indien dans la ville\nhttp://idlv.co/\nidlv.contact@gmail.com', 'contact@commeundessein.co', [owner.email], fail_silently=True)

	return json.dumps( {'state': 'success', 'author': request.user.username, 'drawingPk':str(drawing.pk), 'commentPk': str(c.pk), 'comment': c.to_json(), 'emailConfirmed': emailConfirmed } )

@checkDebug
def modifyComment(request, commentPk, comment):
	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})
	
	try:
		user = UserProfile.objects.get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'The user profile does not exist.'})
	
	if user.banned:
		return json.dumps({'state': 'error', 'message': 'User is banned.'})

	if not emailIsConfirmed(request, user):
		return json.dumps({'state': 'error', 'message': 'Please confirm your email'})

	c = None
	try:
		c = Comment.objects.get(pk=commentPk)
	except Comment.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Comment does not exist.', 'pk': commentPk})

	if request.user.username != c.author.username and not isAdmin(request.user):
		return json.dumps({'state': 'error', 'message': 'User is not the author of the comment.'})

	c.text = comment
	c.save()

	drawingPk = str(c.drawing.pk) if c.drawing else str(c.tile.pk)
	return json.dumps( {'state': 'success', 'comment': comment, 'commentPk': str(c.pk), 'drawingPk': drawingPk } )

@checkDebug
def deleteComment(request, commentPk):
	if not request.user.is_authenticated():
		return json.dumps({'state': 'not_logged_in'})

	try:
		user = UserProfile.objects.get(username=request.user.username)
	except UserProfile.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'The user profile does not exist.'})
	
	if user.banned:
		return json.dumps({'state': 'error', 'message': 'User is banned.'})

	if not emailIsConfirmed(request, user):
		return json.dumps({'state': 'error', 'message': 'Please confirm your email'})

	comment = None
	try:
		comment = Comment.objects.get(pk=commentPk)
	except Comment.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Comment does not exist.', 'pk': commentPk})

	if request.user.username != comment.author.username and not isAdmin(request.user):
		return json.dumps({'state': 'error', 'message': 'User is not the author of the comment.'})

	if comment.drawing:
		comment.drawing.comments.remove(comment)
		comment.drawing.save()
	elif comment.tile:
		comment.tile.comments.remove(comment)
		comment.tile.save()
	comment.author.comments.remove(comment)
	comment.author.save()
	comment.delete()
	
	drawingPk = str(c.drawing.pk) if c.drawing else str(c.tile.pk)

	return json.dumps( {'state': 'success', 'commentPk': str(comment.pk), 'drawingPk': drawingPk } )


@checkDebug
def loadItems(request, itemsToLoad):
	items = []

	for itemToLoad in itemsToLoad:
		itemType = itemToLoad['itemType']
		pks = itemToLoad['pks']
		
		if itemType not in ['Path', 'Div', 'Box', 'AreaToUpdate', 'Drawing']:
			return json.dumps({'state': 'error', 'message': 'Can only load Paths, Divs, Boxs, AreaToUpdates or Drawings.'})

		itemsQuerySet = globals()[itemType].objects(pk__in=pks)
	
		for item in itemsQuerySet:
			items.append(item.to_json())

	return json.dumps( {'state': 'success', 'items': items } )


# @checkDebug
# def getNextValidatedDrawing(request, cityName=None):
	
# 	city = getCity(cityName)
# 	if not city:
# 		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )
	
# 	drawings = Drawing.objects(status='drawing', city=str(city.pk))

# 	drawingNames = []

# 	for drawing in drawings:
# 		for vote in drawing.votes:

# 			try:
# 				if isinstance(vote, Vote) and vote.author.admin:

# 					if drawing is not None:
						
# 						drawingNames.append(drawing.title)

# 						# get all path of the first drawing
# 						paths = []
# 						# for path in drawing.paths:
# 						# 	paths.append(path.to_json())
# 						for path in drawing.pathList:
# 							pJSON = json.loads(path)
# 							paths.append(json.dumps({'data': json.dumps({'points': pJSON['points'], 'data': pJSON['data'], 'planet': {'x': 0, 'y': 0}}), '_id': {'$oid': None} }))

# 						return  json.dumps( {'state': 'success', 'pk': str(drawing.pk), 'items': paths, 'svg': drawing.svg } )
# 			except DoesNotExist:
# 				pass
		
# 	if len(drawings) > 0:
# 		drawingChanged.send(sender=None, type='adminMessage', title='Drawing validated but no moderator', description='Drawing names: ' + json.dumps(drawingNames))

# 	#	 send_mail('[Comme un dessein] Drawing validated but no moderator voted for it', '[Comme un dessein] One or more drawing has been validated but no moderator voted for it', 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
# 	return  json.dumps( {'state': 'success', 'message': 'no path' } )

# @checkDebug
# def getNextTestDrawing(request, cityName=None):
	
# 	city = getCity(cityName)
# 	if not city:
# 		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )
	
# 	drawings = Drawing.objects(status='test', city=str(city.pk))

# 	for drawing in drawings:
# 		if drawing is not None:			

# 			# get all path of the first drawing
# 			paths = []
# 			# for path in drawing.paths:
# 			# 	paths.append(path.to_json())
# 			for path in drawing.pathList:
# 				pJSON = json.loads(path)
# 				paths.append(json.dumps({'data': json.dumps({'points': pJSON['points'], 'data': pJSON['data'], 'planet': {'x': 0, 'y': 0}}), '_id': {'$oid': None} }))

# 			return  json.dumps( {'state': 'success', 'pk': str(drawing.pk), 'items': paths } )
		
# 	#	 send_mail('[Comme un dessein] Drawing validated but no moderator voted for it', '[Comme un dessein] One or more drawing has been validated but no moderator voted for it', 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)
# 	return  json.dumps( {'state': 'success', 'message': 'no path' } )


@checkDebug
def setDrawingStatus(request, pk, status):

	if not isAdmin(request.user):
		return json.dumps( { 'state': 'error', 'message': 'You must be administrator to move a drawing.' } )
	
	try:
		drawing = Drawing.objects.get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Drawing does not exist.', 'pk': pk})
	
	drawing.status = status
	drawing.save()

	# send_mail('[Comme un dessein] Set drawing status', u'Set drawing status ' + status + ' ' + str(drawing.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

	return json.dumps( {'state': 'success', 'message': 'Drawing status successfully updated.', 'pk': pk, 'status': status } )

# @checkDebug
# def setDrawingStatusDrawn(request, pk, secret):
# 	if secret != TIPIBOT_PASSWORD:
# 		return json.dumps({'state': 'error', 'message': 'Secret invalid.'})

# 	try:
# 		drawing = Drawing.objects.get(pk=pk)
# 	except Drawing.DoesNotExist:
# 		return json.dumps({'state': 'error', 'message': 'Drawing does not exist.', 'pk': pk})
	
# 	drawing.status = 'drawn'
# 	drawing.save()
# 	send_mail('[Comme un dessein] Set drawing status drawn', u'Set drawing status drawn ' + str(drawing.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

# 	# drawingValidated.send(sender=None, drawingId=drawing.clientId, status=drawing.status)
# 	drawingChanged.send(sender=None, type='status', drawingId=drawing.clientId, status=drawing.status, pk=str(drawing.pk))

# 	return json.dumps( {'state': 'success', 'message': 'Drawing status successfully updated.', 'pk': pk } )

# @checkDebug
# def setDrawingStatusDrawnTest(request, pk, secret):
# 	if secret != TIPIBOT_PASSWORD:
# 		return json.dumps({'state': 'error', 'message': 'Secret invalid.'})

# 	try:
# 		drawing = Drawing.objects.get(pk=pk)
# 	except Drawing.DoesNotExist:
# 		return json.dumps({'state': 'error', 'message': 'Drawing does not exist.', 'pk': pk})
	
# 	drawing.status = 'drawntest'
# 	drawing.save()
# 	send_mail('[Comme un dessein] setDrawingStatusDrawnTest', u'setDrawingStatusDrawnTest status: drawntest ' + str(drawing.pk), 'contact@commeundessein.co', ['idlv.contact@gmail.com'], fail_silently=True)

# 	return json.dumps( {'state': 'success', 'message': 'Drawing status successfully updated.', 'pk': pk } )


@checkDebug
def setDrawingToCity(request, pk, cityName):
	
	if not isAdmin(request.user):
		return json.dumps( { 'state': 'error', 'message': 'You must be administrator to move a drawing.' } )
	
	city = getCity(cityName)
	if not city:
		return json.dumps( { 'state': 'error', 'message': 'The city does not exist.', 'code': 'CITY_DOES_NOT_EXIST' } )

	try:
		d = Drawing.objects.get(pk=pk)
	except Drawing.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})
	
	d.city = str(city.pk)
	d.save()

	for path in d.paths:
		if isinstance(path, Path):
			path.city = d.city
			path.save()

	return json.dumps( {'state': 'success' } )

def floorToMultiple(x, m):
	return int(floor(x/float(m))*m)

# warning: difference between ceil(x/m)*m and floor(x/m)*(m+1)
def ceilToMultiple(x, m):
	return int(ceil(x/float(m))*m)

def intersectRectangles(l1, t1, r1, b1, l2, t2, r2, b2):
	l = max(l1, l2)
	t = max(t1, t2)
	r = min(r1, r2)
	b = min(b1, b2)
	return (l, t, r, b)

@checkDebug
def pasteImage2onImage1(image1, image2, box1, box2, scale = 1):

	union = intersectRectangles(box1[0], box1[1], box1[2], box1[3], box2[0], box2[1], box2[2], box2[3])

	subImage2 = image2.crop(( int( ( union[0] - box2[0] ) / scale ) , int( ( union[1] - box2[1] ) / scale) , int( ( union[2] -  box2[0] ) / scale), int( ( union[3] -  box2[1] ) / scale) ))
	
	image1.paste(subImage2, ( int( ( union[0] - box1[0] ) / scale ) , int( (union[1] - box1[1] ) / scale) ))

	return image1

@checkDebug
def blendImages(image1, image2, box1, box2, scale = 1, overwrite = False):
	if overwrite:
		return pasteImage2onImage1(image1, image2, box1, box2, scale)

	union = intersectRectangles(box1[0], box1[1], box1[2], box1[3], box2[0], box2[1], box2[2], box2[3])

	subImage1 = image1.crop(( int( ( union[0] - box1[0] ) / scale ) , int( ( union[1] - box1[1] ) / scale) , int( ( union[2] -  box1[0] ) / scale), int( ( union[3] -  box1[1] ) / scale) ))
	subImage2 = image2.crop(( int( ( union[0] - box2[0] ) / scale ) , int( ( union[1] - box2[1] ) / scale) , int( ( union[2] -  box2[0] ) / scale), int( ( union[3] -  box2[1] ) / scale) ))

	alpha_composite = Image.alpha_composite(subImage1, subImage2)
	
	image1.paste(alpha_composite, ( int( ( union[0] - box1[0] ) / scale ) , int( (union[1] - box1[1] ) / scale) ))

	return alpha_composite

@checkDebug
def getDrawingBounds(city, drawing):
	drawingBounds = makeBoundsFromBox(city, drawing.box)
	return [ drawingBounds['x'], drawingBounds['y'], drawingBounds['x'] + drawingBounds['width'], drawingBounds['y'] + drawingBounds['height'] ]

@checkDebug
def boundsOverlap(b1, b2):
	ileft = max(b1[0], b2[0])
	itop = max(b1[1], b2[1])
	iright = min(b1[2], b2[2])
	ibottom = min(b1[3], b2[3])

	if (iright-ileft) <= 0 or (ibottom-itop) <= 0 or (iright-ileft) * (ibottom-itop) <= 0.001:
		return False

	return True

@checkDebug
def removeDrawingFromRasters(city, drawing):
	
	drawingBounds = getDrawingBounds(city, drawing)

	imageX = drawingBounds[0]
	imageY = drawingBounds[1]
	imageWidth = int(drawingBounds[2] - drawingBounds[0])
	imageHeight = int(drawingBounds[3] - drawingBounds[1])
	
	scaleFactor = 4

	pixelRatio = pow(scaleFactor, 3)

	l = int(floor(imageX / pixelRatio) * pixelRatio)
	t = int(floor(imageY / pixelRatio) * pixelRatio)
	r = int(ceil( (imageX + imageWidth) / pixelRatio) * pixelRatio)
	b = int(ceil( (imageY + imageHeight) / pixelRatio) * pixelRatio)

	imageWidth = r - l
	imageHeight = b - t
	
	newImage = Image.new("RGBA", (imageWidth, imageHeight), (255, 255, 255, 0))

	imageX = l
	imageY = t

	geometry = makeBoxFromBounds(city, {'x': imageX, 'y': imageY, 'width': imageWidth, 'height': imageHeight})

	overlappingDrawings = Drawing.objects(city=drawing.city, planetX=drawing.planetX, planetY=drawing.planetY, status__in=['pending', 'drawing', 'drawn'], box__geo_intersects=geometry)
	
	drawingBounds[0] = l
	drawingBounds[1] = t
	drawingBounds[2] = r
	drawingBounds[3] = b

	for d in overlappingDrawings:

		dBounds = getDrawingBounds(city, d)

		if boundsOverlap(drawingBounds, dBounds):

			imageName = 'Wetu/static/drawings/' + str(d.pk) + '.png'
			try:
				dImage = Image.open(imageName)

				(clampedImage, dBounds[0], dBounds[1], dBounds[2], dBounds[3]) = createClampedImage(dImage, {'x': dBounds[0], 'y': dBounds[1], 'width': dBounds[2]-dBounds[0], 'height': dBounds[3] - dBounds[1]})
				
				blendImages(newImage, clampedImage, drawingBounds, dBounds)

			except IOError:
				pass

	updateRastersFromImage(newImage, { 'x': imageX, 'y': imageY, 'width': imageWidth, 'height': imageHeight }, True)

	return

@checkDebug
def updateRasters(imageData, bounds):

	try:
		image = Image.open(StringIO.StringIO(imageData))				# Pillow version
	except IOError:
		return { 'state': 'error', 'message': 'impossible to read image.'}

	return updateRastersFromImage(image, bounds)


@checkDebug
def updateRastersFromDrawing(city, drawing, rasterType = 'active'):

	try:
		image = Image.open('Wetu/static/drawings/'+str(drawing.pk)+'.png')
	except IOError:
		return { 'state': 'error', 'message': 'impossible to read the drawing image.'}

	return updateRastersFromImage(image, makeBoundsFromBox(city, drawing.box), False, rasterType)

def createClampedImage(image, bounds, scaleFactor=4):

	imageX = int(bounds['x'])
	imageY = int(bounds['y'])
	imageWidth = int(image.size[0])
	imageHeight = int(image.size[1])

	pixelRatio = pow(scaleFactor, 3)

	l = int(floor(imageX / pixelRatio) * pixelRatio)
	t = int(floor(imageY / pixelRatio) * pixelRatio)
	r = int(ceil( (imageX + imageWidth) / pixelRatio) * pixelRatio)
	b = int(ceil( (imageY + imageHeight) / pixelRatio) * pixelRatio)

	imageWidth = r - l
	imageHeight = b - t
	
	clampedImage = Image.new("RGBA", (imageWidth, imageHeight))
	clampedImage.paste(image, ( imageX - l, imageY - t ) )

	imageX = l
	imageY = t

	return (clampedImage, imageX, imageY, imageWidth, imageHeight)

@checkDebug
def updateRastersFromImage(image, bounds, overwrite = False, rasterType = 'active'):

	# find top, left, bottom and right positions of the area in the quantized space
	
	scaleFactor = 4

	(clampedImage, imageX, imageY, imageWidth, imageHeight) = createClampedImage(image, bounds, scaleFactor)

	for n in range(0, 4):

		scale = pow(scaleFactor, n)
		nPixelsPerTile = 1000 * scale

		l = int(floor(imageX / nPixelsPerTile))
		t = int(floor(imageY / nPixelsPerTile))
		r = int(floor( (imageX + imageWidth) / nPixelsPerTile) + 1)
		b = int(floor( (imageY + imageHeight) / nPixelsPerTile) + 1)

		for xi in range(l, r):
			for yi in range(t, b):

				rasterName = 'Wetu/static/rasters/' + rasterType + '/zoom' + str(n) + '/' + str(xi) + ',' + str(yi) + '.png'
				try:
					# raster = Image(filename=rasterName)  		# Wand version
					raster = Image.open(rasterName)				# Pillow version
				except IOError:
					# raster = Image(width=1000, height=1000) 	# Wand version
					raster = Image.new("RGBA", (1000, 1000)) 	# Pillow version

				x = xi * nPixelsPerTile
				y = yi * nPixelsPerTile

				blendImages(raster, clampedImage, [x, y, x + nPixelsPerTile, y + nPixelsPerTile], [imageX, imageY, imageX + imageWidth, imageY + imageHeight], scale, overwrite)
				
				raster.save(rasterName)
				raster.close()

		if n < 3:
			clampedImage = clampedImage.resize((max(0, clampedImage.size[0]/scaleFactor), max(0, clampedImage.size[1]/scaleFactor)), Image.LANCZOS)

	clampedImage.close()
	image.close()

	return { 'state': 'success' }

# --- images --- #

# @dajaxice_register
@checkDebug
def saveImage(request, image):

	imageData = re.search(r'base64,(.*)', image).group(1)

	imagePath = 'media/images/' + request.user.username + '/'

	try:
		os.mkdir(imagePath)
	except OSError as exception:
		if exception.errno != errno.EEXIST:
			raise

	date = str(datetime.datetime.now()).replace (" ", "_").replace(":", ".")
	imageName = imagePath + date + ".png"

	output = open(imageName, 'wb')
	output.write(imageData.decode('base64'))
	output.close()

	# to read the image
	# inputfile = open(imageName, 'rb')
	# imageData = inputfile.read().encode('base64')
	# inputfile.close()
	# return json.dumps( { 'image': imageData, 'url': imageName } )

	return json.dumps( { 'url': imageName } )

@checkDebug
def submitTilePhoto(request, pk, imageName, dataURL):
	
	try:	
		tile = Tile.objects.get(pk=pk)
	except Tile.DoesNotExist:
		return json.dumps({'state': 'error', 'message': 'Element does not exist'})

	imgstr = re.search(r'base64,(.*)', dataURL).group(1)
	output = open('Wetu/media/images/'+imageName+'.jpg', 'wb')
	imageData = imgstr.decode('base64')
	output.write(imageData)
	output.close()

	tile.photoURL = imageName+'.jpg'
	tile.status = 'created'
	tile.save()

	return json.dumps( { 'photoURL': tile.photoURL, 'x': tile.x, 'y': tile.y, 'status': tile.status } )	

@checkDebug
def uploadImage(request, imageName, dataURL):

	imgstr = re.search(r'base64,(.*)', dataURL).group(1)
	output = open('Wetu/media/images/'+imageName+'.jpg', 'wb')
	imageData = imgstr.decode('base64')
	output.write(imageData)
	output.close()

	return json.dumps( { 'url': imageName } )
