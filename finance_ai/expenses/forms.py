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
                "min": "0.01",
                "max": "1000000.00",
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

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise ValidationError("Amount is required.")
        if amount <= 0:
            raise ValidationError("Expense amount must be greater than zero.")
        if amount > 1000000:
            raise ValidationError("Expense amount cannot exceed ₹10,00,000.")
        return amount

class MonthFilterForm(forms.Form):
    month = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "month", "class": "form-control"}),
        help_text="Filter by month",
    )

class IncomeForm(forms.ModelForm):
    from .models import Income
    class Meta:
        from .models import Income
        model = Income
        fields = ("date", "source", "amount", "description")
        widgets = {
            "date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "source": forms.Select(attrs={
                "class": "form-select",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "0.00",
                "min": "0.01",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "e.g., Monthly Salary",
                "style": "min-height: 90px; padding: 0.6rem 0.75rem;"
            }),
        }

    def clean_date(self):
        selected_date = self.cleaned_data.get('date')
        if selected_date and selected_date > dt_date.today():
            raise ValidationError("Future dates are not allowed.")
        return selected_date

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise ValidationError("Amount is required.")
        if amount <= 0:
            raise ValidationError("Income amount must be greater than zero.")
        return amount

class SavingGoalForm(forms.ModelForm):
    from .models import SavingGoal
    class Meta:
        from .models import SavingGoal
        model = SavingGoal
        fields = ("title", "target_amount", "saved_amount", "deadline")
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Buy Laptop",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "target_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "0.00",
                "min": "0.01",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "saved_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "0.00",
                "min": "0.00",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
            "deadline": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
                "style": "min-height: 42px; padding: 0.6rem 0.75rem;"
            }),
        }

    def clean_target_amount(self):
        amount = self.cleaned_data.get('target_amount')
        if amount is None:
            raise ValidationError("Target amount is required.")
        if amount <= 0:
            raise ValidationError("Target amount must be greater than zero.")
        return amount

    def clean_saved_amount(self):
        amount = self.cleaned_data.get('saved_amount')
        if amount is None:
            return 0
        if amount < 0:
            raise ValidationError("Saved amount cannot be negative.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        target_amount = cleaned_data.get('target_amount')
        saved_amount = cleaned_data.get('saved_amount')

        if target_amount is not None and saved_amount is not None:
            if saved_amount > target_amount:
                raise ValidationError("Saved amount cannot exceed target amount.")

        deadline = cleaned_data.get('deadline')
        if deadline and deadline <= dt_date.today():
             raise ValidationError("Deadline must be a future date.")

        return cleaned_data

