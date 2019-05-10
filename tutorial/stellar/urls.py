from django.urls import path

from . import views

app_name = 'stellar'


urlpatterns = [
    path('', views.AccountList.as_view(), name='list'),
    path('issue/', views.IssueAsset.as_view(), name='issue_asset'),
    path('send_payment/', views.SendPayment.as_view(), name='send_payment')
]
