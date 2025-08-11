from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name = 'chat_view'),
    path('api/upload/', views.upload_pdf, name = 'upload_pdf'),
    path('api/chat/', views.chat, name='chat_view'),
    path('api/chat/compare/',views.compare_models_result, name="compare_models_result")
]