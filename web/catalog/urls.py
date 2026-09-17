from django.urls import path
from . import views

urlpatterns = [
    path('', views.catalog, name='catalog'), path('mods/<uuid:mod_id>/', views.detail, name='detail'),
    path('files/<uuid:release_id>/download/', views.release_file, name='download'),
    path('files/<uuid:release_id>/cover/', views.release_file, {'cover': True}, name='cover'),
    path('downloads/', views.downloads, name='downloads'),
    path('login/', views.sign_in, name='login'), path('logout/', views.sign_out, name='logout'),
    path('password/', views.password_change, name='password_change'),
    path('workshop/', views.workshop, name='workshop'),
    path('workshop/new/', views.edit_mod, name='new_mod'),
    path('workshop/<uuid:mod_id>/edit/', views.edit_mod, name='edit_mod'),
    path('workshop/<uuid:mod_id>/versions/', views.upload, name='upload'),
    path('workshop/versions/<uuid:release_id>/action/', views.release_action, name='release_action'),
    path('manage/', views.management, name='management'),
    path('manage/mods/<uuid:mod_id>/', views.moderate, name='moderate'),
    path('manage/accounts/', views.accounts, name='accounts'),
    path('manage/accounts/<int:user_id>/', views.account_change, name='account_change'),
    path('api/v1/catalog/', views.api_catalog, name='api_catalog'), path('health/', views.health),
]
