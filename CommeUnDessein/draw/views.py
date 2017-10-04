from django.shortcuts import get_object_or_404, get_list_or_404, render_to_response, render
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.shortcuts import redirect

from allauth.account.views import SignupView
from allauth.account.forms import LoginForm

from draw import ajax
from ajax import getPositiveVoteThreshold, getNegativeVoteThreshold, getVoteMinDuration
from math import floor
from django.views.decorators.csrf import csrf_exempt
from models import *
# from django.http import JsonResponse
import json

# from socketio.namespace import BaseNamespace
# from sockets import ChatNamespace, DrawNamespace
# from socketio import socketio_manage

def index(request, site=None, owner=None, city=None, x=0, y=0, useDebugFiles=False, drawingMode=None, visit=False, pk=None):

	if not visit and not request.user.is_authenticated():
		return render_to_response(	"welcome.html", {}, RequestContext(request) )

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
	if pk:
		result['drawingImageURL'] = 'https://commeundessein.co/static/drawings/' + pk + '.png'
		result['drawingPk'] = pk
		try:
			drawing = Drawing.objects.get(pk=pk)
			result['drawingTitle'] = drawing.title
			result['drawingAuthor'] = drawing.owner
			try:
				city = City.objects.get(pk=drawing.city)
				result['drawingCity'] = city.name
			except City.DoesNotExist:
				print('City not found')
			
		except Drawing.DoesNotExist:
			print('Drawing not found')

	result['positiveVoteThreshold'] = getPositiveVoteThreshold()
	result['negativeVoteThreshold'] = getNegativeVoteThreshold()
	result['voteMinDuration'] = getVoteMinDuration()

	response = render_to_response(	"index.html", result, RequestContext(request) )
	return response

def live(request):
    return redirect('https://www.youtube.com/user/smarthurt/live')

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

class CustomSignupView(SignupView):
    # here we add some context to the already existing context
    def get_context_data(self, **kwargs):
        # we get context data from original view
        context = super(CustomSignupView,
                        self).get_context_data(**kwargs)
        context['login_form'] = LoginForm() # add form to context
        return context

connection = CustomSignupView.as_view()
