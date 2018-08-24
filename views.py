from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.forms import formset_factory

from .forms import ContactForm, SubscriptionForm, CartUpdateForm

from .multiforms import MultiFormsView, make_formgroup


MyFormset = formset_factory(ContactForm)

class ExtensiveMultipleFormsDemoView(MultiFormsView):
    """Using the <input name="form_name" value="form_name"> method"""
    template_name = "app_name/extensive_demo.html"
    form_classes = [
        ContactForm,
        ("better_name", SubscriptionForm), # Not a MultipleForm subclass
        ("my_formset", MyFormset) 
        # Note: for a formset, you need to provide your own input in the
        # template, with a name that contains "form_name" and value 
        # equal to "my_formset" or {{forms.my_formset.prefix}}.
    ]

    # The order is important! and you need to provide an
    # url for every ClassName.
    success_urls = [
        reverse_lazy("app_name:contact_view"),
        reverse_lazy("app_name:subcribe_view"),
        reverse_lazy("app_name:my_view")
    ]
    # Or, if it is the same url:
    #success_url = reverse_lazy("app_name:some_view")


    initial = {
        "contactform": {"message": "some initial data"}
    }
    
    def get_contactform_initial(self, form_name):
        initial = super().get_initial(form_name)
        # Some logic here? I just wanted to show it could be done,
        # initial data is assigned automatically from self.initial anyway
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
        form_name = form.cleaned_data.get('form_name')
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


class NoFormNameDemoView(MultiFormsView):
    """
    If there are forms that are not using the <input name="form_name"> 
    method, either by MultipleForm subclassing or manually giving one in 
    the template, you will not be able to use a <formname>_form_valid() 
    for THESE forms, use form_valid() instead and make your own checks.
    """
    template_name = "app_name/no_form_name_demo.html"
    form_classes = [
        ContactForm,
        CartUpdateForm, # Not a MultipleForm subclass

        # A FormClass needs a different name if used more 
        # than once.
        ("usercartform", CartUpdateForm),
        ("cartupdateform2", CartUpdateForm),
        ("usercartform2", CartUpdateForm)
    ]

    success_url = reverse_lazy("app_name:my_view")
    
    # Even if not using the form_name input, all get_<name>_methods are 
    # still available.
    def get_cartupdateform_form_kwargs(self, form_name):
        kwargs = super().get_form_kwargs(form_name)
        kwargs["selection"] = self.get_selection()
        return kwargs
    
    def contactform_form_valid(self, form):
        title = form.cleaned_data.get('title')
        print(title)
        return super().form_valid(form) 
    
    # I gave my own input inside the </form>, and since I know there are
    # 2 forms in it, I can process them.
    def name_i_gave_in_template_form_valid(self, form):
        # Or so you mignt think, but ^ this name does not
        # match any forms so this function will never be called, 
        # the forms where sent to self.form_valid(). 
        # If you want to process multiple different forms with 
        # a <form_name>_form_valid function, see make_formgroup() 
        # in the next DemoView.
        pass

    def form_valid(self, forms):
        # This is just an example of how you could do it.
        if forms["cartupdateform2"].is_bound:
            form = forms["cartupdateform2"]
            action = form.cleaned_data.get('action')
            print(action)
            return super().form_valid(form_name=form.prefix)
            # Note: If, for some reason, you are using a prefix 
            # other than the default given one, use 
            # form_name="cartupdateform2" instead.

        elif forms["usercartform2"].is_bound:
            form = forms["usercartform2"]
            # logic
            return super().form_valid(form_name=form.prefix)

        # And here are my lost forms
        elif forms["cartupdateform"].is_bound:
            # Both were in the same </form>, so if 1 is bound, 
            # all are bound.
            form1 = forms["cartupdateform"]
            form2 = forms["usercartform"]
            return super().form_valid(form_name=form1.prefix)

    def get_selection(self):
        #selection = Book.objects.filter(id__in=user_cart)
        selection = [(0, "Book0"), (1, "Book1")]
        return selection


# Here we create a formgroup for our next view
FormGroup = make_formgroup(
    "MyFormGroup",
    CartUpdateForm,
    ("usercartform", CartUpdateForm),
)

class FormGroupDemoView(MultiFormsView):
    """
    The make_formgroup function uses a django-betterforms.Multiform
    to wrap multiple forms in a single "form behaving" class. It takes
    an unlimited number of FormClass and/or {"custom_name": FormClass} 
    arguments and returns a FormGroup class. Nothing special really, you
    can make your own function using a django-betterforms.Multiform.

    Just like FormSets, don't forget to provide a "form_name" input in
    the template if you want to use <formgroup_name>_form_valid().
    """
    template_name = "app_name/form_group_demo.html"
    form_classes = [
        CartUpdateForm,
        ("usercartform", CartUpdateForm),

    # don't do this:
    #   ("some_name", MyFormGroup),
    # The name must be the same as the one used at instanciation
        ("myformgroup", FormGroup), # manual naming
    #   FormGroup,                  # automatic naming
    ]

    success_urls = [
        # A FormGroup only needs 1 url
        reverse_lazy("app_name:my_formgroup_view"), 
        reverse_lazy("app_name:my_view"),
        reverse_lazy("app_name:my_other_view"),
    ]
    
    def get_myformgroup_initial(self, form_name):
        # A FormGroup takes a { "formname": {"field_name": value} }
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

    def form_valid(self, forms):
        # Not a formgroup
        if forms["cartupdateform"].is_bound:
            form1 = forms["cartupdateform"]
            form2 = forms["usercartform"]
            return super().form_valid(form_name=form2.prefix)
        

