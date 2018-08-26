from django import forms

class ContactForm(forms.Form):
    title = forms.CharField(max_length=150)
    message = forms.CharField(max_length=200, widget=forms.TextInput)


class SubscriptionForm(forms.Form):
    email = forms.EmailField()

class CartUpdateForm(forms.Form):
    """
    This form has a dynamic number of checkboxes, hence why the overload
    on the __ini__ method.
    """
    ACTIONS = (
        (None, '--------'),
        ('remove', 'Retirer la sélection'),
    )
    action = forms.ChoiceField(choices=ACTIONS)
    selection = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        items = kwargs.pop("selection", None)
        super().__init__(*args, **kwargs)
        if items:
            self.fields["selection"].choices = items
        self.fields["selection"].error_messages.update({
            "invalid_choice": 'Choix checkbox invalide.',
            'required': 'Sélectionnez au moins 1 item.'
        })

    def clean_selection(self):
        selection = self.cleaned_data.get('selection')
        if selection == [] or selection is None:
            raise forms.ValidationError('Vous devez choisir au moins 1 item')
        return selection
