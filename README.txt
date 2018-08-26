
Here are some info and usage guidelines:

For all Views:
  - A FormClass cannot be used twice unless each duplicate class is 
    given a unique name. This is done by giving a ("name", FormClass)
    tuple instead of a FormClass.

    form_classes = [
        ContactForm,
        ("mycontactform", ContactForm),
        ("i_just_want_to_rename_it", SubscriptionForm),
    ]

  - Use success_url if there is a single succes url, else provide a of 
    urls to listan success_urls, one url per FormClass or tuple.

    success_urls = [
        reverse_lazy("app_name:contact_view"),
        reverse_lazy("app_name:contact_view"),
        reverse_lazy("app_name:my_view")
    ]

    === OR ===

    success_url = reverse_lazy("app_name:my_view")

  - A prefix is automatically assigned to every form based on its class
    name or user defined name, using the format <name>. On POST, a form
    will be assigned POST data if its prefix is found in the POST keys.
    Without this check, every forms would receive POST data, be bound, 
    and thus go through form validation, weither or not they where part 
    of the same </form> tag.


For FormsView:
  - Barebone version, with no <form_name>_method overload support.

  - After a succesfull validation the bound forms are sent to form_valid
    as a dictionnary, where you will have to check which form or forms
    where received.


For MultiFormView:
  - You can overload get_methods initial, prefix and form_kwargs on a 
    per form basis by defining a get_<form's name>_<method name> for it.

  - After form(s) validation, the view iterates through the valid forms'
    name to checks if a corresponding <form name>_form_valid method 
    was defined. It picks the first one it finds, so only 1 method can
    be defined for a group of forms. If no method is found, it calls 
    form_valid (just like FormsView).
