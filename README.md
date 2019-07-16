# FormsView and MultiFormView for Django

Create views that can manage more than 1 form, possibly in more than 1 </form> tag.

## Getting Started

Clone or download the repo and add multiforms.py, qualname and django_betterforms to your project

## Info

### Class name retrieval

The python 3.3+ __qualname__ attribut is used to retrieve a FormClass' name. For older versions it 
uses source code inspection, and if that fails it will instanciate a copy of the FormClass and use 
its __name__ instead. If you use python 3.2- and don't want to use the automatic naming system, you 
can simply use a ("name", FormClass) tuples instead of a FormClass to manually assign a name instead.

### Name mangling

A FormClass cannot be used twice unless each duplicate class is given a unique name. This is done by 
giving a ("name", FormClass) tuple instead of a FormClass. Note that if you are using multiple 
duplicates of the same FormClass, a django Formset might be more appropriate.

```
form_classes = [
    ContactForm,
    ("mycontactform", ContactForm),
    ("i_just_want_to_rename_it", SubscriptionForm),
]
```

### Url redirection

Use success_url if there is a single succes url, 
```
success_url = reverse_lazy("app_name:my_view")
```
or success_urls with a list of urls, one per FormClass or tuple.
```
success_urls = [
    reverse_lazy("app_name:contact_view"),
    reverse_lazy("app_name:contact_view"),
    reverse_lazy("app_name:my_view")
]
```

### Use of prefixes

A prefix is automatically assigned to every form based on its class lower case name or user defined name. 
On POST, a form will be assigned POST data if its prefix is found in the POST keys. Without this check, 
every forms would receive POST data, be bound, and thus go through form validation, weither or not they 
where part of the same </form> tag of the submitted form.

## Availlable Classes

### FormsView

- Barebone version, with no <form_name>_method overload support.

- After a succesfull validation the bound forms are sent to form_valid
  as a dictionnary, where you will have to check which form or forms
  where received.
  
```
def form_valid(self, form):
    # We can access individual forms like so:
    form1 = form["usercartform"].cleaned_data.get("action")
    form2 = form["cartupdateform"].cleaned_data.get('title')
    action = form1.cleaned_data.get("action")
    # ...
    return super().form_valid(form)
```

### MultiFormView

You can overload the get_methods initial, prefix and form_kwargs on a per form basis by defining a 
get_<form's name>_<method name> for it.
  
```
class Example(MultiFormView):
    # ...
    form_classes = [
        ContactForm,
        ("mycontactform", ContactForm),
        ("i_just_want_to_rename_it", SubscriptionForm), 
    ]
    # ...
    
    def get_contactform_form_kwargs(self, form_name):
        kwargs = super().get_form_kwargs(form_name)
        kwargs["some_args"] = "some_args"
        return kwargs
```

After form(s) validation, the view uses the valid form's name to checks if a corresponding 
<form name>_form_valid method was defined and call it. 
  
```
def contactform_form_valid(self, form):
    title = form.cleaned_data.get('title')
    print(title)
    return super().form_valid(form) 
```
  
If there are more than 1 valid form (when multiple Form are used in a single </form>), it iterates 
through the form names and picks the first matching method it finds. A form dict containing all valid
forms will be passed as argument, instead of a single form. 

If no method is found, it calls form_valid just like FormsView.

## Installation

Not yet packaged.

## Running the tests

No automated tests yet, maybe one day.

## Deployment

-

## Authors

* **Alexandre Cox** - *Initial work* - [PurpleBooth](https://github.com/PurpleBooth)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments
