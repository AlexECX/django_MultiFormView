from django.forms import Form, CharField, HiddenInput
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.edit import ProcessFormView
from django.core.exceptions import ImproperlyConfigured
from django.http import (HttpResponseForbidden, HttpResponseRedirect, 
                         HttpResponseBadRequest)

from .qualname import qualname
from .django_betterforms.multiform import MultiForm
import sys

if sys.version_info >= (3,7):
    # Python 3.7+ keeps order
    OrderedDict = dict
else:
    try:
        from collections import OrderedDict
    except ImportError:  # Python 2.6, Django < 1.7
        from django.utils.datastructures import SortedDict as OrderedDict

import inspect
from abc import ABC, abstractmethod


class MultipleForm(Form):
    form_name = CharField(max_length=60, widget=HiddenInput())


def cls_name(obj):
    """Returns the instance or class's class name in lower case. It
    will not be used if form_classes is a list of (name, Class) tuples.

    Code for qualname module from: 
        https://github.com/wbolster/qualname/blob/master/qualname.py
        Python 3.3+ : uses the python __qualname__ attribut
        Python 3.2- : uses source code inspection
    """
    try:
        name = qualname(obj)
    except AttributeError:
        # last ressort, hopefully never needed
        obj = obj()
        name = type(obj).__name__
    return name.lower()


def make_formgroup(name, *args):
    form_classes = []
    for form_cls in args:
        if inspect.isclass(form_cls):
            form_classes.append((cls_name(form_cls), form_cls))
        else:
            form_classes.append(form_cls) 

    FormGroup = type(
        str(name), 
        (MultiForm,), 
        {
            "form_classes": OrderedDict(form_classes), # Py 3.7+ uses dict()
            "prefix": str(name).lower(), # This will add a prefix attribut, 
                                         # usefull for the template
        },
    )
    return FormGroup


class AbstractFormsMixin(ABC, ContextMixin):
    """
    Abstract base class for Forms mixins. When implemented, provides a
    way to show and handle multiple forms. It generates prefixes from 
    the FormClass' name or a user given ("name", FormClass) tuple and
    use them to determine if a form received POST data.

    A name cannot appear twice, so either use a FormSet or give a 
    different name to recurring classes with the tuple method if the 
    same FormClass is used more than once.
    """
    initials = {}
    form_classes = {} 
    success_urls = {}
    prefixes = {}
    
    success_url = None

    def get_initial(self, form_name=None):
        """
        Return the initial data to use for form_name on this view.
        """
        return self.initials.get(form_name, self.initials.copy())

    def get_prefix(self, form_name):
        """Return the prefix to use for forms."""
        return self.prefixes.get(form_name, form_name)
    
    def get_form_classes(self):
        """
        Returns a [(name, FormClass)] list of the form classes to use.
        """
        form_classes = [] 
        for f_class in self.form_classes:
            if inspect.isclass(f_class):
                form_classes.append((cls_name(f_class), f_class))
            else:
                form_classes.append(f_class)
        return form_classes

    @abstractmethod
    def get_form(self, form_name, form_class=None):
        """Return an instance of a form."""
        pass

    def get_forms(self, form_classes=None):
        """
        Generate the forms from the form_classes list as a 
        {"form_name": form_instance} dict.
        """
        if form_classes is None:
            form_classes = self.get_form_classes()
        form_dict = OrderedDict() # Py 3.7+ uses dict()
        for name, form_cls in form_classes:
            form_dict[name] = self.get_form(name, form_cls)
        return form_dict
        # return {(name, self.get_form(name, form_cls)) \
        #         for name, form_cls in form_classes}

    @abstractmethod
    def get_form_kwargs(self, form_name):
        """Return the keyword arguments for instantiating a form."""
        pass

    def get_success_url(self, form_name):
        """
        Return the URL to redirect to after a successful form(s) 
        validation.
        """
        if not self.success_url:
            self.success_url = self.get_success_urls().get(form_name)
            if not self.success_url:
                raise ImproperlyConfigured(
                    "No redirection URL for %s where provided." % form_name
                    )
        return str(self.success_url)  # success_url may be lazy

    def get_success_urls(self):
        """Returns a {form_name: form_url} dict of the success URLs"""
        names = [name for name, f_cls in self.get_form_classes()]
        return {k: v for k, v in zip(names, self.success_urls)} 

    def form_valid(self, form, form_name):
        """If the form is valid, redirect to the supplied URL."""
        return HttpResponseRedirect(self.get_success_url(form_name))
     
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

    def forms_are_valid(self, forms):
        """Form(s) validation."""
        validate = [form.is_valid() \
                    for form in forms.values() if form.is_bound]
        return validate != [] and all(validate)


class FormsMixin(AbstractFormsMixin):
    """Barebone mixin with no available <form_name> method overload."""

    def get_form(self, form_name, form_class=None):
        """Return an instance of a form."""
        if form_class is None:
            form_class = dict(self.get_form_classes()).get(form_name)
            if not form_class:
                return form_class
        return form_class(**self.get_form_kwargs(form_name))

    def get_form_kwargs(self, form_name):
        """Return the keyword arguments for instantiating a form."""
        kwargs = {
            'initial':self.get_initial(form_name),
            'prefix': self.get_prefix(form_name)
            }

        if self.request.method in ('POST', 'PUT'):
            # If a forms prefix is found in the POST data, it will
            # be filled and bounded.
            if next(
                (k for k in self.request.POST if kwargs['prefix'] in k),
                False
                ):
                kwargs.update({
                        'data': self.request.POST,
                        'files': self.request.FILES,
                    })
        return kwargs


