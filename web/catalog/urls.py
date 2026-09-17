from django.urls import path
from . import views
from . import seeds
from . import visitors

urlpatterns = [
    path('api/v1/visitor/', visitors.visit, name='visitor_visit'),
    path('seeds/', seeds.gallery, name='seeds'),
    path('seeds/<uuid:seed_id>/', seeds.detail, name='seed_detail'),
    path('api/v1/seeds/', seeds.publish, name='seed_publish'),
    path('manage/seeds/', seeds.management, name='seed_management'),
    path('', views.catalog, name='catalog'), path('mods/<uuid:mod_id>/', views.detail, name='detail'),
    path('files/<uuid:release_id>/download/', views.release_file, name='download'),
    path('files/<uuid:release_id>/cover/', views.release_file, {'cover': True}, name='cover'),
    path('downloads/', views.downloads, name='downloads'),
    path('downloads/windows/', views.desktop_download, name='desktop_download'),
    path('downloads/windows/<uuid:release_id>/', views.desktop_download, name='desktop_version_download'),
    path('login/', views.sign_in, name='login'), path('logout/', views.sign_out, name='logout'),
    path('password/', views.password_change, name='password_change'),
    path('workshop/', views.workshop, name='workshop'),
    path('workshop/new/', views.quick_publish, name='new_mod'),
    path('workshop/<uuid:mod_id>/edit/', views.edit_mod, name='edit_mod'),
    path('workshop/<uuid:mod_id>/versions/', views.upload, name='upload'),
    path('workshop/versions/<uuid:release_id>/action/', views.release_action, name='release_action'),
    path('manage/', views.management, name='management'),
    path('manage/software/', views.software_management, name='software_management'),
    path('manage/software/<uuid:release_id>/', views.software_action, name='software_action'),
    path('manage/mods/<uuid:mod_id>/', views.moderate, name='moderate'),
    path('manage/accounts/', views.accounts, name='accounts'),
    path('manage/accounts/<int:user_id>/', views.account_change, name='account_change'),
    path('api/v1/catalog/', views.api_catalog, name='api_catalog'), path('health/', views.health),
    path('api/v1/desktop/releases/', views.api_desktop_releases, name='api_desktop_releases'),
]
