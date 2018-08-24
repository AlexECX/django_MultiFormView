from django.forms import Form, CharField, HiddenInput
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.edit import ProcessFormView
from django.core.exceptions import ImproperlyConfigured
from django.http import (HttpResponseForbidden, HttpResponseRedirect, 
                         HttpResponseBadRequest)

from .qualname import qualname
from .django_betterforms.multiform import MultiForm
try:
    from collections import OrderedDict
except ImportError:  # Python 2.6, Django < 1.7
    from django.utils.datastructures import SortedDict as OrderedDict  # NOQA
import inspect

class MultipleForm(Form):
    form_name = CharField(max_length=60, widget=HiddenInput())


def cls_name(obj):
    """Returns the instance or class's class name in lower case. It
    will not be used if form_classes is a list {name: Class} dicts.

    Code for qualname module from: 
        https://github.com/wbolster/qualname/blob/master/qualname.py
        Python 3.3+ : uses the __qualname__ attribut
        Python 3.2- : uses python magic (idk)
    """
    #name = "{}{}".format(self.get_prefix(name), name)
    name = qualname(obj)
    return name.lower() if name != "str" else obj.lower()

def make_formgroup(*args):
    form_classes = OrderedDict(
        {cls_name(form_cls): form_cls for form_cls in args}
    )
    FormGroup = type("FormGroup", 
                     (MultiForm,), 
                     {"form_classes": form_classes})
    return FormGroup

class MultiFormMixin(ContextMixin):
    """
    Provide a way to show and handle multiple forms in a request.
    The Simple class does not offer <form_name>_method overload
    aside from <form_name>_form_valid and get_<form_name>_initial.
    """
    initials = {}
    form_classes = {} 
    success_urls = {}
    prefixes = {}
    
    success_url = None
    _form_name = None

    def get_initial(self, form_name=None):
        """
        Return the initial data to use for form_name on this view.
        """
        initial = self.initials.get(form_name, self.initials.copy())
        initial.update({"form_name": form_name})
        return initial
     
    def get_initials(self, form_name):
        """Makes get_%_initial overload possible."""
        initial_method = 'get_%s_initial' % form_name
        if hasattr(self, initial_method):
            return getattr(self, initial_method)(form_name)
        else:
            return self.get_initial(form_name)

    def get_prefix(self, form_name):
        """Return the prefix to use for forms."""
        return self.prefixes.get(form_name, form_name)
    
    def get_form_classes(self):
        """
        Returns a {name: FormClass} dict of the form classes to use.
        """
        form_classes = {}
        for f_class in self.form_classes:
            if inspect.isclass(f_class):
                form_classes[cls_name(f_class)] = f_class
            else:
                form_classes.update(f_class)
        return form_classes

    def get_form(self, form_name=None, form_class=None):
        """
        Return an instance of a form. Defaults to the one in
        POST["form_name"].
        """
        if form_name is None:
            form_name = self.get_form_name()
        if form_class is None:
            form_class = self.get_form_classes().get(form_name)
        if not form_class:
            return form_class
        return form_class(**self.get_form_kwargs(form_name))

    def get_forms(self, form_classes=None):
        """
        Generate the forms from the form_classes dict as a 
        {"form_name": form_instance} dict.
        """
        if form_classes is None:
            form_classes = self.get_form_classes()
        return {name: self.get_form(name, form_cls) \
                 for name, form_cls in form_classes.items()}

    def get_form_kwargs(self, form_name):
        """Return the keyword arguments for instantiating a form."""
        kwargs = {
            'initial':self.get_initials(form_name),
            'prefix':self.get_prefix(form_name)
        }
        if self.request.method in ('POST', 'PUT'):
            # If a forms prefix is found in the POST data, it will
            # be filled and bounded.
            if next(
                (d for d in self.request.POST if kwargs['prefix'] in d),
                False
                ):
                kwargs.update({
                        'data': self.request.POST,
                        'files': self.request.FILES,
                    })
        return kwargs
        
    def get_success_url(self, form_name=None):
        """
        Return the URL to redirect to after a successful form(s) 
        validation.
        """
        if form_name is None:
            form_name = self.get_form_name()
        if not self.success_url:
            self.success_url = self.get_success_urls().get(form_name)
            if not self.success_url:
                raise ImproperlyConfigured("No redirection URL where provided.")

        return str(self.success_url)  # success_url may be lazy

    def get_success_urls(self):
        """Returns a {form_name: form_url} dict of the success URLs"""
        return {f_name: self.success_urls[i] \
                for i, f_name in enumerate(self.get_form_classes())}

    def form_valid(self, form=None, form_name=None):
        """If the form is valid, redirect to the supplied URL."""
        if form_name is None:
            form_name = self.get_form_name()
        return HttpResponseRedirect(self.get_success_url(form_name))
    
    def forms_valid(self, forms, form_name=None):
        """
        Makes %_form_valid overload possible. If using form_groups,
        overload using form_valid instead.
        """
        if form_name is None:
            form_name = self.get_form_name()
        if form_name is None:
            return self.form_valid(forms)
        else:
            form_valid_method = '%s_form_valid' % form_name
            if hasattr(self, form_valid_method):
                return getattr(self, form_valid_method)(forms[form_name])
            else:
                return self.form_valid(forms[form_name], form_name)
     
    def forms_invalid(self, forms):
        """
        If the validation was not successfull, render the invalid form(s).
        """
        return self.render_to_response(self.get_context_data(forms=forms))

    def get_context_data(self, **kwargs):
        """Insert the forms into the context dict."""
        if 'forms' not in kwargs:
            kwargs['forms'] = self.get_forms()
        return super().get_context_data(**kwargs)

    def get_form_name(self):
        """
        Searches for a POST key with 'form_name' 
        """
        if self._form_name is None:
            self._form_name = self.request.POST.get("form_name")
        if self._form_name is None:
            self._form_name = next(
                (v for k, v in self.request.POST.items() if "form_name" in k),
                ""
                )
        return self._form_name

    def forms_are_valid(self, forms):
        """Form(s) validation."""
        validate = [form.is_valid() \
                    for form in forms.values() if form.is_bound]
        return validate != [] and all(validate)


