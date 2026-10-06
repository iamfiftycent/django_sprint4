from django.urls import path
from . import views


app_name = 'blog'

urlpatterns = [
    path('', views.index, name='index'),
    path('posts/<int:pk>/', views.post_detail, name='post_detail'),
    path('category/<slug:category_slug>/',
         views.category_posts,
         name='category_posts'),
    path('profile/<slug:username>/edit/',
         views.edit_profile,
         name='edit_profile'),
    path('profile/<slug:username>/', views.profile, name='profile'),
    path('posts/create/', views.post_create, name='create_post'),
    path('posts/<int:pk>/edit/', views.edit_post, name='edit_post'),
]
