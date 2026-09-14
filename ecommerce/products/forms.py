from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Customer, CustomUser, Payment, Review, ReturnRequest, ShippingAddress


class NoColonMixin:
    """Labels read better without Django's default trailing colon."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class SignupForm(NoColonMixin, UserCreationForm):
    """Signup with hashed passwords, handled by Django's own auth machinery."""

    first_name = forms.CharField(max_length=150)
    middle_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = CustomUser
        fields = ["first_name", "middle_name", "last_name", "username", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            phone = self.cleaned_data.get("phone", "")
            if phone:
                Customer.objects.filter(user=user).update(phone=phone)
        return user


class LoginForm(NoColonMixin, AuthenticationForm):
    username = forms.CharField(label="Username")


class ProfileForm(NoColonMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = Customer
        fields = ["phone", "address", "city"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

    def save(self, commit=True):
        customer = super().save(commit=commit)
        user = customer.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return customer


class CheckoutForm(NoColonMixin, forms.ModelForm):
    payment_method = forms.ChoiceField(
        choices=Payment.METHOD_CHOICES,
        widget=forms.RadioSelect,
        initial=Payment.CASH,
    )

    class Meta:
        model = ShippingAddress
        fields = ["recipient_name", "phone", "address", "city", "postal_code", "country"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        digits = phone.replace("+", "").replace("-", "").replace(" ", "")
        if not digits.isdigit() or len(digits) < 11:
            raise forms.ValidationError("Enter a full phone number, e.g. 01712345678.")
        return phone


class ReviewForm(NoColonMixin, forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect(choices=[(i, f"{i}") for i in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": "How was it?"}),
        }


class ReturnRequestForm(NoColonMixin, forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Tell us what went wrong"}
            ),
        }
