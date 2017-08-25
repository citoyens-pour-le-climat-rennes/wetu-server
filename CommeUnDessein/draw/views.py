from django.shortcuts import get_object_or_404, get_list_or_404, render_to_response, render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from draw import ajax
from ajax import positiveVoteThreshold, negativeVoteThreshold, voteMinDuration
from math import floor
from django.views.decorators.csrf import csrf_exempt
from models import *
# from django.http import JsonResponse
import json

# from socketio.namespace import BaseNamespace
# from sockets import ChatNamespace, DrawNamespace
# from socketio import socketio_manage

def index(request, site=None, owner=None, city=None, x=0, y=0, useDebugFiles=False, drawingMode=None):

	profileImageURL = ''

	try:
		profileImageURL = UserProfile.objects.get(username=request.user.username).profile_image_url
	except UserProfile.DoesNotExist:
		print 'user profile does not exist.'

	connectedToGithub = False
	githubLogin = ''
	# try:
	# 	socialAccount = SocialAccount.objects.filter(user_id=request.user.id, provider='github')[:1].get()
	# 	if socialAccount:
	# 		connectedToGithub = True
	# 		githubLogin = socialAccount.extra_data['login']
	# except:
	# 	print 'can not load social account.'

	result = {}
	if site:
		result = loadSite(request, site)

	result['profileImageURL'] = 'static/images/face.png'
	# result['profileImageURL'] = profileImageURL
	result['connectedToGithub'] = connectedToGithub
	result['githubLogin'] = githubLogin
	result['drawingMode'] = drawingMode
	result['useDebugFiles'] = useDebugFiles

	result['positiveVoteThreshold'] = positiveVoteThreshold
	result['negativeVoteThreshold'] = negativeVoteThreshold
	result['voteMinDuration'] = voteMinDuration

	response = render_to_response(	"index.html", result, RequestContext(request) )
	return response

def about(request):
	return render_to_response(	"about.html", {}, RequestContext(request) )

def termsOfService(request):
	return render_to_response(	"terms-of-service.html", {}, RequestContext(request) )

def privacyPolicy(request):
	return render_to_response(	"privacy-policy.html", {}, RequestContext(request) )


def ajaxCall(request):
	# import pdb; pdb.set_trace()
	if request.is_ajax():
		data = json.loads(request.POST.get('data'))
		function = data["function"]
		args = data["args"]
		print "ajaxCall"
		print function
		if args is None:
			args = {}
		args['request'] = request
		result = getattr(ajax, function)(**args)
		return HttpResponse(result, content_type="application/json")
		# return JsonResponse(result)
	else:
		return HttpResponse("Fail")

@csrf_exempt
def ajaxCallNoCSRF(request):
	if request.is_ajax():
		import pdb; pdb.Pdb(skip=['django.*', 'gevent.*']).set_trace()
		data = json.loads(request.POST.get('data'))
		function = data["function"]
		args = data["args"]
		if function == "getNextValidatedDrawing" or function == "setDrawingStatusDrawn":
			ajaxCall(request)
	else:
		return HttpResponse("Fail")

# socketio_manage(request.environ, {'': BaseNamespace, '/chat': ChatNamespace, '/draw': DrawNamespace}, request)


# def index(request, x=0, y=0):
# 	xf = floor(float(x))
# 	yf = floor(float(y))
# 	areasToLoad = [[xf,yf], [xf+1,yf], [xf,yf+1], [xf+1,yf+1]]
# 	points = ajax.load(request,areasToLoad)
# 	return render_to_response(	"index.html", {'x':xf, 'y':yf, 'points':points}, RequestContext(request) )
# return render(request, 'index.html')
# return render_to_response( 'index.html', {}, context_instance = RequestContext(request))

@csrf_exempt
def commeUnDesseinCoinsReturn(request):

	return render_to_response(	"commeUnDesseinin/return.html", RequestContext(request) )

@csrf_exempt
def commeUnDesseinCoinsCancel(request):
	return render_to_response(	"commeUnDesseinin/cancel.html", RequestContext(request) )


# # from ajax.py

