from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import Product, Profile, Category, Subtype, Shop, OrderReview, UserAddress, BuyNowOrders, AddToCartProducts, Order, OrderItem
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import json
from django.db.models import Count, F




# ---------------- HOME ----------------


def home(request):
    if request.user.is_authenticated:
        logout(request)
    request.session.flush()

    reviews = (
        OrderReview.objects
        .select_related('user__profile', 'product', 'order')
        .prefetch_related('order__items__product')
        .order_by('-rating', '-created_at')[:12]
    )

    # 🔥 attach first cart product for cart reviews
    for review in reviews:
        if review.product:
            review.display_product = review.product
        elif review.order:
            first_item = review.order.items.first()
            review.display_product = first_item.product if first_item else None
        else:
            review.display_product = None

    return render(request, 'home.html', {
        'reviews': reviews
    })




# ---------- REGISTER ----------
def register_view(request):
    if request.method == "POST":
        role = request.POST.get('role')
        username = request.POST.get('username')
        password = request.POST.get('password')
        fullname = request.POST.get('fullname')
        contact = request.POST.get('contact')
        email = request.POST.get('email')

        # prevent admin self registration
        if role == "admin":
            messages.error(request, "Admin cannot register directly.", extra_tags='auth')
            return redirect('home')

        # check username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists. Try another one.", extra_tags='auth')
            return redirect('home')

        # create django user
        user = User.objects.create_user(username=username, password=password)

        # create profile for seller/user
        Profile.objects.create(
            user=user,
            role=role,
            fullname=fullname,
            contact_number=contact,
            email=email
        )

        messages.success(request, "Registration successful! Please login.", extra_tags='auth')
        return redirect('home')

    # if someone opens /register/ directly
    return redirect('home')


# ---------- LOGIN ----------
def login_view(request):
    if request.method == "POST":
        role = request.POST.get('role')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # --------- ADMIN LOGIN (hardcoded) ----------
        if role == "admin":
            if username == "admin" and password == "admin123":
                request.session['role'] = 'admin'
                request.session['username'] = 'admin'
                messages.success(request, "Welcome Admin!")
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Invalid admin credentials.", extra_tags='auth')
                return redirect('home')

        # --------- SELLER / USER LOGIN (DB) ----------
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password.", extra_tags='auth')
            return redirect('home')

        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            messages.error(request, "Account profile not found.", extra_tags='auth')
            return redirect('home')

        # check selected role matches stored role
        if profile.role != role:
            messages.error(request, "Selected role does not match your account.", extra_tags='auth')
            return redirect('home')

        # login and set session role
        login(request, user)
        request.session['role'] = role

        if role == "seller":
            messages.success(request, f"Welcome Seller {profile.fullname}!")
            return redirect('seller_dashboard')

        elif role == "user":
            messages.success(request, f"Welcome {profile.fullname}!")
            return redirect('user_dashboard')

        else:
            messages.error(request, "Invalid role.", extra_tags='auth')
            return redirect('home')

    # if someone opens /login/ directly
    return redirect('home')

# ---------- LOGOUT ----------
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('home')




# ---------- DASHBOARDS ----------



def admin_dashboard(request):
    if request.session.get('role') != 'admin':
        return redirect('home')

    total_sellers = Profile.objects.filter(role='seller').count()
    total_users = Profile.objects.filter(role='user').count()
    total_products = Product.objects.count()

    total_orders = (
        BuyNowOrders.objects.count() +
        OrderItem.objects.count()
    )

    sellers = Profile.objects.filter(role='seller')
    users = Profile.objects.filter(role='user')

    context = {
        'total_sellers': total_sellers,
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'sellers': sellers,
        'users': users,
    }

    return render(request, 'admin_dashboard.html', context)


