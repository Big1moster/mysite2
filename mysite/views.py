from django.shortcuts import render,redirect,HttpResponse
from django.contrib.contenttypes.models import ContentType
from read_account.utils import get_seven_days_read_date,get_today_hot_data,get_yesterday_hot_data,get_seven_days_hot_blog
from blog.models import Blog
from django.core.cache import cache
from django.contrib import auth
from django.urls import reverse
from .forms import LoginForm,RegForm
from django.contrib.auth.models import User
from django.http import JsonResponse
import random
import os
from io import BytesIO
from PIL import Image
from PIL import ImageFilter
from PIL.ImageDraw import Draw
from PIL.ImageFont import truetype
from django.views.decorators.csrf import csrf_exempt



# 生成验证码
class Bezier(object):
    """贝塞尔曲线"""

    def __init__(self):
        self.tsequence = tuple([t / 20.0 for t in range(21)])
        self.beziers = {}

    def make_bezier(self, n):
        """绘制贝塞尔曲线"""
        try:
            return self.beziers[n]
        except KeyError:
            combinations = pascal_row(n - 1)
            result = []
            for t in self.tsequence:
                tpowers = (t ** i for i in range(n))
                upowers = ((1 - t) ** i for i in range(n - 1, -1, -1))
                coefs = [c * a * b for c, a, b in zip(combinations,
                                                      tpowers, upowers)]
                result.append(coefs)
            self.beziers[n] = result
            return result
class Captcha(object):
    """验证码"""

    def __init__(self, width, height, fonts=None, color=None):
        self._image = None
        self._fonts = fonts if fonts else \
            [os.path.join(os.path.dirname(__file__), 'fonts', font)
             for font in ['georgia.ttf','msyh.ttc']]
        # for font in ['ArialRB.ttf', 'ArialNI.ttf', 'Georgia.ttf', 'Kongxin.ttf']]
        self._color = color if color else random_color(0, 200, random.randint(220, 255))
        self._width, self._height = width, height

    @classmethod
    def instance(cls, width=200, height=75):
        prop_name = '_instance_{width}_{height}'
        if not hasattr(cls, prop_name):
            setattr(cls, prop_name, cls(width, height))
        return getattr(cls, prop_name)

    def background(self):
        """绘制背景"""
        Draw(self._image).rectangle([(0, 0), self._image.size],
                                    fill=random_color(230, 255))

    def smooth(self):
        """平滑图像"""
        return self._image.filter(ImageFilter.SMOOTH)

    def curve(self, width=4, number=6, color=None):
        """绘制曲线"""
        dx, height = self._image.size
        dx /= number
        path = [(dx * i, random.randint(0, height))
                for i in range(1, number)]
        bcoefs = Bezier().make_bezier(number - 1)
        points = []
        for coefs in bcoefs:
            points.append(tuple(sum([coef * p for coef, p in zip(coefs, ps)])
                                for ps in zip(*path)))
        Draw(self._image).line(points, fill=color if color else self._color, width=width)

    def noise(self, number=50, level=2, color=None):
        """绘制扰码"""
        width, height = self._image.size
        dx, dy = width / 10, height / 10
        width, height = width - dx, height - dy
        draw = Draw(self._image)
        for i in range(number):
            x = int(random.uniform(dx, width))
            y = int(random.uniform(dy, height))
            draw.line(((x, y), (x + level, y)),
                      fill=color if color else self._color, width=level)

    def text(self, captcha_text, fonts, font_sizes=None, drawings=None, squeeze_factor=0.75, color=None):
        """绘制文本"""
        color = color if color else self._color
        fonts = tuple([truetype(name, size)
                       for name in fonts
                       for size in font_sizes or (65, 70, 75)])
        draw = Draw(self._image)
        char_images = []
        for c in captcha_text:
            font = random.choice(fonts)
            c_width, c_height = draw.textsize(c, font=font)
            char_image = Image.new('RGB', (c_width, c_height), (0, 0, 0))
            char_draw = Draw(char_image)
            char_draw.text((0, 0), c, font=font, fill=color)
            char_image = char_image.crop(char_image.getbbox())
            for drawing in drawings:
                d = getattr(self, drawing)
                char_image = d(char_image)
            char_images.append(char_image)
        width, height = self._image.size
        offset = int((width - sum(int(i.size[0] * squeeze_factor)
                                  for i in char_images[:-1]) -
                      char_images[-1].size[0]) / 2)
        for char_image in char_images:
            c_width, c_height = char_image.size
            mask = char_image.convert('L').point(lambda i: i * 1.97)
            self._image.paste(char_image,
                        (offset, int((height - c_height) / 2)),
                        mask)
            offset += int(c_width * squeeze_factor)

    @staticmethod
    def warp(image, dx_factor=0.3, dy_factor=0.3):
        """图像扭曲"""
        width, height = image.size
        dx = width * dx_factor
        dy = height * dy_factor
        x1 = int(random.uniform(-dx, dx))
        y1 = int(random.uniform(-dy, dy))
        x2 = int(random.uniform(-dx, dx))
        y2 = int(random.uniform(-dy, dy))
        warp_image = Image.new(
            'RGB',
            (width + abs(x1) + abs(x2), height + abs(y1) + abs(y2)))
        warp_image.paste(image, (abs(x1), abs(y1)))
        width2, height2 = warp_image.size
        return warp_image.transform(
            (width, height),
            Image.QUAD,
            (x1, y1, -x1, height2 - y2, width2 + x2, height2 + y2, width2 - x2, -y1))

    @staticmethod
    def offset(image, dx_factor=0.1, dy_factor=0.2):
        """图像偏移"""
        width, height = image.size
        dx = int(random.random() * width * dx_factor)
        dy = int(random.random() * height * dy_factor)
        offset_image = Image.new('RGB', (width + dx, height + dy))
        offset_image.paste(image, (dx, dy))
        return offset_image

    @staticmethod
    def rotate(image, angle=25):
        """图像旋转"""
        return image.rotate(random.uniform(-angle, angle),
                            Image.BILINEAR, expand=1)

    def generate(self, captcha_text='', fmt='PNG'):
        """生成验证码(文字和图片)"""
        self._image = Image.new('RGB', (self._width, self._height), (255, 255, 255))
        self.background()
        self.text(captcha_text, self._fonts,
                  drawings=['warp', 'rotate', 'offset'])
        self.curve()
        self.noise()
        self.smooth()
        image_bytes = BytesIO()
        self._image.save(image_bytes, format=fmt)
        return image_bytes.getvalue()
