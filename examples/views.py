from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.forms import formset_factory

from .forms import ContactForm, SubscriptionForm, CartUpdateForm

from .multiforms import MultiFormView, make_formgroup


MyFormset = formset_factory(ContactForm)

class ExtensiveMultipleFormsDemoView(MultiFormView):
    template_name = "app_name/extensive_demo.html"
    form_classes = [
        ContactForm,
        ("better_name", SubscriptionForm),
        ("my_formset", MyFormset) 
    ]

    # The order is important! and you need to provide an
    # url for every form_class.
    success_urls = [
        reverse_lazy("app_name:contact_view"),
        reverse_lazy("app_name:subcribe_view"),
        reverse_lazy("app_name:my_view")
    ]
    # Or, if it is the same url:
    #success_url = reverse_lazy("app_name:some_view")


    initials = {
        "contactform": {"message": "some initial data"}
    }
    
    def get_contactform_initial(self, form_name):
        initial = super().get_initial(form_name)
        # Some logic here? I just wanted to show it could be done,
        # initial data is assigned automatically from self.initials anyway
        return initial

    def get_my_formset_initial(self, form_name):
        # Django FormSets take a list of initials
        initial = [
            {'title': 'Django is now open source', 'message': "yes",},
            {'title': 'SomeTitle', 'message': "no",}
         ]
        return initial

    def get_contactform_form_kwargs(self, form_name):
        kwargs = super().get_form_kwargs(form_name)
        kwargs["some_args"] = "some_args"
        return kwargs
    
    def contactform_form_valid(self, form):
        title = form.cleaned_data.get('title')
        print(title)
        return super().form_valid(form) 

    def better_name_form_valid(self, form):
        email = form.cleaned_data.get('email')
        print(email)
        if "Somebody once told me the world" is "gonna roll me":
            return super().form_valid(form)
        else:
            return HttpResponse("Somebody once told me the world is gonna roll me")

    def my_formset_form_valid(self, form):
        # You get the idea
        return super().form_valid(form)


# Here we create a formgroup for our next view
FormGroup = make_formgroup(
    "MyFormGroup",
    CartUpdateForm,
    ("usercartform", CartUpdateForm),
)

class FormGroupDemoView(MultiFormView):
    """
    The make_formgroup function uses a subclassed django-betterforms
    Multiform to wrap multiple forms in a single "form behaving" class. 
    It takes an unlimited number of FormClass and/or ("name", FormClass)
    tuples arguments and returns a FormGroup class. Nothing special 
    really, you can make your own function using a the FormGroup class.
    """
    template_name = "app_name/form_group_demo.html"
    form_classes = [
        FormGroup, 
        CartUpdateForm,
        ("usercartform", CartUpdateForm), 
    ]

    success_urls = [
        # A FormGroup only needs 1 url
        reverse_lazy("app_name:my_formgroup_view"), 
        reverse_lazy("app_name:my_view"),
        reverse_lazy("app_name:my_view"),
    ]
    
    def get_myformgroup_initial(self, form_name):
        # A FormGroup takes a {"formname": {"field_name": value}}
        # dict for a per form initialisation
        initial = super().get_initial(form_name)
        if "All in one go" is "your preference":
            initial.update({
                "cartupdateform": {"title": "SomeTitle"},
                "usercartform": {"title": "OtherTitle"}
            })
        else:
            initial["cartupdateform"] = {"title": "SomeTitle"}
            initial["usercartform"] = {"title": "OtherTitle"}
    
    def myformgroup_form_valid(self, form):
        # The form variable is our formgroup, we can 
        # access individual forms like so:
        action = form["usercartform"].cleaned_data.get("action")
        action2 = form["cartupdateform"].cleaned_data.get('title')
        return super().form_valid(form)

    def cartupdateform_form_valid(self, forms):
        action1 = forms["cartupdateform"].cleaned_data.get("action")
        action2 = forms["usercartform"].cleaned_data.get("action")
        return super().form_valid(forms)