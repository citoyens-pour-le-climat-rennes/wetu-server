from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic.base import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as django_contrib_auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from CommeUnDessein import settings
# from dajaxice.core import dajaxice_autodiscover, dajaxice_config

admin.autodiscover()

urlpatterns = [
    # prevent the extra are-you-sure-you-want-to-logout step on logout
    # url(r'^accounts/logout/$', django_contrib_auth_views.logout, {'next_page': '/'}),

    url(r'^', include('draw.urls')),
    # url(r'^$', 'draw.views.index'),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    # url(dajaxice_config.dajaxice_url, include('dajaxice.urls')),

] # + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += patterns('django.views.static',
        url(r'media/(?P<path>.*)', 'serve', {'document_root': settings.MEDIA_ROOT}),
    )

urlpatterns += staticfiles_urlpatterns()

# dajaxice_autodiscover()