# import datetime
# import logging
# import os
# import errno
# import json
# from django.utils import json
# # from dajaxice.decorators import dajaxice_register
# from django.core import serializers
# # from dajaxice.core import dajaxice_functions
# from django.contrib.auth.models import User
# from django.db.models import F
# from models import Path, Box, Div, UserProfile, Tool, Site
# import ast
# from pprint import pprint
# from django.contrib.auth import authenticate, login, logout
# from paypal.standard.ipn.signals import payment_was_successful, payment_was_flagged, payment_was_refunded, payment_was_reversed
# from math import *
# import re
# from django.core.validators import URLValidator
# from django.core.exceptions import ValidationError

# from mongoengine.base import ValidationError
# from mongoengine.queryset import Q

# from django_ajax.decorators import ajax


# def makeBox(tlX, tlY, brX, brY):
# 	return { "type": "Polygon", "coordinates": [ [ [tlX, tlY], [brX, tlY], [brX, brY], [tlX, brY], [tlX, tlY] ] ] }

# userID = 0

# #@dajaxice_register
# @ajax
# def load(request, areasToLoad):

# 	import pdb; pdb.set_trace()

# 	paths = []
# 	divs = []
# 	boxes = []

# 	ppks = []
# 	dpks = []
# 	bpks = []

# 	for area in areasToLoad:

# 		tlX = area['pos']['x']
# 		tlY = area['pos']['y']

# 		planetX = area['planet']['x']
# 		planetY = area['planet']['y']

# 		geometry = makeBox(tlX, tlY, tlX+1, tlY+1)
# 		# geometry = makeBox(tlX, tlY, tlX+0.1, tlY+0.1)

# 		p = Path.objects(planetX=planetX, planetY=planetY, points__geo_intersects=geometry, pk__nin=ppks)
# 		d = Div.objects(planetX=planetX, planetY=planetY, box__geo_intersects=geometry, pk__nin=dpks)
# 		b = Box.objects(planetX=planetX, planetY=planetY, box__geo_intersects=geometry, pk__nin=bpks)

# 		paths.append(p.to_json())
# 		boxes.append(b.to_json())
# 		divs.append(d.to_json())

# 		ppks += p.scalar("id")
# 		dpks += d.scalar("id")
# 		bpks += b.scalar("id")

# 	global userID
# 	user = request.user.username
# 	if not user:
# 		user = userID
# 	userID += 1


# 	# return json.dumps( {  'paths': paths, 'boxes': boxes, 'divs': divs, 'user': user } )
# 	return { 'paths': paths, 'boxes': boxes, 'divs': divs, 'user': user }

# #@dajaxice_register
# @ajax
# def savePath(request, points, pID, planet, object_type, data=None):

# 	planetX = planet['x']
# 	planetY = planet['y']

# 	lockedAreas = Box.objects(planetX=planetX, planetY=planetY, box__geo_intersects={"type": "LineString", "coordinates": points }, owner__ne=request.user.username )
# 	if lockedAreas.count()>0:
# 		# return json.dumps( { 'state': 'error', 'message': 'Your drawing intersects with a locked area'} )
# 		return {'state': 'error', 'message': 'Your drawing intersects with a locked area'}

# 	p = Path(planetX=planetX, planetY=planetY, points=points, owner=request.user.username, object_type=object_type, data=data )
# 	p.save()

# 	# return json.dumps( { 'state': 'success', 'pID': pID, 'pk': str(p.pk) } )
# 	return {'state': 'success', 'pID': pID, 'pk': str(p.pk) }

# #@dajaxice_register
# @ajax
# def updatePath(request, pk, points=None, planet=None, data=None):

# 	try:
# 		p = Path.objects.get(pk=pk)
# 	except Path.DoesNotExist:
# 		# return json.dumps({'state': 'error', 'message': 'Update impossible: element does not exist for this user'})
# 		return{'state': 'error', 'message': 'Update impossible: element does not exist for this user'}

# 	if p.locked and request.user.username != p.owner:
# 		# return json.dumps({'state': 'error', 'message': 'Not owner of path'})
# 		return{'state': 'error', 'message': 'Not owner of path'}

