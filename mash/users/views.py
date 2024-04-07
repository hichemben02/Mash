from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from .models import Profile
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
import requests
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from friend.utils import get_friend_request_or_false
from friend.friend_request_status import FriendRequestStatus
from notification.models import Notification
from friend.models import FriendList, FriendRequest
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from cryptography.fernet import Fernet
from django.contrib.auth.views import LoginView as BaseLoginView
from django.contrib.auth.views import LogoutView as BaseLogoutView
# Create your views here.

cipher = Fernet(b'79G7lLKB6J6gZ6BBjrK4gqXrDRbG0iGdZXRrp3bFaOE=')

def delete_inactive_users():
    # Delete inactive users (is_active=False) 
    inactive_users = get_user_model().objects.filter(is_active=False)
    inactive_users.delete()  # Delete inactive users

User = get_user_model()

@receiver(user_logged_in)
def got_online(user, **kwargs):    
    user.profile.is_online = True
    user.profile.save()

@receiver(user_logged_out)
def got_offline(user, **kwargs):   
    user.profile.is_online = False
    user.profile.save()

class CustomLoginView(BaseLoginView):
    #delete_inactive_users()
    template_name = 'users/login.html'

    def form_valid(self, form):
        # Authenticate user
        user = form.get_user()

        if user is not None:
            if user.profile.is_online:
                # User is already logged in, prevent login
                messages.error(self.request, 'User is already logged in.')
                return self.form_invalid(form)

            # Set is_logged_in to True
            got_online(user)

        return super().form_valid(form)
    


class CustomLogoutView(BaseLogoutView):
    def dispatch(self, request, *args, **kwargs):
        # Set is_logged_in to False
        if request.user.is_authenticated:
            got_offline(request.user)
        return super().dispatch(request, *args, **kwargs)



# Following and Unfollowing users
@login_required
def follow_unfollow_profile(request):
    if request.method == 'POST':
        my_profile = Profile.objects.get(user = request.user)
        pk = request.POST.get('profile_pk')
        obj = Profile.objects.get(pk=pk)

        if obj.user in my_profile.following.all():
            my_profile.following.remove(obj.user)
            notify = Notification.objects.filter(sender=request.user, notification_type=2)
            notify.delete()
        else:
            my_profile.following.add(obj.user)
            notify = Notification(sender=request.user, user=obj.user, notification_type=2)
            notify.save()
        return redirect(request.META.get('HTTP_REFERER'))
    return redirect('profile-list-view')


# User account creation
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():

            user = form.save(commit=False)
            user.is_active = False  # Deactivate user until confirmation
            otp = get_random_string(length=6, allowed_chars='0123456789')
            user.otp = cipher.encrypt(otp.encode()).decode()
            user.save()

            request.session['signup_email'] = user.email
            request.session['attempts'] = 0
            # Set expiry time for session to 30 min
            request.session.set_expiry(1800)

            # Send confirmation email with OTP
            subject = 'Account Confirmation'
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            otp = otp
            message = (
                f"Hello Dear {first_name} {last_name},\n\n"
                f"Your OTP is: {otp}\n\n"
                "Thanks for signing up with us. "
                "Please confirm your account by entering the OTP on the website.\n\n"
                "If you did not request this OTP, please ignore this email.\n\n"
                "Thanks,\nMash Team"
            )
            user_email = form.cleaned_data.get('email')

            try:
                send_mail(subject, message, "mash.admcenter@gmail.com", [user_email], fail_silently=False)
                messages.info(request, 'Please check your email for OTP to confirm your account.')
                return redirect('confirm_account')
            except Exception as e:
                messages.error(request, 'An error occurred while sending the confirmation email. Please try again later.')
                return redirect('register')

            # reCAPTCHA V2
            recaptcha_response = request.POST.get('g-recaptcha-response')
            data = {
                'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
                'response': recaptcha_response
            }
            r = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
            result = r.json()

            if result['success']:
                form.save()
                username = form.cleaned_data.get('username')
                messages.success(request, f"Your account has been created! You can login now")
                return redirect('login')
            else:
                messages.error(request, 'Invalid reCAPTCHA. Please try again.')            
            
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form':form})



