from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from users.forms import ProfileForm


User = get_user_model()


@login_required
def profile_edit(request):
    user = get_object_or_404(User, username=request.user.username)
    form = ProfileForm(
        request.POST or None,
        instance=user,
    )
    context = {
        'form': form,
    }
    if not form.is_valid():
        return render(request, 'users/profile_edit.html', context)
    form.save()
    messages.success(request, 'Данные профиля успешно изменены')
    return render(request, 'users/profile_edit.html', context)
