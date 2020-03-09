"""mysite URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings #先导外层
from django.conf.urls.static import static

from . import views
import xadmin
xadmin.autodiscover()

from xadmin.plugins import xversion
xversion.register_models()

urlpatterns = [
    path('',views.home,name='home'),#调用views中的blog_list函数
    path('admin/', admin.site.urls),
    path('ckeditor',include('ckeditor_uploader.urls')), #添加ckeditor   url
    path('blog/',include('blog.urls')),  #当匹配到前面的url时，会将剩余的url传递给下面的urls文件进行分发
    path('login/',views.login,name='login'),
    path('logout/',views.logout,name='logout'),
    path('user_info/',views.user_info,name='user_info'),
    path('login_for_modal/',views.login_for_modal,name='login_for_modal'),
    path('comment/',include('comment.urls')),
    path('register/', views.register, name='register'),
    path('likes/',include('likes.urls')),
    path('vcode/<int:num>',views.get_pic,name='get_pic',),

]
urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)