@login_required(login_url='home')
def seller_dashboard(request):
    if request.session.get('role') != 'seller':
        return redirect('home')

    profile = get_object_or_404(Profile, user=request.user)

    # Total products by this seller
    product_count = Product.objects.filter(seller=profile).count()

    # Total Buy Now orders for this seller
    buy_now_orders_count = BuyNowOrders.objects.filter(product__seller=profile).count()

    # Total Cart orders containing this seller's products
    cart_orders_count = Order.objects.filter(items__product__seller=profile).distinct().count()

    total_orders = buy_now_orders_count + cart_orders_count

    # Categories for product creation
    categories = Category.objects.prefetch_related('subtypes').all()

    categories_json = [
        {
            'id': cat.id,
            'name': cat.name,
            'subtypes': [{'id': st.id, 'name': st.name} for st in cat.subtypes.all()]
        }
        for cat in categories
    ]

    # Get the "Others" category explicitly
    others = Category.objects.filter(name="Others").first()

    context = {
        'profile': profile,
        'product_count': product_count,
        'total_orders': total_orders,
        'categories': categories,
        'categories_json': categories_json,
        'others': others,
    }

    return render(request, "seller_dashboard.html", context)


@login_required(login_url='home')
def user_dashboard(request):
    if request.session.get('role') != 'user':
        return redirect('home')

    products = Product.objects.select_related(
        'seller', 'category', 'subtype'
    ).all()

    product_data = []
    for product in products:
        shop = Shop.objects.filter(seller=product.seller).first()
        product_data.append({
            'product': product,
            'shop_name': shop.shop_name if shop else "No Shop"
        })

    cart_count = AddToCartProducts.objects.filter(user=request.user).count()

    return render(request, "user_dashboard.html", {
        'product_data': product_data,
        'cart_count': cart_count
    })





def delete_seller(request, seller_id):
    # Only admin can delete
    if request.session.get('role') != 'admin':
        messages.error(request, "Unauthorized action.")
        return redirect('home')

    # Get the seller Profile object
    seller_profile = get_object_or_404(Profile, id=seller_id, role='seller')

    # Optionally, delete the linked Django User as well
    user = seller_profile.user
    seller_name = seller_profile.fullname

    seller_profile.delete()  # Delete the profile first
    user.delete()            # Delete the User

    messages.success(request, f"Seller '{seller_name}' deleted successfully.")
    return redirect('admin_dashboard')


@login_required(login_url='home')
def seller_profile(request):
    if request.session.get('role') != 'seller':
        messages.error(request, "Unauthorized access.")
        return redirect('home')

    profile, created = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            'role': 'seller',
            'fullname': '',
            'contact_number': '',
            'email': ''
        }
    )

    return render(request, 'seller_profile.html', {'profile': profile})



# Update profile
@login_required(login_url='home')
def update_seller_profile(request):
    if request.method == "POST":
        if request.session.get('role') != 'seller':
            messages.error(request, "Unauthorized action.")
            return redirect('home')

        user = request.user

        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'role': 'seller',
                'fullname': '',
                'contact_number': '',
                'email': ''
            }
        )

        # text fields
        profile.fullname = request.POST.get('fullname')
        profile.contact_number = request.POST.get('contact')
        profile.email = request.POST.get('email')

        # 🔥 handle profile image upload
        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']

        profile.save()

        # optional password change
        password = request.POST.get('password')
        if password:
            user.set_password(password)
            user.save()

        messages.success(request, "Profile updated successfully!")
        return redirect('seller_profile')

    return redirect('seller_dashboard')



@login_required
def add_shop(request):
    if request.session.get('role') != 'seller':
        messages.error(request, "Unauthorized access")
        return redirect('seller_dashboard')

    profile = get_object_or_404(Profile, user=request.user)

    # ❗ Block if shop already exists
    if profile.shops.exists():
        messages.error(request, "You can add only one shop.")
        return redirect('seller_dashboard')

    if request.method == "POST":
        shop_name = request.POST.get('shop_name')
        shop_address = request.POST.get('shop_address')
        image1 = request.FILES.get('shop_image1')
        image2 = request.FILES.get('shop_image2')

        Shop.objects.create(
            seller=profile,
            shop_name=shop_name,
            shop_address=shop_address,
            shop_image1=image1,
            shop_image2=image2
        )

        messages.success(request, "Shop added successfully!")
        return redirect('seller_dashboard')

    return redirect('seller_dashboard')




