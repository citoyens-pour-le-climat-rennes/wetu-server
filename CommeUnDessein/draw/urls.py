from django.conf.urls import patterns, include, url
from draw import views
import socketio.sdjango

socketio.sdjango.autodiscover()

urlpatterns = [
    # hack for Brackets Theseus...
    url(r'^draw/templates/index\.html', views.index, name='index'),
    url(r'^draw/index\.html', views.index, name='index'),
    url(r'^index\.html', views.index, name='index'),

    url(r'^debug\.html', views.index, {'useDebugFiles': True}, name='index'),

    url(r'^debug-free\.html', views.index, {'drawingMode': 'free', 'useDebugFiles': True}, name='index'),
    url(r'^debug-pixel\.html', views.index, {'drawingMode': 'pixel', 'useDebugFiles': True}, name='index'),
    url(r'^debug-image\.html', views.index, {'drawingMode': 'image', 'useDebugFiles': True}, name='index'),
    url(r'^debug-ortho\.html', views.index, {'drawingMode': 'ortho', 'useDebugFiles': True}, name='index'),
    url(r'^debug-ortho-diag\.html', views.index, {'drawingMode': 'orthoDiag', 'useDebugFiles': True}, name='index'),
    url(r'^debug-line\.html', views.index, {'drawingMode': 'line', 'useDebugFiles': True}, name='index'),

    url(r'^free\.html', views.index, {'drawingMode': 'free'}, name='index'),
    url(r'^pixel\.html', views.index, {'drawingMode': 'pixel'}, name='index'),
    url(r'^image\.html', views.index, {'drawingMode': 'image'}, name='index'),
    url(r'^ortho\.html', views.index, {'drawingMode': 'ortho'}, name='index'),
    url(r'^ortho-diag\.html', views.index, {'drawingMode': 'orthoDiag'}, name='index'),
    url(r'^line\.html', views.index, {'drawingMode': 'line'}, name='index'),

    url(r'^$', views.index, name='index'),
    url(r'^ajaxCall/$', views.ajaxCall),
    url(r'^ajaxCallNoCSRF/$', views.ajaxCallNoCSRF),

    # url(r'^#(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$', views.index, name='index'),
    # url(r'^(?P<owner>[\w-]+)/(?P<name>[\w-]+)/#(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$', views.index, name='index'),
    url(r'^#(?P<x>[\d.]+),(?P<y>[\d.]+)$', views.index, name='index'),
    url(r'^#(?P<owner>[\w]+)/(?P<city>[\w-]+)$', views.index, name='index'),
    url(r'^#(?P<owner>[\w]+)/(?P<city>[\w-]+)/(?P<x>[\d.]+),(?P<y>[\d.]+)$', views.index, name='index'),
    url(r'^#sites/(?P<site>[\w]+)$', views.index, name='index'),
    url(r'^#sites/(?P<site>[\w]+)/(?P<x>[\d.]+),(?P<y>[\d.]+)$', views.index, name='index'),
    url(r'^#(?P<owner>[\w]+)/(?P<city>[\w-]+)/sites/(?P<site>[\w]+)$', views.index, name='index'),
    url(r'^#(?P<owner>[\w]+)/(?P<city>[\w-]+)/sites/(?P<site>[\w]+)/(?P<x>[\d.]+),(?P<y>[\d.]+)$', views.index, name='index'),
    url(r'^rasterizer/$', views.index),
    url(r'^rasterizer/ajaxCall/$', views.ajaxCall),
    url(r'^rasterizer/#(?P<x>[\d.]+),(?P<y>[\d.]+)$', views.index),
    # url(r'^rasterizer/#(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$', views.rasterizer, name='index'),
    # url(r'^([\w,.,-]+)$', views.index, name='index'),
        # url(r'^(?P<sitename>([\w,.,-]+)).romanesc.co/', views.index, name='index'),
    url("^socket\.io", include(socketio.sdjango.urls)),
    url(r'^commeUnDesseinin/paypal/', include('paypal.standard.ipn.urls')),
    url(r'^paypal/commeUnDesseinin/return/$', views.commeUnDesseinCoinsReturn),
    url(r'^paypal/commeUnDesseinin/cancel/$', views.commeUnDesseinCoinsCancel),
]