# 	if points or planet:
# 		planetX = planet['x']
# 		planetY = planet['y']

# 		lockedAreas = Box.objects(planetX=planetX, planetY=planetY, box__geo_intersects={"type": "LineString", "coordinates": points }, owner__ne=request.user.username )
# 		if lockedAreas.count()>0:
# 			# return json.dumps( { 'state': 'error', 'message': 'Your drawing intersects with a locked area'} )
# 			return {'state': 'error', 'message': 'Your drawing intersects with a locked area'}

# 	if points:
# 		p.points = points
# 	if planet:
# 		p.planetX = planet['x']
# 		p.planetY = planet['y']
# 	if data:
# 		p.data = data

# 	p.save()

# 	# return json.dumps( { 'state': 'success'} )
# 	return {'state': 'success'}

# #@dajaxice_register
# @ajax
# def deletePath(request, pk):

# 	try:
# 		p = Path.objects.get(pk=pk)
# 	except Path.DoesNotExist:
# 		# return json.dumps({'state': 'error', 'message': 'Delete impossible: element does not exist for this user'})
# 		return{'state': 'error', 'message': 'Delete impossible: element does not exist for this user'}

# 	if p.locked and request.user.username != p.owner:
# 		# return json.dumps({'state': 'error', 'message': 'Not owner of path'})
# 		return{'state': 'error', 'message': 'Not owner of path'}

# 	p.delete()

# 	# return json.dumps( {  'state': 'success', 'pk': pk } )
# 	return { 'state': 'success', 'pk': pk }

# #@dajaxice_register
# @ajax
# def saveBox(request, box, object_type, message, name="", url="", clonePk=None, website=False, restrictedArea=False, disableToolbar=False):
# 	if not request.user.is_authenticated():
# 		# return json.dumps({'state': 'not_logged_in'})
# 		return{'state': 'not_logged_in'}

# 	points = box['points']
# 	planetX = box['planet']['x']
# 	planetY = box['planet']['y']

# 	# check if the box intersects with another one
# 	geometry = makeBox(points[0][0], points[0][1], points[2][0], points[2][1])
# 	lockedAreas = Box.objects(planetX=planetX, planetY=planetY, box__geo_intersects=geometry, owner__ne=request.user.username )
# 	if lockedAreas.count()>0:
# 		# return json.dumps( {'state': 'error', 'message': 'This area intersects with another locked area'} )
# 		return {'state': 'error', 'message': 'This area intersects with another locked area'}

# 	if len(url)==0:
# 		url = None

# 	loadEntireArea = object_type == 'video-game'

# 	try:
# 		data = json.dumps( { 'loadEntireArea': loadEntireArea } )
# 		b = Box(planetX=planetX, planetY=planetY, box=[points], owner=request.user.username, object_type=object_type, url=url, message=message, name=name, website=website, data=data)
# 		b.save()
# 	except ValidationError:
# 		# return json.dumps({'state': 'error', 'message': 'invalid_url'})
# 		return{'state': 'error', 'message': 'invalid_url'}

# 	if website:
# 		site = Site(box=b, restrictedArea=restrictedArea, disableToolbar=disableToolbar, loadEntireArea=loadEntireArea, name=name)
# 		site.save()

# 	# pathsToLock = Path.objects(planetX=planetX, planetY=planetY, box__geo_within=geometry)
# 	# for path in pathsToLock:
# 	# 	path.locked = True
# 	# 	path.save()

# 	Path.objects(planetX=planetX, planetY=planetY, points__geo_within=geometry).update(set__locked=True, set__owner=request.user.username)
# 	Div.objects(planetX=planetX, planetY=planetY, box__geo_within=geometry).update(set__locked=True, set__owner=request.user.username)

# 	# return json.dumps( {'state': 'success', 'object_type':object_type, 'message': message, 'name': name, 'url': url, 'owner': request.user.username, 'pk':str(b.pk), 'box':box, 'clonePk': clonePk, 'website': website } )
# 	return {'state': 'success', 'object_type':object_type, 'message': message, 'name': name, 'url': url, 'owner': request.user.username, 'pk':str(b.pk), 'box':box, 'clonePk': clonePk, 'website': website }

