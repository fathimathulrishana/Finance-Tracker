from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Expense


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (css + ' form-control').strip()


from datetime import date as dt_date
from django.core.exceptions import ValidationError

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ("date", "category", "amount", "description")
        widgets = {
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "category": forms.Select(attrs={
                "class": "form-select",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "0.00",
                "min": "0",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "e.g., Lunch at downtown café",
                "style": "min-height: 90px; padding: 0.6rem 0.75rem;"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add an empty choice for Phase 2 Auto Categorization
        choices = [('', '--- Auto Detect ---')] + list(self.fields['category'].choices)
        self.fields['category'].choices = choices
        self.fields['category'].required = False
        
    def clean_date(self):
        """Prevent users from selecting future dates."""
        selected_date = self.cleaned_data.get('date')
        if selected_date and selected_date > dt_date.today():
            raise ValidationError("Future dates are not allowed.")
        return selected_date

class MonthFilterForm(forms.Form):
    month = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "month", "class": "form-control"}),
        help_text="Filter by month",
    )
