from django.shortcuts import render
from django.http import HttpResponse
from .models import CustomUser


def home(request):
    return render(request, 'home.html')


def test(request):
    if request.method == 'POST':
        fname = request.POST.get('fname')
        mname = request.POST.get('mname')
        lname = request.POST.get('lname')
        username = request.POST.get('username')
        password = request.POST.get('password')

        user1 = CustomUser(firstName= fname, middleName = mname , lastName =lname, userName = username, password=password )
        user1.save()
    return render(request, 'test.html')



