from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name = 'chat_view'),
    path('api/upload/', views.upload_pdf, name = 'upload_pdf'),
    path('api/chat/', views.chat, name='chat_view'),
    path('api/chat/compare/',views.compare_models_result, name="compare_models_result"),
    path('api/feedback/', views.feedback, name='feedback'),
    path('api/login/', views.login, name="login"),
    path('api/loginPage/', views.login_page, name="loginPage"),
    path('api/promptPage/', views.prompt_page, name="PromptPage"),
    path('api/addprompt/', views.add_or_update_prompt, name="add_or_update_prompt"),
]