# #@dajaxice_register
# @ajax
# def updateBox(request, object_type, pk, box=None, message=None, name=None, url=None, data=None):
# 	if not request.user.is_authenticated():
# 		# return json.dumps({'state': 'not_logged_in'})
# 		return {'state': 'not_logged_in'}

# 	if box:
# 		points = box['points']
# 		planetX = box['planet']['x']
# 		planetY = box['planet']['y']

# 		geometry = makeBox(points[0][0], points[0][1], points[2][0], points[2][1])

# 		# check if new box intersects with another one
# 		lockedAreas = Box.objects(planetX=planetX, planetY=planetY, box__geo_intersects=geometry, owner__ne=request.user.username )
# 		if lockedAreas.count()>0:
# 			# return json.dumps( {'state': 'error', 'message': 'This area intersects with a locked area'} )
# 			return {'state': 'error', 'message': 'This area intersects with a locked area'}

# 	try:
# 		b = Box.objects.get(pk=pk, owner=request.user.username)
# 	except Box.DoesNotExist:
# 		# return json.dumps({'state': 'error', 'message': 'Element does not exist for this user'})
# 		return {'state': 'error', 'message': 'Element does not exist for this user'}

# 	if box:
# 		# retrieve the old paths and divs to unlock them if they are not in the new box:
# 		points = b.box['coordinates'][0]

# 		planetX = b.planetX
# 		planetY = b.planetY

# 		geometry = makeBox(points[0][0], points[0][1], points[2][0], points[2][1])
# 		oldPaths = Path.objects(planetX=planetX, planetY=planetY, points__geo_within=geometry)
# 		oldDivs = Div.objects(planetX=planetX, planetY=planetY, box__geo_within=geometry)

# 	# update the box:
# 	if box:
# 		b.box = [box['points']]
# 		b.planetX = box['planet']['x']
# 		b.planetY = box['planet']['y']
# 	if name:
# 		b.name = name
# 	if url and len(url)>0:
# 		b.url = url
# 	if message:
# 		b.message = message
# 	if data:
# 		b.data = data

# 	try:
# 		b.save()
# 	except ValidationError:
# 		# return json.dumps({'state': 'error', 'message': 'invalid_url'})
# 		return{'state': 'error', 'message': 'invalid_url'}

# 	if box:
# 		# retrieve the new paths and divs to lock them if they were not in the old box:
# 		points = box['points']
# 		planetX = box['planet']['x']
# 		planetY = box['planet']['y']
# 		geometry = makeBox(points[0][0], points[0][1], points[2][0], points[2][1])

# 		newPaths = Path.objects(planetX=b.planetX, planetY=b.planetY, points__geo_within=geometry)
# 		newDivs = Div.objects(planetX=b.planetX, planetY=b.planetY, box__geo_within=geometry)

# 		# update old and new paths and divs
# 		newPaths.update(set__locked=True, set__owner=request.user.username)
# 		newDivs.update(set__locked=True, set__owner=request.user.username)

# 		oldPaths.filter(pk__nin=newPaths.scalar("id")).update(set__locked=False, set__owner='public')
# 		oldDivs.filter(pk__nin=newDivs.scalar("id")).update(set__locked=False, set__owner='public')

# 		# for oldPath in oldPaths:
# 		# 	if oldPath not in newPaths:
# 		# 		oldPath.locked = False
# 		# 		oldPath.save()

# 		# for oldDiv in oldDivs:
# 		# 	if oldDiv not in newDivs:
# 		# 		oldDiv.locked = False
# 		# 		oldDiv.save()

# 	# return json.dumps( {'state': 'success', 'object_type':object_type } )
# 	return {'state': 'success', 'object_type':object_type }

# #@dajaxice_register
# @ajax
# def deleteBox(request, pk):
# 	if not request.user.is_authenticated():
# 		# return json.dumps({'state': 'not_logged_in'})
# 		return{'state': 'not_logged_in'}

