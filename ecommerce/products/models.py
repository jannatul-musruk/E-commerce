from django.db import models



class CustomUser(models.Model):

    CustomUser_ID = models.AutoField(primary_key=True)
    firstName = models.CharField(255)
    middleName = models.CharField(255,null=True)
    lastName = models.CharField(255)
    userName = models.CharField(255)
    password = models.CharField(255)
    CustomUser_email = models.EmailField(unique=True,Required=True)

    def __str__(self):
        return f"{self.userName} - {self.firstName} {self.lastName}"


class Customer(models.Model):
    Customer_ID = models.AutoField(primary_key=True)
    CustomUser_ID = models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    Customer_phone = models.CharField(max_length=20)
    Customer_address = models.CharField(max_length=255)
    def __str__(self):
        return f"{self.CustomUser_ID.userName} - {self.Customer_phone}"

class Category(models.Model):
    Category_ID = models.AutoField(primary_key=True)
    Category_name = models.CharField(255)

    def __str__(self):
        return self.Category_name
    
class Brand(models.Model):
    Brand_ID = models.AutoField(primary_key=True)
    Brand_name = models.CharField(255) 
    def __str__(self):
        return self.Brand_name
    
class Product(models.Model):
    Product_ID = models.AutoField(primary_key=True)
    Product_name = models.CharField(255)
    Product_description = models.TextField()
    Category_ID = models.ForeignKey(Category,on_delete=models.CASCADE)
    Brand_ID = models.ForeignKey(Brand,on_delete=models.CASCADE)

    def __str__(self):
        return self.Product_name
    
class ProductVariant(models.Model):
    ProductVariant_ID = models.AutoField(primary_key=True)
    Product_ID = models.ForeignKey(Product,on_delete=models.CASCADE)
    ProductVariant_name = models.CharField(255)
    price = models.DecimalField(max_digits=10,decimal_places=2)
    stock = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.ProductVariant_name} - {self.price}"
    
class Cart(models.Model):
    Cart_ID = models.AutoField(primary_key=True)
    Customer_ID = models.ForeignKey(Customer,on_delete=models.CASCADE)
    Cart_created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.Cart_ID} - {self.Customer_ID.CustomUser_ID.userName}" 

class CartItem(models.Model):
    CartItem_ID = models.AutoField(primary_key=True)
    Cart_ID = models.ForeignKey(Cart,on_delete=models.CASCADE)
    ProductVariant_ID = models.ForeignKey(ProductVariant,on_delete=models.CASCADE)
    CartItem_quantity = models.CharField(255)

    def __str__(self):
        return f"{self.quantity} x {self.ProductVariant_ID.ProductVariant_name}"
    
class Order(models.Model):
    Order_ID = models.AutoField(primary_key=True)
    Customer_ID = models.ForeignKey(Customer,on_delete=models.CASCADE)
    Order_status = models.CharField(max_length=255)
    Order_created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.Order_ID} - {self.Customer_ID.CustomUser_ID.userName} - {self.status}" 

class OrderItem(models.Model):
    OrderItem_ID = models.AutoField(primary_key=True)
    Order_ID = models.ForeignKey(Order,on_delete=models.CASCADE)
    ProductVariant_ID = models.ForeignKey(ProductVariant,on_delete=models.CASCADE)
    OrderItem_quantity = models.IntegerField()

    def __str__(self):
        return f"order#{self.Order_ID.Order_ID} - {self.ProductVariant_ID.ProductVariant_name} * {self.OrderItem_quantity}" #order12 -red L * 2
    
class Payment(models.Model):
    Payment_ID = models.AutoField(primary_key=True)
    Order_ID = models.OneToOneField(Order,on_delete=models.CASCADE)
    amount = models.IntegerField()
    PAYMENT_CHOICES = [
    ('Cash', 'Cash'),
    ('Card', 'Card'),
    ('Bkash', 'Bkash'),
    ('Nagad', 'Nagad'),
    ]
    Payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES)
    paid_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)   

    def __str__(self):
        return f"Payment#{self.Payment_ID} - Order#{self.Order_ID.Order_ID} - Amount: {self.amount}"

class ShippingAddress(models.Model):
    ShippingAddress_ID = models.AutoField(primary_key=True)
    Order_ID = models.OneToOneField(Order,on_delete=models.CASCADE)
    ShippingAddress_address = models.CharField(255)
    city = models.CharField(max_length=255, default='Unknown')
    postal_code = models.CharField(max_length=20, default='0000')
    country = models.CharField(max_length=255)

    def __str__(self):
        f"{self.ShippingAddress_ID} - {self.Order_ID.Order_ID} - {self.country}"

class Wishlist(models.Model):
    Wishlist_ID = models.AutoField(primary_key=True)
    Customer_ID = models.ForeignKey(Customer,on_delete=models.CASCADE)
    ProductVariant_ID = models.ForeignKey(ProductVariant,on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.Customer_ID.CustomUser_ID.userName} - {self.ProductVariant_ID.ProductVariant_name}"

class Review(models.Model):
    Review_ID = models.AutoField(primary_key=True)
    Customer_ID = models.ForeignKey(Customer,on_delete=models.CASCADE)
    Product_ID = models.ForeignKey(Product,on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.CharField(max_length=255)
    Review_created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.Customer_ID.CustomUser_ID.userName} - {self.Product_ID.Product_name} - {self.rating}"

class ReturnRequest(models.Model):
    ReturnRequest_ID = models.AutoField(primary_key=True)
    OrderItem_ID = models.OneToOneField(OrderItem,on_delete=models.CASCADE)
    reason = models.CharField(max_length=255)
    is_approved = models.BooleanField(default=False)
    requested_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ReturnRequest #{self.ReturnRequest_ID} for OrderItem #{self.OrderItem_ID.OrderItem_ID}"    

class Subscription(models.Model):
    StopIteration_ID = models.AutoField(primary_key=True)
    Customer_ID = models.OneToOneField(Customer,on_delete=models.CASCADE)
    Subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Subscription for {self.Customer_ID.CustomUser_ID.userName} - Active: {self.is_active}"
    
class Notification(models.Model):
    Notification_ID = models.AutoField(primary_key=True)
    Customer_ID = models.ForeignKey(Customer,on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    Notification_created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.Customer_ID.CustomUser_ID.userName} - Read: {self.is_read}"

class ActivityLog(models.Model):
    ActivityLog_ID = models.AutoField(primary_key=True)
    Customer_ID = models.ForeignKey(Customer,on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    Timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.Customer_ID.CustomUser_ID.userName} - {self.action} at {self.timestamp}"       
    
    

    
    



    