from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (
        ('seller', 'Seller'),
        ('user', 'User'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    fullname = models.CharField(max_length=150)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Shop(models.Model):
    seller = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='shops')
    shop_name = models.CharField(max_length=150)
    shop_address = models.TextField()
    shop_image1 = models.ImageField(upload_to='shop_images/', null=True, blank=True)
    shop_image2 = models.ImageField(upload_to='shop_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shop_name} ({self.seller.user.username})"


# ---------------- Product ----------------
class Category(models.Model):
    name = models.CharField(max_length=100)  # e.g., Edible Mushrooms, Medicinal Mushrooms, Others

    def __str__(self):
        return self.name

class Subtype(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subtypes')
    name = models.CharField(max_length=100)  # e.g., Button Mushrooms, Oyster Mushrooms
    extra_subtypes = models.JSONField(blank=True, null=True)  
    # optional: list of detailed subtypes like ["White Button", "Cremini", "Portobello"]

    def __str__(self):
        return f"{self.name} ({self.category.name})"

class Product(models.Model):
    seller = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    subtype = models.ForeignKey(Subtype, on_delete=models.SET_NULL, null=True, blank=True)
    other_description = models.TextField(blank=True, null=True)  # for 'Others' category
    TYPE_CHOICES = [
        ('fresh', 'Fresh'),
        ('dried', 'Dried')
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='fresh')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    



class BuyNowOrders(models.Model):

    SOURCE_CHOICES = (
        ('BUY_NOW', 'Buy Now'),
        ('CART', 'Cart'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    shop_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=35)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='BUY_NOW'   # ✅ IMPORTANT
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.source})"


class UserAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.address[:30]}"



class Order(models.Model):
    ORDER_TYPE = (
        ('buy_now', 'Buy Now'),
        ('cart', 'Cart'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE)

    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=35)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"
    

class OrderReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Nullable for Buy Now or cart product review
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Cart order reference (nullable for Buy Now orders)"
    )

    # Product being reviewed
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reviews', 
        help_text="The product being reviewed (optional for cart-wide review)"
    )

    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        help_text="Rating from 1 to 5"
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'order', 'product')  # ensures one review per product per order

    def __str__(self):
        if self.product:
            return f"Review for {self.product.name} by {self.user.username}"
        return f"Cart Review by {self.user.username}"



class AddToCartProducts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def item_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def item_total(self):
        return self.unit_price * self.quantity