# 	try:
# 		b = Box.objects.get(pk=pk, owner=request.user.username)
# 	except Box.DoesNotExist:
# 		# return json.dumps({'state': 'error', 'message': 'Element does not exist for this user'})
# 		return{'state': 'error', 'message': 'Element does not exist for this user'}

# 	points = b.box['coordinates'][0]
# 	planetX = b.planetX
# 	planetY = b.planetY
# 	oldGeometry = makeBox(points[0][0], points[0][1], points[2][0], points[2][1])

# 	Path.objects(planetX=planetX, planetY=planetY, points__geo_within=oldGeometry).update(set__locked=False)
# 	Div.objects(planetX=planetX, planetY=planetY, box__geo_within=oldGeometry).update(set__locked=False)

# 	if request.user.username != b.owner:
# 		# return json.dumps({'state': 'error', 'message': 'Not owner of div'})
# 		return{'state': 'error', 'message': 'Not owner of div'}

# 	b.delete()

# 	# return json.dumps( { 'state': 'success', 'pk': pk } )
# 	return { 'state': 'success', 'pk': pk }

# #@dajaxice_register
# @ajax
# def saveDiv(request, box, object_type, message=None, url=None, data=None, clonePk=None):

# 	points = box['points']
# 	planetX = box['planet']['x']
# 	planetY = box['planet']['y']

# 	lockedAreas = Box.objects( planetX=planetX, planetY=planetY, box__geo_intersects=makeBox(points[0][0], points[0][1], points[2][0], points[2][1]) ) # , owner__ne=request.user.username )
# 	locked = False
# 	for area in lockedAreas:
# 		if area.owner == request.user.username:
# 			locked = True
# 		else:
# 			# return json.dumps( {'state': 'error', 'message': 'Your div intersects with a locked area'} )
# 			return {'state': 'error', 'message': 'Your div intersects with a locked area'}

# 	# if lockedAreas.count()>0:
# 	# 	return json.dumps( {'state': 'error', 'message': 'Your div intersects with a locked area'} )

# 	d = Div(planetX=planetX, planetY=planetY, box=[points], owner=request.user.username, object_type=object_type, message=message, url=url, data=data, locked=locked)
# 	d.save()

# 	# return json.dumps( {'state': 'success', 'object_type':object_type, 'message': message, 'url': url, 'owner': request.user.username, 'pk':str(d.pk), 'box': box, 'data': data, 'clonePk': clonePk } )
# 	return {'state': 'success', 'object_type':object_type, 'message': message, 'url': url, 'owner': request.user.username, 'pk':str(d.pk), 'box': box, 'data': data, 'clonePk': clonePk }

# #@dajaxice_register
# @ajax
# def updateDiv(request, object_type, pk, box=None, message=None, url=None, data=None):

# 	try:
# 		d = Div.objects.get(pk=pk)
# 	except Div.DoesNotExist:
# 		# return json.dumps({'state': 'error', 'message': 'Element does not exist'})
# 		return{'state': 'error', 'message': 'Element does not exist'}

# 	if d.locked and request.user.username != d.owner:
# 		# return json.dumps({'state': 'error', 'message': 'Not owner of div'})
# 		return{'state': 'error', 'message': 'Not owner of div'}

# 	if box:
# 		points = box['points']
# 		planetX = box['planet']['x']
# 		planetY = box['planet']['y']

# 		lockedAreas = Box.objects(planetX=planetX, planetY=planetY, box__geo_intersects=makeBox(points[0][0], points[0][1], points[2][0], points[2][1]) ) # , owner__ne=request.user.username )
# 		d.locked = False
# 		for area in lockedAreas:
# 			if area.owner == request.user.username:
# 				d.locked = True
# 			else:
# 				# return json.dumps( {'state': 'error', 'message': 'Your div intersects with a locked area'} )
# 				return {'state': 'error', 'message': 'Your div intersects with a locked area'}

