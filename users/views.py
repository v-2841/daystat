from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from users.forms import ProfileForm


@login_required
def profile_edit(request):
    # a copy of the user: a rejected form must not repaint the page with
    # the unsaved gender and name that it puts into its instance
    user = get_user_model().objects.get(pk=request.user.pk)
    form = ProfileForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Данные профиля успешно изменены')
        return redirect('users:profile_edit')
    return render(request, 'users/profile_edit.html', {'form': form})
