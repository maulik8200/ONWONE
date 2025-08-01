from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models import Count, Q, Min, Max
from django.http import HttpResponseBadRequest
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone


from urllib.parse import urlparse


from datetime import datetime, timedelta
from decimal import Decimal


import random
import pandas as pd
import requests


from .models import *


# Create your views here.


def home(request):
    slider_items = SliderItem.objects.all()
    trending_products = Product.objects.filter(trending_now=True)
    popular_products = Product.objects.filter(Most_popular_products=True)

    context = {
        'slider_items': slider_items,
        'trending_products': trending_products,
        'popular_products': popular_products,
    }
    return render(request, 'index.html', context)

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

    # Price filtering using discount_price
    if min_price and max_price:
        try:
            product_list = product_list.filter(
                Q(discount_price__gte=float(min_price), discount_price__lte=float(max_price))
            )
        except ValueError:
            pass

    product_list = product_list.distinct()

    paginator = Paginator(product_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Calculate min/max from discount_price (fallback to price if null)
    price_range = Product.objects.aggregate(
        min_price=Min('discount_price'),
        max_price=Max('discount_price')
    )
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

@login_required(login_url='/login/')
def wishlist(request):
    return render(request, 'wishlist.html')

@login_required(login_url='/login/')
def cart(request):
    cart_items = CartItem.objects.filter(user=request.user)
    subtotal = sum(item.subtotal() for item in cart_items)

    gst_rate = Decimal('0.08')
    gst = int(Decimal(subtotal) * gst_rate)

    delivery_charge = 0 if subtotal >= 500 else 50

    # Get coupon info from session
    coupon_code = request.session.get('coupon_code')
    coupon_discount_percent = request.session.get('coupon_discount', 0)
    
    # Convert to Decimal before calculation
    discount_amount = int(Decimal(subtotal) * (Decimal(coupon_discount_percent) / Decimal(100)))

    total = int(subtotal - discount_amount + gst + delivery_charge)

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'subtotal': int(subtotal),
        'gst': gst,
        'delivery_charge': delivery_charge,
        'discount_amount': discount_amount,
        'coupon_discount_percent': coupon_discount_percent,
        'total': total,
        'code': coupon_code,
    })

@login_required(login_url='/login/')
def apply_coupon(request):
    if request.method == 'POST':
        code = request.POST.get('coupon_code')
        try:
            coupon = Coupon.objects.get(code__iexact=code, active=True)
            request.session['coupon_code'] = coupon.code
            request.session['coupon_discount'] = coupon.discount_percent
            messages.success(request, f"Coupon '{code}' applied successfully!")
        except Coupon.DoesNotExist:
            request.session['coupon_code'] = None
            request.session['coupon_discount'] = 0
            messages.error(request, "Invalid or inactive coupon code.")
    return redirect('cart')  # or whatever your cart page URL name is

def remove_coupon(request):
    request.session['coupon_code'] = None
    request.session['coupon_discount'] = 0
    messages.success(request, "Coupon removed successfully.")
    return redirect('cart')  # or whatever your cart page URL name is

@login_required(login_url='/login/')
def add_to_cart(request, id):
    product = get_object_or_404(Product, id=id)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        size_id = request.POST.get('size')

        if quantity < 1 or quantity > 4:
            return HttpResponseBadRequest("Quantity must be between 1 and 4.")

        size = Size.objects.get(id=size_id) if size_id else None

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            size=size,
            defaults={'quantity': quantity}
        )
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return redirect('cart')  # Redirect to cart page

    return redirect('product_detail', id=id)

@login_required(login_url='/login/')
def remove_from_cart(request, id):
    item = get_object_or_404(CartItem, id=id, user=request.user)
    item.delete()
    return redirect('cart')


@login_required(login_url='/login/')
def add_address(request):
    user = request.user
    billing_addresses = user.billing_addresses.all()

    if request.method == "POST":
        selected_id = request.POST.get('selected_address_id')
        selected_address = get_object_or_404(BillingAddress, id=selected_id, user=user)

        # Save the selected address ID in session
        request.session['selected_address_id'] = selected_address.id

        return redirect('checkout')  # Or 'checkout'

    return render(request, 'add_address.html', {'billing_addresses': billing_addresses})