@login_required(login_url='home')
def edit_shop(request, shop_id):
    if request.session.get('role') != 'seller':
        messages.error(request, "Unauthorized action.")
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id, seller__user=request.user)

    if request.method == "POST":
        shop.shop_name = request.POST.get('shop_name')
        shop.shop_address = request.POST.get('shop_address')

        if request.FILES.get('shop_image1'):
            shop.shop_image1 = request.FILES.get('shop_image1')

        if request.FILES.get('shop_image2'):
            shop.shop_image2 = request.FILES.get('shop_image2')

        shop.save()
        messages.success(request, "Shop updated successfully!")
        return redirect('seller_profile')

    return redirect('seller_profile')


@login_required(login_url='home')
def delete_shop(request, shop_id):
    if request.session.get('role') != 'seller':
        messages.error(request, "Unauthorized action.")
        return redirect('home')

    shop = get_object_or_404(Shop, id=shop_id)
    shop.delete()
    messages.success(request, "Shop deleted successfully.")
    return redirect('seller_profile')



def admin_view_seller(request, seller_id):
    if request.session.get('role') != 'admin':
        return redirect('home')

    seller_profile = get_object_or_404(Profile, id=seller_id, role='seller')

    # Get shop
    shop = Shop.objects.filter(seller=seller_profile).first()

    # Get products
    products = Product.objects.filter(seller=seller_profile)

    context = {
        'seller': seller_profile,
        'shop': shop,
        'products': products,
    }
    return render(request, 'admin_view_seller.html', context)


def admin_view_products(request):
    if request.session.get('role') != 'admin':
        return redirect('home')

    products = (
        Product.objects
        .select_related('seller', 'category', 'subtype')
        .annotate(
            cart_orders=Count('orderitem', distinct=True),
            buy_now_orders=Count('buynoworders', distinct=True),
        )
        .annotate(
            order_count=F('cart_orders') + F('buy_now_orders')
        )
        .order_by('-order_count', '-created_at')
    )

    return render(request, 'admin_view_products.html', {
        'products': products
    })




def admin_view_orders(request):
    if request.session.get('role') != 'admin':
        return redirect('home')

    # CART ORDERS (Order + OrderItem)
    cart_items = (
        OrderItem.objects
        .select_related(
            'order',
            'order__user',
            'product',
            'product__seller'
        )
        .prefetch_related('product__seller__shops')
        .order_by('-order__created_at')
    )

    # BUY NOW ORDERS
    buy_now_orders = (
        BuyNowOrders.objects
        .select_related(
            'user',
            'product',
            'product__seller'
        )
        .prefetch_related('product__seller__shops')
        .order_by('-created_at')
    )

    return render(request, 'admin_view_orders.html', {
        'cart_items': cart_items,
        'buy_now_orders': buy_now_orders,
    })


# product section

@login_required(login_url='home')
def products_list(request):
    if request.session.get('role') != 'seller':
        messages.error(request, "Unauthorized access.")
        return redirect('home')

    profile = get_object_or_404(Profile, user=request.user)
    products = Product.objects.filter(seller=profile).order_by('-created_at')
    product_count = products.count()

    categories = Category.objects.prefetch_related('subtypes').all()

    # convert to pure Python list (NOT QuerySet)
    categories_data = []
    for cat in categories:
        subtypes_list = []
        for st in cat.subtypes.all():
            subtypes_list.append({
                "id": st.id,
                "name": st.name
            })

        categories_data.append({
            "id": cat.id,
            "name": cat.name,
            "subtypes": subtypes_list
        })

    return render(request, 'product_list.html', {
        'products': products,
        'product_count': product_count,
        'categories': categories,                    
        'categories_json': json.dumps(categories_data)  
    })



@login_required(login_url='home')
def add_product(request):
    if request.session.get('role') != 'seller':
        messages.error(request, "Unauthorized access.")
        return redirect('home')

    profile = get_object_or_404(Profile, user=request.user)
    categories = Category.objects.prefetch_related('subtypes').all()
    others = Category.objects.filter(name="Others").first()

    if request.method == "POST":
        category_id = request.POST.get('category')
        subtype_id = request.POST.get('subtype')
        other_description = request.POST.get('other_description')
        product_type = request.POST.get('type')

        category = get_object_or_404(Category, id=category_id)
        subtype = Subtype.objects.filter(id=subtype_id).first() if subtype_id else None

        Product.objects.create(
            seller=profile,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
            price=request.POST.get('price'),
            image=request.FILES.get('image'),
            category=category,
            subtype=subtype,
            other_description=other_description if category.name == "Others" else None,
            type=product_type
        )
        messages.success(request, "Product added successfully!")
        return redirect('products_list')

    return render(request, 'products_list.html', {'categories': categories, 'others': others})


