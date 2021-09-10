from django.conf import settings
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import UserPassesTestMixin
from django.utils.decorators import method_decorator
from django.views.generic import RedirectView, TemplateView

try:
    from django.db.transaction import commit_on_success
except ImportError:
    # There's no commit_on_success in newer django versions
    def identity_decorator(func):
        return func
    commit_on_success = identity_decorator


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class CommitOnSuccessMixin(object):
    '''
    View mixin to commit transaction on success
    Not really required for Django1.6+
    '''
    @method_decorator(commit_on_success)
    def dispatch(self, request, *args, **kwargs):
        return super(CommitOnSuccessMixin, self).dispatch(request,
                                                          *args,
                                                          **kwargs)


class AdditionalContextMixin(object):
    '''All `get_additional_context` to return additional context

    If the class defines `get_additional_context` then add this
    to the results of get_context_data
    '''
    def get_additional_context(self, **kwargs):
        return {}

    def get_context_data(self, **kwargs):
        context = super(AdditionalContextMixin,
                        self).get_context_data(**kwargs)
        additional_context = self.get_additional_context(**kwargs)
        if additional_context:
            context.update(additional_context)
        return context


class NextURLMixin(object):
    def get_next_url(self, request, *args, **kwargs):
        return request.GET.get(
            'next', request.POST.get(
                'next', kwargs.get(
                    'next_url', kwargs.get('next'))))


class NextOnSuccessMixin(object):
    '''Use with FormView and descendents'''
    def get_success_url(self, *args, **kwargs):
        next_url = self.get_next_url(self.request, *args, **kwargs)
        if next_url:
            return next_url
        return super(NextOnSuccessMixin, self).get_success_url()


class ActionAndRedirectView(RedirectView):
    '''do self.action and redirect to self.url or self.get_redirect_url'''
    def get(self, request, *a, **kw):
        self.action()
        return super(ActionAndRedirectView, self).get(request, *a, **kw)


class ActionAndRedirectToNextView(NextURLMixin, ActionAndRedirectView):
    '''self.action is the action, and 'next' param is the redirect'''
    def get_redirect_url(self, *args, **kwargs):
        return self.get_next_url(self.request, *args, **kwargs) or '/'


class TemplateViewWithExtraContext(AdditionalContextMixin, TemplateView):
    extra_context = {}

    def get_additional_context(self):
        return self.kwargs('extra_context')