# 	if url:
# 		#	No need to update URL?
# 		# 	valid, errorMessage = validateURL(url)
# 		# 	if not valid:
# 		# 		return errorMessage
# 		d.url = url
# 	if box:
# 		d.box = [box['points']]
# 		d.planetX = box['planet']['x']
# 		d.planetY = box['planet']['y']
# 	if message:
# 		d.message = message
# 	if data:
# 		d.data = data

# 	d.save()

# 	# return json.dumps( {'state': 'success' } )
# 	return {'state': 'success' }

# #@dajaxice_register
# @ajax
# def deleteDiv(request, pk):

# 	try:
# 		d = Div.objects.get(pk=pk)
# 	except Div.DoesNotExist:
# 		# return json.dumps({'state': 'error', 'message': 'Element does not exist for this user.'})
# 		return{'state': 'error', 'message': 'Element does not exist for this user.'}

# 	if d.locked and request.user.username != d.owner:
# 		# return json.dumps({'state': 'error', 'message': 'You are not the owner of this div.'})
# 		return{'state': 'error', 'message': 'You are not the owner of this div.'}

# 	d.delete()

# 	# return json.dumps( { 'state': 'success', 'pk': pk } )
# 	return { 'state': 'success', 'pk': pk }

# # --- images --- #

# #@dajaxice_register
# @ajax
# def saveImage(request, image):

# 	imageData = re.search(r'base64,(.*)', image).group(1)

# 	imagePath = 'static/images/' + request.user.username + '/'

# 	try:
# 		os.mkdir(imagePath)
# 	except OSError as exception:
# 		if exception.errno != errno.EEXIST:
# 			raise
# 	date = str(datetime.datetime.now()).replace (" ", "_").replace(":", ".")
# 	imageName = imagePath + date + ".png"

# 	output = open(imageName, 'wb')
# 	output.write(imageData.decode('base64'))
# 	output.close()

# 	# to read the image
# 	# inputfile = open(imageName, 'rb')
# 	# imageData = inputfile.read().encode('base64')
# 	# inputfile.close()
# 	# return json.dumps( { 'image': imageData, 'url': imageName } )

# 	# return json.dumps( { 'url': imageName } )
# 	return { 'url': imageName }

# # --- tools --- #

# #@dajaxice_register
# @ajax
# def addTool(request, name, className, source, compiledSource):
# 	try:
# 		tool = Tool(owner=request.user.username, name=name, className=className, source=source, compiledSource=compiledSource)
# 	except OperationError:
# 		# return json.dumps( { 'state': 'error', 'message': 'A tool with the name ' + name + ' or the className ' + className + ' already exists.' } )
# 		return { 'state': 'error', 'message': 'A tool with the name ' + name + ' or the className ' + className + ' already exists.' }
# 	tool.save()
# 	# return json.dumps( { 'state': 'success', 'message': 'Request for adding ' + name + ' successfully sent.' } )
# 	return { 'state': 'success', 'message': 'Request for adding ' + name + ' successfully sent.' }

# #@dajaxice_register
# @ajax
# def updateTool(request, name, className, source, compiledSource):
# 	try:
# 		tool = Tool.objects.get(name=name)
# 	except Tool.DoesNotExist:
# 		# return json.dumps( { 'state': 'error', 'message': 'The tool with the name ' + name + ' or the className ' + className + ' does not exist.' } )
# 		return { 'state': 'error', 'message': 'The tool with the name ' + name + ' or the className ' + className + ' does not exist.' }

# 	tool.nRequests += 1
# 	tool.save()
# 	newName = name + str(tool.nRequests)
# 	newClassName = className + str(tool.nRequests)
# 	newTool = Tool(owner=request.user.username, name=newName, originalName=name, className=newClassName, source=source, compiledSource=compiledSource)
# 	newTool.save()

# 	# return json.dumps( { 'state': 'success', 'message': 'Request for updating ' + name + ' successfully sent.' } )
# 	return { 'state': 'success', 'message': 'Request for updating ' + name + ' successfully sent.' }

# #@dajaxice_register
# @ajax
# def getTools(request):
# 	tools = Tool.objects(accepted=True)
# 	# return json.dumps( { 'state': 'success', 'tools': tools.to_json() } )
# 	return { 'state': 'success', 'tools': tools.to_json() }