@login_required(login_url='home')
def edit_product(request, product_id):
    if request.session.get('role') != 'seller':
        messages.error(request, "Unauthorized access.")
        return redirect('home')

    profile = get_object_or_404(Profile, user=request.user)
    product = get_object_or_404(Product, id=product_id, seller=profile)

    if request.method == "POST":
        # correct field names from form
        category_id = request.POST.get('category')
        subtype_id = request.POST.get('subtype')
        other_description = request.POST.get('other_description')
        product_type = request.POST.get('type')  # ✅ fixed

        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.type = product_type              # ✅ fixed

        # set category
        category = get_object_or_404(Category, id=category_id)
        product.category = category

        # set subtype (or None)
        if subtype_id:
            product.subtype = Subtype.objects.filter(id=subtype_id).first()
        else:
            product.subtype = None

        # only keep other_description for "Others" category
        if category.name.lower() == "others":
            product.other_description = other_description
        else:
            product.other_description = None

        # optional image update
        if 'image' in request.FILES:
            product.image = request.FILES['image']

        product.save()
        messages.success(request, "Product updated successfully!")
        return redirect('products_list')

    return redirect('products_list')




@login_required(login_url='home')
def delete_product(request, product_id):
    if request.session.get('role') != 'seller':
        messages.error(request, "Unauthorized access.")
        return redirect('home')

    profile = get_object_or_404(Profile, user=request.user)
    product = get_object_or_404(Product, id=product_id, seller=profile)
    product.delete()
    messages.success(request, "Product deleted successfully!")
    return redirect('products_list')



@login_required(login_url='home')
def create_buy_now_order(request):
    if request.method == "POST":
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity'))

        product = get_object_or_404(Product, id=product_id)

        unit_price = product.price
        delivery = 35
        total = (unit_price * quantity) + delivery

        # get seller's first shop
        shop = product.seller.shops.first()
        shop_name = shop.shop_name if shop else "Unknown Shop"

        BuyNowOrders.objects.create(
            user=request.user,
            product=product,
            quantity=quantity,
            shop_name=shop_name,   # ✅ correct value from Shop model
            unit_price=unit_price,
            delivery_charge=delivery,
            total_amount=total
        )

        return redirect('orders_page')



@login_required(login_url='home')
def user_profile(request):
    if request.session.get('role') != 'user':
        return redirect('home')

    profile = get_object_or_404(Profile, user=request.user)
    addresses = request.user.addresses.all()

    return render(request, 'user_profile.html', {
        'profile': profile,
        'addresses': addresses
    })



@login_required(login_url='home')
def add_address(request):
    if request.method == 'POST':
        address_text = request.POST.get('address')

        # DELETE old address (keep only one)
        request.user.addresses.all().delete()

        # CREATE new address
        UserAddress.objects.create(
            user=request.user,
            address=address_text
        )

        messages.success(request, "Address updated successfully")

    return redirect('user_profile')



@login_required(login_url='home')
def edit_address(request, address_id):
    addr = get_object_or_404(UserAddress, id=address_id, user=request.user)

    if request.method == "POST":
        addr.address = request.POST.get('address')
        addr.save()
        return redirect('user_profile')


@login_required(login_url='home')
def delete_address(request, address_id):
    addr = get_object_or_404(UserAddress, id=address_id, user=request.user)
    addr.delete()
    return redirect('user_profile')


@login_required(login_url='home')
def upload_profile_image(request):
    if request.method == 'POST':
        profile = get_object_or_404(Profile, user=request.user)

        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']
            profile.save()

            messages.success(request, "Profile image updated successfully")

    return redirect('user_profile')


# --------------CART------------------


@login_required(login_url='home')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart_item, created = AddToCartProducts.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('cart')