# Confirm account
def ConfirmAccountView(request):
    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        user_email = request.session.get('signup_email')
        if user_email:
            user = get_user_model().objects.get(email=user_email)
            otp = cipher.decrypt(user.otp.encode()).decode()
            if otp == otp_entered:
                user.is_active = True
                user.save()
                messages.success(request, 'Account activated successfully. You can now log in.')
                return redirect('login')
            else:
                # Increment the attempts count
                request.session['attempts'] = request.session.get('attempts', 0) + 1
                if request.session['attempts'] >= 3:
                    # Delete user if attempts exceed threshold
                    user.delete()
                    messages.error(request, 'You have exceeded the maximum number of attempts. Your account has been deleted.')
                    return redirect('register')
                messages.error(request, 'Invalid OTP. Please try again.')
        else:
            messages.error(request, 'Email not found in session.')
    user = get_user_model().objects.get(email=request.session.get('signup_email'))
    return render(request, 'users/confirm_account.html', {'user': user}) 


#  User profile
@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f"Your account has been updated!")
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'u_form':u_form,
        'p_form':p_form
    }

    return render(request, 'users/profile.html', context)


# Creating a public profile view
def public_profile(request, username):
    user = User.objects.get(username=username)
    return render(request, 'users/public_profile.html', {"cuser":user})


# All user profiles
class ProfileListView(LoginRequiredMixin,ListView):
    model = Profile
    template_name = "users/all_profiles.html"
    context_object_name = "profiles"

    def get_queryset(self):
        return Profile.objects.all().exclude(user=self.request.user)
    

# User profile details view
class ProfileDetailView(LoginRequiredMixin,DetailView):
    model = Profile
    template_name = "users/user_profile_details.html"
    context_object_name = "profiles"

    def get_queryset(self):
        return Profile.objects.all().exclude(user=self.request.user)

    def get_object(self,**kwargs):
        pk = self.kwargs.get("pk")
        print(f"=========== {pk} ===========")
        view_profile = Profile.objects.get(pk=pk)
        return view_profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        view_profile = self.get_object()
        my_profile = Profile.objects.get(user=self.request.user)
        if view_profile.user in my_profile.following.all():
            follow = True
        else:
            follow = False
        context["follow"] = follow

        # FRIENDS START

        account = view_profile.user
        try:
            friend_list = FriendList.objects.get(user=account)
        except FriendList.DoesNotExist:
            friend_list = FriendList(user=account)
            friend_list.save()
        friends = friend_list.friends.all()
        context['friends']=friends

        is_self = True
        is_friend = False
        request_sent = FriendRequestStatus.NO_REQUEST_SENT.value
        friend_requests = None
        user=self.request.user
        if user.is_authenticated and user!=account:
            is_self = False
            if friends.filter(pk=user.id):
                is_friend = True
            else:
                is_friend = False
                # CASE 1: request from them to you
                if get_friend_request_or_false(sender=account, receiver=user) != False:
                    request_sent = FriendRequestStatus.THEM_SENT_TO_YOU.value
                    context['pending_friend_request_id'] = get_friend_request_or_false(sender=account, receiver=user).pk
                # CASE 2: request you sent to them
                elif get_friend_request_or_false(sender=user, receiver=account) != False:
                    request_sent = FriendRequestStatus.YOU_SENT_TO_THEM.value
                # CASE 3: no request has been sent
                else:
                    request_sent = FriendRequestStatus.NO_REQUEST_SENT.value

        elif not user.is_authenticated:
            is_self = False
        else:
            try:
                friend_requests = FriendRequest.objects.filter(receiver=user, is_active=True)
            except:
                pass
        context['request_sent'] = request_sent
        context['is_friend'] = is_friend
        context['is_self'] = is_self
        context['friend_requests'] = friend_requests
        # FRIENDS END
        
        return context