class ProcessMultipleFormsView(ProcessFormView):
    """Render the form(s) on GET and processes on POST."""
    def get(self, request, *args, **kwargs):
        """
        Handle GET requests: instantiate a blank version of the form(s).
        """
        return self.render_to_response(self.get_context_data())
     
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate the form(s), with only the 
        submitting form or form_group receiving POST data and 
        validation. All other forms are instanciated blank.
        """
        forms = self.get_forms()
        if self.forms_are_valid(forms):
            return self.forms_valid(forms)
        else:
            return self.forms_invalid(forms)

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that browsers only support POST for now.
    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)
 
 
class BaseMultipleFormsView(MultiFormMixin, ProcessMultipleFormsView):
    """
    A base view for displaying several forms.
    """

class SimpleMultiFormsView(TemplateResponseMixin, BaseMultipleFormsView):
    """
    A view for displaying several forms, and rendering a template response.
    """

class MultiFormsView(SimpleMultiFormsView):
    """
    A view for displaying several forms, and rendering a template response.
    This class view adds get_<form_name>_method overload for get_prefix
    and get_form_kwargs methods.
    """
    def get_prefix(self, form_name):
        """Return the prefix to use for forms."""
        return self.prefixes.get(form_name, form_name)

    def get_prefixes(self, form_name):
        """Makes get_%_prefix overload possible."""
        prefix_method = 'get_%s_prefix' % form_name
        if hasattr(self, prefix_method):
            return getattr(self, prefix_method)(form_name)
        else:
            return self.get_prefix(form_name)

    def get_form(self, form_name=None, form_class=None):
        """
        Return an instance of a form. Defaults to the one in
        POST["form_name"].
        """
        if form_name is None:
            form_name = self.get_form_name()
        if form_class is None:
            form_class = self.get_form_classes().get(form_name)
        if not form_class:
            return form_class
        return form_class(**self.get_forms_kwargs(form_name))

    def get_form_kwargs(self, form_name):
        """Return the keyword arguments for instantiating a form."""
        kwargs = {
            'initial':self.get_initials(form_name),
            'prefix':self.get_prefix(form_name)
        }
        if self.request.method in ('POST', 'PUT'):
            # If a forms prefix is found in the POST data, it will
            # be filled and bounded.
            if next(
                (d for d in self.request.POST if kwargs['prefix'] in d),
                False
                ):
                kwargs.update({
                        'data': self.request.POST,
                        'files': self.request.FILES,
                    })
        return kwargs

    def get_forms_kwargs(self, form_name):
        """Makes get_%_form_kwargs overload possible."""
        kwargs_method = 'get_%s_form_kwargs' % form_name
        if hasattr(self, kwargs_method):
            return getattr(self, kwargs_method)(form_name)
        else:
            return self.get_form_kwargs(form_name)