@login_required(login_url='home')
def cart_page(request):
    cart_items = AddToCartProducts.objects.filter(user=request.user)

    subtotal = sum(item.item_total() for item in cart_items)
    delivery_charge = 35 if cart_items.exists() else 0
    grand_total = subtotal + delivery_charge

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_charge': delivery_charge,
        'grand_total': grand_total
    })

@login_required(login_url='home')
def update_cart_quantity(request, item_id, action):
    item = get_object_or_404(AddToCartProducts, id=item_id, user=request.user)

    if action == "increase":
        item.quantity += 1
    elif action == "decrease" and item.quantity > 1:
        item.quantity -= 1

    item.save()
    return redirect('cart')



@login_required(login_url='home')
def remove_from_cart(request, item_id):
    item = get_object_or_404(AddToCartProducts, id=item_id, user=request.user)
    item.delete()
    return redirect('cart')


@login_required
def confirm_order(request):
    cart_items = AddToCartProducts.objects.filter(user=request.user)

    if not cart_items.exists():
        return redirect('cart')

    subtotal = sum(item.product.price * item.quantity for item in cart_items)

    order = Order.objects.create(
        user=request.user,
        order_type='cart',
        delivery_charge=35,
        total_amount=subtotal + 35
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            unit_price=item.product.price
        )

    cart_items.delete()  # clear cart

    # ✅ FIXED: redirect to the correct view name
    return redirect('orders_page')

@login_required
def orders_page(request):
    role = request.session.get('role', 'user')

    if role == 'user':
        buy_now_orders = BuyNowOrders.objects.filter(
            user=request.user
        ).order_by('-created_at')

        cart_orders = Order.objects.filter(
            user=request.user,
            order_type='cart'
        ).order_by('-created_at')

    else:  # SELLER
        buy_now_orders = BuyNowOrders.objects.filter(
            product__seller__user=request.user
        ).order_by('-created_at')

        cart_orders = Order.objects.filter(
            items__product__seller__user=request.user
        ).distinct().order_by('-created_at')

    # ================= ATTACH REVIEWS =================

    # BUY NOW → product-based review
    for order in buy_now_orders:
        order.user_review = OrderReview.objects.filter(
            product=order.product,
            user=order.user,
            order__isnull=True
        ).first()
        order.order_type = 'buy_now'

    # CART → order-wide review
    for order in cart_orders:
        order.user_review = OrderReview.objects.filter(
            order=order,
            product__isnull=True
        ).first()
        order.order_type = 'cart'

    all_orders = list(buy_now_orders) + list(cart_orders)

    return render(request, 'orders.html', {
        'role': role,
        'buy_now_orders': buy_now_orders,
        'cart_orders': cart_orders,
        'all_orders': all_orders,
    })



@login_required
def add_review(request):
    if request.method != "POST":
        return redirect('orders_page')

    order_type  = request.POST.get('order_type')
    order_id    = request.POST.get('order_id')
    rating      = request.POST.get('rating')
    description = request.POST.get('description')

    if not rating or not description:
        messages.error(request, "Rating and review are required.")
        return redirect('orders_page')

    rating = int(rating)

    # ================= BUY NOW =================
    if order_type == 'buy_now':
        buy_order = get_object_or_404(
            BuyNowOrders,
            id=order_id,
            user=request.user
        )

        # prevent duplicate
        if OrderReview.objects.filter(
            user=request.user,
            product=buy_order.product,
            order__isnull=True
        ).exists():
            messages.warning(request, "You already reviewed this product.")
            return redirect('orders_page')

        OrderReview.objects.create(
            user=request.user,
            product=buy_order.product,
            rating=rating,
            description=description
        )

    # ================= CART =================
    elif order_type == 'cart':
        order = get_object_or_404(
            Order,
            id=order_id,
            user=request.user
        )

        # cart-wide review (one per order)
        if OrderReview.objects.filter(
            user=request.user,
            order=order,
            product__isnull=True
        ).exists():
            messages.warning(request, "You already reviewed this order.")
            return redirect('orders_page')

        OrderReview.objects.create(
            user=request.user,
            order=order,
            rating=rating,
            description=description
        )

    else:
        messages.error(request, "Invalid order type.")
        return redirect('orders_page')

    messages.success(request, "Review submitted successfully!")
    return redirect('orders_page')










