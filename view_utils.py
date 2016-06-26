from django.conf import settings
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.decorators import method_decorator
from django.views.generic import RedirectView, TemplateView

try:
    from django.db.transaction import commit_on_success
except ImportError:
    # There's no commit_on_success in newer django versions
    def identity_decorator(func):
        return func
    commit_on_success = identity_decorator


class AccessMixin(object):
    """
    'Abstract' mixin that gives access mixins the same customizable
    functionality.
    """
    login_url = settings.LOGIN_URL  # LOGIN_URL from project settings
    raise_exception = False  # Default whether to raise an exception to none
    redirect_field_name = REDIRECT_FIELD_NAME

    def get_login_url(self):
        """
        Override this method to customize the login_url.
        """
        if self.login_url is None:
            raise ImproperlyConfigured(
                "%(cls)s is missing the login_url. "
                "Define %(cls)s.login_url or override "
                "%(cls)s.get_login_url()." % {"cls": self.__class__.__name__})

        return self.login_url

    def get_redirect_field_name(self):
        """
        Override this method to customize the redirect_field_name.
        """
        if self.redirect_field_name is None:
            raise ImproperlyConfigured(
                "{cls} is missing the "
                "redirect_field_name. Define {cls}.redirect_field_name or "
                "override {cls}.get_redirect_field_name().".format(
                    cls=self.__class__.__name__))

        return self.redirect_field_name


class UserPassesTestMixin(AccessMixin):
    """
    View mixin which verifies that the user is passes a given test

    The test should be put in the over-ridden method `user_passes_test`
    Redirect to login if user fails the test

    NOTE:
    This should be the left-most mixin of a view.
    """
    def user_passes_test(self, user):
        '''Derived Classes have to over-ride this'''
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.user_passes_test(request.user):
            if self.raise_exception:
                raise PermissionDenied  # return a forbidden response
            else:
                return redirect_to_login(
                    request.get_full_path(),
                    self.get_login_url(),
                    self.get_redirect_field_name())

        return super(UserPassesTestMixin, self).dispatch(request,
                                                         *args,
                                                         **kwargs)


class LoginRequiredMixin(UserPassesTestMixin):
    def user_passes_test(self, user):
        return user.is_authenticated()


class StaffRequiredMixin(UserPassesTestMixin):
    def user_passes_test(self, user):
        return user.is_staff


class UserHasPermissionMixin(UserPassesTestMixin):
    permission = None

    def user_passes_test(self, user):
        return user.has_perm(self.permission)


class CommitOnSuccessMixin(object):
    '''
    View mixin to commit transaction on success
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
    def get_next_url(self, request):
        return request.GET.get('next', request.POST.get('next', None))


class NextOnSuccessMixin(object):
    '''Use with FormView and descendents'''
    def get_success_url(self):
        next_url = self.get_next_url(self.request)
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
        return self.get_next_url(self.request) or '/'


class TemplateViewWithExtraContext(AdditionalContextMixin, TemplateView):
    extra_context = {}

    def get_additional_context(self):
        return self.kwargs('extra_context')