def pascal_row(n=0):
    """生成Pascal三角第n行"""
    result = [1]
    x, numerator = 1, n
    for denominator in range(1, n // 2 + 1):
        x *= numerator
        x /= denominator
        result.append(x)
        numerator -= 1
    if n & 1 == 0:
        result.extend(reversed(result[:-1]))
    else:
        result.extend(reversed(result))
    return result
# def random_color(start=0, end=255, opacity=255):
def random_color(start=100, end=255, opacity=255):
    """获得随机颜色"""
    red = random.randint(start, end)
    green = random.randint(start, end)
    blue = random.randint(start, end)
    if opacity is None:
        return red, green, blue
    return red, green, blue, opacity
def get_captcha_text(length=4):
    ALL_CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    selected_chars = random.choices(ALL_CHARS, k=length)
    return ''.join(selected_chars)
# 点击一下验证码，就执行一次该函数并且将验证码加入session，方便post登录字段时在login函数验证验证码
def get_pic(request,num):
    captcha_text = get_captcha_text()
    image = Captcha.instance().generate(captcha_text)
    request.session['vcode'] = captcha_text
    return HttpResponse(image,'image.png')

def home(request):
    blog_content_type = ContentType.objects.get_for_model(Blog)
    read_nums ,dates= get_seven_days_read_date(blog_content_type)

    today_hot_data = get_today_hot_data(blog_content_type)
    yesterday_hot_data = get_yesterday_hot_data(blog_content_type)

    # 获取7天热门博客的缓存数据，字典类型
    hot_blogs_for_seven_days = cache.get('hot_blogs_for_seven_days')
    #如果缓存表中无该数据
    if hot_blogs_for_seven_days is None:
        hot_blogs_for_seven_days = get_seven_days_hot_blog()
        #将该数据以键值加到缓存表中,并设置缓存时间/s
        cache.set('hot_blogs_for_seven_days',hot_blogs_for_seven_days,3600)
        print("计算")
    else:
        print("使用缓存")
    context={}
    context['read_nums'] = read_nums
    context['dates'] = dates
    context['today_hot_data'] = today_hot_data
    context['yesterday_hot_data'] = yesterday_hot_data
    context['hot_blogs_for_seven_days'] = hot_blogs_for_seven_days
    return render(request,'home.html',context)
@csrf_exempt
def login(request):
    # username = request.POST.get('username','')  #取出POST类似字典中的username数据，若没有就默认空字符串
    # password = request.POST.get('password','')
    # user = auth.authenticate(request,username=username,password=password) #验证用户，如果没问题，返回真实user，否则返回none
    # #得到发送请求的网址，没有解析出别名为home的网址
    # referer = request.META.get("HTTP_REFERER",reverse('home'))
    # if user is not None:
    #     #如果验证通过，则登录用户
    #     auth.login(request,user)
    #     return redirect(referer)
    # else:
    #     return render(request,'error.html',{'message':"用户名或密码不正确"})
    vcode_msg = ''
    if request.method == 'POST':
        # 如果表单提交用的是 POST请求，那么该视图将再次
        # 创建一个表单实例并使用请求中的数据填充它
        login_form = LoginForm(request.POST)   #login_form.errors 实际上是个dict  login_form.errors.username 如果存在则说明username字段出错
        vcode = request.POST.get('vcode')
        print(request.session.items())
        if vcode.upper() == request.session['vcode'].upper():
            if login_form.is_valid(): #该方法会判断字段是否符合我们定义
                user = login_form.cleaned_data['user']
                auth.login(request,user)
                return redirect(request.GET.get('from', reverse('home')))
                #以下注释内容都在forms.py中进行处理
                #经过验证后的数据（填写符合规范），字典
                # username = login_form.cleaned_data['username']
                # password = login_form.cleaned_data['password']
                # user = auth.authenticate(request,username=username,password = password)
                # if user is not None:
                #     auth.login(request,user)
                #     #跳转到点击登录的那个页面，否则回到首页
                #     return redirect(request.GET.get('from',reverse('home')))
                # else:
                #     login_form.add_error(None,'用户名或密码不正确')
        else:
            vcode_msg = '验证码错误'

    else:
        # 如果我们访问这个视图用的是GET请求，它会创建一个空的表单实例并将其放置在
        # 模板上下文中进行渲染。这是我们在首次访问这个URL时能预料到会发生的情况。
        login_form = LoginForm()
    context = {}
    context['login_form'] = login_form
    context['vcode_msg'] = vcode_msg
    return render(request,'login.html',context)

def login_for_modal(request):
    login_form = LoginForm(request.POST)
    data = {}
    if login_form.is_valid():
        user = login_form.cleaned_data['user']
        auth.login(request, user)
        data['status'] = 'SUCCESS'
    else:
       data['status'] = 'ERROR'
    return JsonResponse(data)
def register(request):
    if request.method == 'POST':
        reg_form = RegForm(request.POST)
        #数据是有效的即经过了验证
        if reg_form.is_valid():
            username = reg_form.cleaned_data['username']
            email = reg_form.cleaned_data['email']
            password = reg_form.cleaned_data['password']
            #创建用户
            user = User.objects.create_user(username,email,password)
            user.save()

            user = auth.authenticate(username=username,password=password)  #验证用户
            # 登录用户,必须要request参数
            auth.login(request,user)
            # 跳转到点击注册的那个页面
            return redirect(request.GET.get('from', reverse('home')))
    else:
        reg_form = RegForm()
    context = {}
    context['reg_form'] = reg_form
    return render(request,'register.html',context)

def logout(request):
    # 自带的登出功能
    auth.logout(request)
    # reverse('home')返回name='home'对应的url字符串''
    return redirect(request.GET.get('from', reverse('home')))

def user_info(request):
    context = {}
    return render(request,'user_info.html',context)
