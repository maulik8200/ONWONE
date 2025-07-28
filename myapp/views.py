from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models import Count, Q, Min, Max
from django.http import HttpResponseBadRequest
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages

import random

from .models import *

# Create your views here.


def home(request):
    slider_items = SliderItem.objects.all
    return render(request, 'index.html', {'slider_items': slider_items})

def shop(request):
    shop_banners = ShopBanner.objects.all()

    color_filter = request.GET.get('color')
    size_filter = request.GET.get('size')
    category_filter = request.GET.get('category')
    tag_filter = request.GET.get('tag')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    product_list = Product.objects.all()

    # Apply filters
    if color_filter:
        product_list = product_list.filter(colors__hex_code=color_filter)
    if size_filter:
        product_list = product_list.filter(sizes__name=size_filter)
    if category_filter:
        product_list = product_list.filter(categories__name=category_filter)
    if tag_filter:
        product_list = product_list.filter(tags__name=tag_filter)
    if min_price and max_price:
        try:
            product_list = product_list.filter(price__gte=float(min_price), price__lte=float(max_price))
        except ValueError:
            pass

    product_list = product_list.distinct()

    paginator = Paginator(product_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    price_range = Product.objects.aggregate(min_price=Min('price'), max_price=Max('price'))
    min_db_price = int(price_range['min_price'] or 0)
    max_db_price = int(price_range['max_price'] or 1000)

    return render(request, 'shop.html', {
        'shop_banners': shop_banners,
        'products': page_obj,
        'page_obj': page_obj,
        'total_products': paginator.count,
        'colors': Color.objects.all(),
        'sizes': Size.objects.all(),
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'selected_color': color_filter,
        'selected_size': size_filter,
        'selected_category': category_filter,
        'selected_tag': tag_filter,
        'price_min_value': min_db_price,
        'price_max_value': max_db_price,
        'min_price': min_price or min_db_price,
        'max_price': max_price or max_db_price,
    })



def product_detail(request, id):
    product = get_object_or_404(Product, id=id)

    # Get categories and tags
    product_categories = product.categories.all()
    product_tags = product.tags.all()

    # Handle POST request for quantity validation
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity < 1 or quantity > 4:
                return HttpResponseBadRequest("Quantity must be between 1 and 4.")
        except ValueError:
            return HttpResponseBadRequest("Invalid quantity.")

        # Process form data like cart addition, etc. here...

    # Filter related products
    related_products = Product.objects.filter(
        Q(categories__in=product_categories) | Q(tags__in=product_tags)
    ).exclude(id=product.id).annotate( # type: ignore
        same_categories=Count('categories', filter=Q(categories__in=product_categories), distinct=True),
        same_tags=Count('tags', filter=Q(tags__in=product_tags), distinct=True),
    ).annotate(
        total_match=Count('categories', filter=Q(categories__in=product_categories), distinct=True) +
                    Count('tags', filter=Q(tags__in=product_tags), distinct=True)
    ).order_by('-total_match')[:10]

    return render(request, 'product_detail.html', {
        'product': product,
        'related_products': related_products
    })











def about(request):
    return render(request, 'about.html')

def faq(request):
    return render(request, 'faq.html')

def contact(request):
    return render(request, 'contact.html')

def wishlist(request):
    return render(request, 'wishlist.html')

def cart(request):
    return render(request, 'cart.html')









def login(request):
    if request.method == 'POST':
        email = request.POST.get('dzName')
        password = request.POST.get('password')

        try:
            # You used email as username during registration
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)

            if user is not None:
                auth_login(request, user)
                messages.success(request, 'Logged in successfully.')
                return redirect('home')  # Redirect after login
            else:
                messages.error(request, 'Invalid email or password.')
        except User.DoesNotExist:
            messages.error(request, 'User with this email does not exist.')

    return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        # Step 2: OTP Verification
        if 'otp' in request.POST:
            entered_otp = request.POST.get('otp')
            original_otp = request.session.get('otp')
            name = request.session.get('name')
            mobile = request.session.get('mobile')
            email = request.session.get('email')
            password = request.session.get('password')

            # Check if all session fields are still available
            if not all([original_otp, name, mobile, email, password]):
                messages.error(request, "Session expired. Please register again.")
                return redirect('register')

            if str(entered_otp) == str(original_otp):
                if not User.objects.filter(email=email).exists():
                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        first_name=name,
                        last_name=mobile
                    )
                    user.save()
                    messages.success(request, "Registration successful.")
                    request.session.flush()
                    return redirect('login')
                else:
                    messages.error(request, "Email already registered.")
            else:
                messages.error(request, "Invalid OTP. Please try again.")
            return render(request, 'register.html', {'otp_required': True})

        # Step 1: Form submission
        else:
            name = request.POST.get('name')
            mobile = request.POST.get('mobile')
            email = request.POST.get('dzName')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already registered.")
                return redirect('register')
            elif password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return redirect('register')
            else:
                otp = random.randint(100000, 999999)
                request.session['otp'] = otp
                request.session['name'] = name
                request.session['mobile'] = mobile
                request.session['email'] = email
                request.session['password'] = password

                try:
                    send_mail(
                        subject='Your OTP Code',
                        message=f'Your OTP for registration is: {otp}',
                        from_email='noreply@yourdomain.com',
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    messages.info(request, f"OTP sent to {email}. Please check your inbox.")
                except Exception as e:
                    messages.error(request, f"Failed to send OTP: {str(e)}")
                    return redirect('register')

                return render(request, 'register.html', {'otp_required': True})

    return render(request, 'register.html')