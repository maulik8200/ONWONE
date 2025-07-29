from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.db.models import Count, Q, Min, Max
from django.http import HttpResponseBadRequest
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from django.core.files.base import ContentFile
from urllib.parse import urlparse


import random
import pandas as pd
import requests


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


def account(request):
    billing_address = None
    if request.user.is_authenticated:
        try:
            billing_address = request.user.billing_address
        except BillingAddress.DoesNotExist:
            billing_address = None

    return render(request, 'account.html', {'billing_address': billing_address})

def account_billing_address(request):
    if request.method == 'POST':
        user = request.user
        data = request.POST

        billing_data = {
            'first_name': data.getlist('dzName')[0],
            'company_name': data.getlist('dzName')[1],
            'country': data.getlist('dzName')[2],
            'street_address_1': data.getlist('dzName')[3],
            'street_address_2': data.getlist('dzName')[4],
            'city': data.getlist('dzName')[5],
            'state': data.getlist('dzName')[6],
            'postcode': data.getlist('dzName')[7],
            'phone': data.getlist('dzName')[8],
            'email': data.getlist('dzName')[9],
        }

        BillingAddress.objects.update_or_create(user=user, defaults=billing_data)

        return redirect('account')  # redirect after save

    return render(request, 'account_billing_address.html')



def edit_billing_address(request):
    try:
        billing_address = request.user.billing_address
    except BillingAddress.DoesNotExist:
        billing_address = None

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        company_name = request.POST.get('company_name')
        country = request.POST.get('country')
        street_address_1 = request.POST.get('street_address_1')
        street_address_2 = request.POST.get('street_address_2')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postcode = request.POST.get('postcode')
        phone = request.POST.get('phone')
        email = request.POST.get('email')


        billing_address.first_name = first_name
        billing_address.company_name = company_name
        billing_address.country = country
        billing_address.street_address_1 = street_address_1
        billing_address.street_address_2 = street_address_2
        billing_address.city = city
        billing_address.state = state
        billing_address.postcode = postcode
        billing_address.phone = phone
        billing_address.email = email
        billing_address.save()

        return redirect('account')

    return render(request, 'edit_billing_address.html', {'billing_address': billing_address})



def remove_billing_address(request):
    try:
        billing_address = request.user.billing_address
        billing_address.delete()
    except:
        pass
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