@login_required(login_url='/login/')
def checkout(request):
    user = request.user
    cart_items = CartItem.objects.filter(user=user)
    subtotal = sum(item.subtotal() for item in cart_items) 

    gst_rate = Decimal('0.08')
    gst = int(Decimal(subtotal) * gst_rate)

    delivery_charge = 0 if subtotal >= 500 else 50

    coupon_code = request.session.get('coupon_code')
    coupon_discount_percent = request.session.get('coupon_discount', 0)
    discount_amount = int(Decimal(subtotal) * (Decimal(coupon_discount_percent) / Decimal(100)))

    total = int(subtotal - discount_amount + gst + delivery_charge)

    selected_address_id = request.session.get('selected_address_id')
    selected_address = None
    if selected_address_id:
        selected_address = get_object_or_404(BillingAddress, id=selected_address_id, user=user)

    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'subtotal': int(subtotal),
        'gst': gst,
        'delivery_charge': delivery_charge,
        'discount_amount': discount_amount,
        'coupon_discount_percent': coupon_discount_percent,
        'total': total,
        'code': coupon_code,
        'selected_address': selected_address,
    })







def login(request):
    # Step 1: Capture previous page and store it in session
    if request.method == 'GET':
        referer = request.META.get('HTTP_REFERER')
        if referer and 'register' not in referer:
            request.session['next_url'] = referer

    if request.method == 'POST':
        email = request.POST.get('dzName')
        password = request.POST.get('password')

        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)

            if user is not None:
                auth_login(request, user)
                messages.success(request, 'Logged in successfully.')

                # Step 2: Redirect to the previous page if it's not the register page
                next_url = request.session.get('next_url')
                if next_url and 'register' not in next_url:
                    return redirect(next_url)
                else:
                    return redirect('home')

            else:
                messages.error(request, 'Invalid email or password.')
        except User.DoesNotExist:
            messages.error(request, 'User with this email does not exist.')

    return render(request, 'login.html')

def register(request):
    if request.method == 'POST':
        # Step 2: OTP verification
        if 'otp' in request.POST:
            entered_otp = request.POST.get('otp')
            original_otp = request.session.get('otp')
            otp_created_at_str = request.session.get('otp_created_at')

            name = request.session.get('name')
            mobile = request.session.get('mobile')
            email = request.session.get('email')
            password = request.session.get('password')

            # Check session data presence
            if not all([original_otp, otp_created_at_str, name, mobile, email, password]):
                messages.error(request, "Session expired. Please register again.")
                return redirect('register')

            try:
                otp_created_at = timezone.datetime.fromisoformat(otp_created_at_str)
            except Exception:
                messages.error(request, "Invalid OTP timestamp. Please try again.")
                return redirect('register')

            if timezone.now() > otp_created_at + timedelta(minutes=5):
                messages.error(request, "OTP expired. Please register again.")
                request.session.flush()
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

        # Step 1: Form submitted
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

                # Save session data and timestamp
                request.session['otp'] = otp
                request.session['otp_created_at'] = timezone.now().isoformat()
                request.session['name'] = name
                request.session['mobile'] = mobile
                request.session['email'] = email
                request.session['password'] = password

                # Prepare and send email
                subject = 'Your OTP Code for Onwone Registration'
                from_email = 'noreply@onwone.com'
                to = [email]

                context = {
                    'brand': 'Onwone',
                    'otp': otp,
                    'user_name': name
                }

                html_content = render_to_string('emails/otp_email.html', context)
                text_content = f"Hi {name},\n\nYour OTP for Onwone registration is: {otp}\n\nIf you didn’t request this, please ignore this email.\n\nThank you,\nOnwone Team"

                email_message = EmailMultiAlternatives(subject, text_content, from_email, to)
                email_message.attach_alternative(html_content, "text/html")

                try:
                    email_message.send()
                    messages.info(request, f"OTP sent to {email}. Please check your inbox.")
                except Exception as e:
                    messages.error(request, f"Failed to send OTP: {str(e)}")
                    return redirect('register')

                return render(request, 'register.html', {'otp_required': True})

    return render(request, 'register.html')