class ExtraFormsMixin(AbstractFormsMixin):
    """FormsMixin with get_<form_name> methods overload support"""

    def get_initials(self, form_name):
        """Makes get_%_initial overload possible."""
        initial_method = 'get_%s_initial' % form_name
        if hasattr(self, initial_method):
            return getattr(self, initial_method)(form_name)
        else:
            initial = self.get_initial(form_name)
            return initial

    def get_prefixes(self, form_name):
        """Makes get_%_prefix overload possible."""
        prefix_method = 'get_%s_prefix' % form_name
        if hasattr(self, prefix_method):
            return getattr(self, prefix_method)(form_name)
        else:
            return self.get_prefix(form_name)

    def get_forms_kwargs(self, form_name):
        """Makes get_%_form_kwargs overload possible."""
        kwargs_method = 'get_%s_form_kwargs' % form_name
        if hasattr(self, kwargs_method):
            return getattr(self, kwargs_method)(form_name)
        else:
            return self.get_form_kwargs(form_name)

    def get_form(self, form_name, form_class=None):
        """Return an instance of a form."""
        if form_class is None:
            form_class = dict(self.get_form_classes()).get(form_name)
            if not form_class:
                return form_class
        return form_class(**self.get_forms_kwargs(form_name))

    def get_form_kwargs(self, form_name):
        """Return the keyword arguments for instantiating a form."""
        kwargs = {
            'initial':self.get_initials(form_name),
            'prefix': self.get_prefixes(form_name)
        }

        if self.request.method in ('POST', 'PUT'):
            # If a forms prefix is found in the POST data, it will
            # be filled and bounded.
            if next(
                (k for k in self.request.POST if kwargs['prefix'] in k),
                False
                ):
                kwargs.update({
                        'data': self.request.POST,
                        'files': self.request.FILES,
                    })
        return kwargs


class BaseMultiFormMixin:
    """
    Adds automatic <input name="form_name"> processing as well as
    <form_name> form_valid overload support.
    """
    _form_name = None

    def get_initial(self, form_name=None):
        initial = super().get_initial(form_name)
        if form_name:
            initial.update({'form_name': form_name})
        return initial
    
    def form_valid(self, form, form_name=None):
        """If the form is valid, redirect to the supplied URL."""
        if form_name is None:
            form_name = self.get_form_name()
        return super().form_valid(form, form_name)

    def forms_valid(self, forms, form_name=None):
        """
        Makes %_form_valid overload possible. If using form_groups,
        overload using form_valid instead.
        """
        if form_name is None:
            form_name = self.get_form_name()
        if not form_name:
            return self.form_valid(forms)
        else:
            form_valid_method = '%s_form_valid' % form_name
            if hasattr(self, form_valid_method):
                return getattr(self, form_valid_method)(forms[form_name])
            else:
                return self.form_valid(forms[form_name], form_name)

    def get_form_name(self):
        """
        Searches for a POST key with 'form_name' 
        """
        if self._form_name is None:
            self._form_name = self.request.POST.get("form_name")
        if self._form_name is None:
            self._form_name = next(
                (self.request.POST[k] for k in self.request.POST 
                 if "form_name" in k),
                ""
                )
        return self._form_name


class ProcessMultiFormView(ProcessFormView):
    """Render the form(s) on GET and processes on POST."""
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
 

class SimpleMultiFormMixin(BaseMultiFormMixin, FormsMixin):
    """"""

class BaseSimpleMultiFormView(SimpleMultiFormMixin, ProcessMultiFormView):
    """A base view for displaying several forms."""

class SimpleMultiFormView(TemplateResponseMixin, BaseSimpleMultiFormView):
    """
    A stripped down MultiForm view without get_<form_name> method
    overload support.
    """

class MultiFormMixin(BaseMultiFormMixin, ExtraFormsMixin):
    """"""

class BaseMultiFormView(MultiFormMixin, ProcessMultiFormView):
    """A base view for displaying several forms."""

class MultiFormView(TemplateResponseMixin, BaseMultiFormView):
    """
    A view for displaying forms, and rendering a template response.

    Full <form_name> method overload suport for form_valid and 
    get_methods initial, prefix and form_kwargs.

    Has automatic "form_name" input initialisation and POST processing.
    If the input is not found in POST, defaults to FormsView behavior.
    """

class BaseFormsView(ProcessMultiFormView):
    """A base view for displaying several forms."""

class FormsView(TemplateResponseMixin, BaseFormsView, FormsMixin):
    """    
    Barebone version with no available <form_name> method overload or 
    automatic <input name="form_name"> processing.

    It generates prefixes from the FormClass' name or a user given tuple
    in the format ("name", FormClass) and use them to determine if a 
    form received POST data.

    A name cannot appear twice, use a FormSet or give a different name 
    with the tuple method if using duplicate classes.
    """

class PlusFormsView(TemplateResponseMixin, BaseFormsView, ExtraFormsMixin):
    """FormView with get_<form_name> method overload support."""


