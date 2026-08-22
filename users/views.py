from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from users.forms import ProfileForm


@login_required
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Данные профиля успешно изменены')
        return redirect('users:profile_edit')
    return render(request, 'users/profile_edit.html', {'form': form})