def logout(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')  # or 'login' or wherever you want to redirect after logout

@login_required(login_url='/login/')
def account(request):
    billing_addresses = request.user.billing_addresses.all()  # Use related_name

    return render(request, 'account.html', {'billing_addresses': billing_addresses})

@login_required(login_url='/login/')
def account_billing_address(request):
    if request.method == 'POST':
        user = request.user
        data = request.POST.getlist('dzName')

        billing_address = BillingAddress.objects.create(
            user=user,
            first_name=data[0],
            company_name=data[1],
            country=data[2],
            street_address_1=data[3],
            street_address_2=data[4],
            city=data[5],
            state=data[6],
            postcode=data[7],
            phone=data[8],
            email=data[9],
        )

        return redirect('account')

    return render(request, 'account_billing_address.html')

@login_required(login_url='/login/')
def account_billing_address_2(request):
    if request.method == 'POST':
        user = request.user
        data = request.POST.getlist('dzName')

        billing_address = BillingAddress.objects.create(
            user=user,
            first_name=data[0],
            company_name=data[1],
            country=data[2],
            street_address_1=data[3],
            street_address_2=data[4],
            city=data[5],
            state=data[6],
            postcode=data[7],
            phone=data[8],
            email=data[9],
        )

        return redirect('add_address')

    return render(request, 'account_billing_address.html')



@login_required(login_url='/login/')
def edit_billing_address(request, address_id):
    billing_address = get_object_or_404(BillingAddress, id=address_id, user=request.user)

    if request.method == 'POST':
        billing_address.first_name = request.POST.get('first_name')
        billing_address.company_name = request.POST.get('company_name')
        billing_address.country = request.POST.get('country')
        billing_address.street_address_1 = request.POST.get('street_address_1')
        billing_address.street_address_2 = request.POST.get('street_address_2')
        billing_address.city = request.POST.get('city')
        billing_address.state = request.POST.get('state')
        billing_address.postcode = request.POST.get('postcode')
        billing_address.phone = request.POST.get('phone')
        billing_address.email = request.POST.get('email')
        billing_address.save()

        return redirect('account')

    return render(request, 'edit_billing_address.html', {'billing_address': billing_address})


@login_required(login_url='/login/')
def remove_billing_address(request, address_id):
    billing_address = get_object_or_404(BillingAddress, id=address_id, user=request.user)
    billing_address.delete()
    return redirect('account')

# Define size sequence to support "S to 5XL"
SIZE_ORDER = ['S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL', '5XL']

def parse_size_range(size_value):
    sizes = []
    size_value = str(size_value).replace(" ", "").upper()  # normalize
    if 'TO' in size_value:
        try:
            start, end = size_value.split('TO')
            start_index = SIZE_ORDER.index(start)
            end_index = SIZE_ORDER.index(end)
            if start_index <= end_index:
                sizes = SIZE_ORDER[start_index:end_index + 1]
        except Exception as e:
            print(f"Size range parse error: {e}")
    else:
        sizes = [s.strip() for s in size_value.split(',') if s.strip() in SIZE_ORDER]
    return sizes


def upload_products_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        df = pd.read_excel(excel_file)

        for _, row in df.iterrows():
            try:
                product, created = Product.objects.get_or_create(
                    sku=row['Sku Id'],
                    defaults={
                        'title': row['Name'],
                        'price': row['MRP'],
                        'discount_price': row['Selling Price'],
                        'description': row['Description'],
                        'mini_description': row['Description'],
                        'in_stock': row['Quantity'] > 0,
                        'manufacturer': '',
                        'country_of_origin': '',
                        'department': '',
                        'included_components': '',
                        'dimensions': f"{row['Packaging Length (in cm)']}x{row['Packaging Breadth (in cm)']}x{row['Packaging Height (in cm)']}",
                        'brand': '',
                    }
                )

                # Sizes (including "S to 5XL")
                if pd.notna(row['Size']):
                    parsed_sizes = parse_size_range(row['Size'])
                    for size_name in parsed_sizes:
                        size_obj, _ = Size.objects.get_or_create(name=size_name)
                        product.sizes.add(size_obj)

                # Colors
                if pd.notna(row['Colour']):
                    for color_name in str(row['Colour']).split(','):
                        color_obj, _ = Color.objects.get_or_create(name=color_name.strip(), defaults={'hex_code': '#000000'})
                        product.colors.add(color_obj)

                # Categories
                if pd.notna(row['Product Type']):
                    for cat_name in str(row['Product Type']).split(','):
                        cat_obj, _ = Category.objects.get_or_create(name=cat_name.strip())
                        product.categories.add(cat_obj)

                # Tags
                if pd.notna(row['attr1_Attribute Name']):
                    for tag_name in str(row['attr1_Attribute Name']).split(','):
                        tag_obj, _ = Tag.objects.get_or_create(name=tag_name.strip())
                        product.tags.add(tag_obj)

                # Product Images (download and save)
                for i in range(1, 11):
                    col_name = f'Image {i}'
                    if pd.notna(row.get(col_name)):
                        image_url = row[col_name]
                        try:
                            response = requests.get(image_url, timeout=10)
                            if response.status_code == 200:
                                image_name = os.path.basename(urlparse(image_url).path)
                                image_file = ContentFile(response.content, name=image_name)

                                product_image = ProductImage()
                                product_image.image.save(image_name, image_file)
                                product_image.alt_text = product.title
                                product_image.save()

                                product.images.add(product_image)
                        except Exception as e:
                            print(f"Failed to download image from {image_url}: {e}")

                # Description Box
                if pd.notna(row['Description']):
                    pdbox, _ = ProductDescriptionBox.objects.get_or_create(
                        title="Overview",
                        description=row['Description'][:250]
                    )
                    product.ProductDescriptionBoxes.add(pdbox)

                product.save()

            except Exception as e:
                print(f"Error processing row {row.get('Sku Id', 'N/A')}: {e}")

        return redirect('upload_products_excel')

    return render(request, 'upload_excel.html')