# # --- admin --- #

# #@dajaxice_register
# @ajax
# def getWaitingTools(request):
# 	if request.user.username != 'arthur.sw':
# 		# return json.dumps( { 'state': 'error', 'message': 'You must be administrator to get the waiting tools.' } )
# 		return { 'state': 'error', 'message': 'You must be administrator to get the waiting tools.' }
# 	tools = Tool.objects(accepted=False)
# 	# return json.dumps( { 'state': 'success', 'tools': tools.to_json() } )
# 	return { 'state': 'success', 'tools': tools.to_json() }

# #@dajaxice_register
# @ajax
# def acceptTool(request, name):
# 	if request.user.username != 'arthur.sw':
# 		# return json.dumps( { 'state': 'error', 'message': 'You must be administrator to accept tools.' } )
# 		return { 'state': 'error', 'message': 'You must be administrator to accept tools.' }
# 	try:
# 		tool = Tool.objects.get(name=name)
# 	except Tool.DoesNotExist:
# 		# return json.dumps( { 'state': 'success', 'message': 'New tool does not exist.' } )
# 		return { 'state': 'success', 'message': 'New tool does not exist.' }
# 	if tool.originalName:
# 		try:
# 			originalTool = Tool.objects.get(name=tool.originalName)
# 		except Tool.DoesNotExist:
# 			# return json.dumps( { 'state': 'success', 'message': 'Original tool does not exist.' } )
# 			return { 'state': 'success', 'message': 'Original tool does not exist.' }
# 		originalTool.source = tool.source
# 		originalTool.compiledSource = tool.compiledSource
# 		originalTool.save()
# 		tool.delete()
# 	else:
# 		tool.accepted = True
# 		tool.save()
# 	# return json.dumps( { 'state': 'success' } )
# 	return { 'state': 'success' }

# # --- loadSite --- #

# #@dajaxice_register
# @ajax
# def loadSite(request, siteName):
# 	try:
# 		site = Site.objects.get(name=siteName)
# 	except:
# 		return { 'state': 'error', 'message': 'Site ' + siteName + ' does not exist.' }
# 	return { 'state': 'success', 'box': site.box.to_json(), 'site': site.to_json(), 'loadEntireArea': site.loadEntireArea }

# # --- payment signal --- #

# def updateUserCommeUnDesseinCoins(sender, **kwargs):
# 	ipn_obj = sender

# 	print "updateUserCommeUnDesseinCoins"

# 	if ipn_obj.payment_status == "Completed":

# 		data = json.loads(ipn_obj.custom)

# 		import pdb; pdb.set_trace()

# 		# profile = User.objects.get(username=data['user']).profile
# 		# profile.commeUnDesseinCoins += ipn_obj.num_cart_items

# 		# Fails with: OperationalError: no such column: user_profile.commeUnDesseinCoins:
# 		# UserProfile.objects.filter(user__username=data['user']).update(commeUnDesseinCoins=F('commeUnDesseinCoins')+1000*ipn_obj.num_cart_items)
# 		# so instead:

# 		try:
# 			userProfile = User.objects.get(username=data['user']).profile
# 			userProfile.commeUnDesseinCoins += 1000*ipn_obj.num_cart_items
# 			userProfile.save()
# 		except UserProfile.DoesNotExist:
# 			pass

# 	else:
# 		print "payment was not successful: "
# 		print ipn_obj.payment_status

# payment_was_successful.connect(updateUserCommeUnDesseinCoins)

# def paymentWasFlagged(sender, **kwargs):
# 	ipn_obj = sender
# 	print "paymentWasFlagged"

# payment_was_flagged.connect(paymentWasFlagged)

# def paymentWasRefunded(sender, **kwargs):
# 	ipn_obj = sender
# 	print "paymentWasRefunded"

# payment_was_refunded.connect(paymentWasRefunded)

# def paymentWasReversed(sender, **kwargs):
# 	ipn_obj = sender
# 	print "paymentWasReversed"

# payment_was_reversed.connect(paymentWasReversed)

# # /from ajax.py
