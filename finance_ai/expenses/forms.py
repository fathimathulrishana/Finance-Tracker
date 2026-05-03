from django import forms
from datetime import date as dt_date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Expense


# ─────────────────────────────────────────────────────────────────────────────
# SAFE DECIMAL FIELD
# Replaces Django's standard DecimalField widget with a plain text input so
# that browsers NEVER transmit values in scientific notation (e.g. 9.99997e3).
# Parsing is done exclusively via str → Decimal (never via float) which
# guarantees bit-for-bit accuracy for all monetary amounts.
# ─────────────────────────────────────────────────────────────────────────────

def _parse_decimal(raw_value: str) -> Decimal:
    """
    Safely parse a user-supplied monetary string to an exact Decimal.

    Handles:
      - Plain integers:       '10000'     → Decimal('10000.00')
      - Decimal strings:      '9999.50'   → Decimal('9999.50')
      - Comma-separated:      '1,00,000'  → Decimal('100000.00')
      - Trailing/leading ws:  '  500  '   → Decimal('500.00')

    Raises django.core.exceptions.ValidationError on invalid input.
    Never uses float() at any point.
    """
    if not raw_value:
        raise ValidationError("Amount is required.")

    # Strip whitespace and remove locale-style comma separators
    cleaned = str(raw_value).strip().replace(',', '')

    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValidationError(
            "Enter a valid monetary amount (e.g. 10000 or 9999.50)."
        )

    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class SafeMoneyInput(forms.TextInput):
    """
    A plain <input type="text"> styled as a number field.
    Uses inputmode="decimal" for the numeric keypad on mobile,
    but avoids type="number" which causes browsers to silently
    transmit large numbers in scientific notation (e.g. 9.99997e3).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.setdefault('inputmode', 'decimal')
        self.attrs.setdefault('autocomplete', 'off')
        self.attrs.setdefault('spellcheck', 'false')


class SafeDecimalField(forms.DecimalField):
    """
    Drop-in replacement for forms.DecimalField that:
      1. Renders as SafeMoneyInput (text input, no scientific notation risk)
      2. Parses the POST string via Decimal(str(...)) — never via float
      3. Always quantizes to 2 decimal places before returning
    """
    def __init__(self, *args, **kwargs):
        # Default to SafeMoneyInput unless caller overrides
        kwargs.setdefault('widget', SafeMoneyInput())
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """Override to use our safe parser instead of Django's default path."""
        if value in self.empty_values:
            return None
        return _parse_decimal(str(value))

    def validate(self, value):
        """Skip DecimalField's default float-based range checks; do them cleanly."""
        if value is None and self.required:
            raise ValidationError(self.error_messages['required'])

    def run_validators(self, value):
        """Skip default validators (they use float internally); validation is
        done explicitly in each form's clean_* method."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# SHARED WIDGET ATTRS
# ─────────────────────────────────────────────────────────────────────────────

_MONEY_WIDGET_ATTRS = {
    'placeholder': '0.00',
    'style': 'min-height: 42px; padding: 0.6rem 0.75rem;',
}

_MONEY_WIDGET_ATTRS_LG = {
    'placeholder': '0.00',
    'autofocus': True,
}


# ─────────────────────────────────────────────────────────────────────────────
# FORMS
# ─────────────────────────────────────────────────────────────────────────────

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


class ExpenseForm(forms.ModelForm):
    # Replace the model's default DecimalField widget with SafeDecimalField
    amount = SafeDecimalField(
        widget=SafeMoneyInput(attrs={
            'class': 'form-control',
            **_MONEY_WIDGET_ATTRS,
        }),
    )

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
        if amount > Decimal('1000000.00'):
            raise ValidationError("Expense amount cannot exceed \u20b910,00,000.")
        return amount  # already quantized by SafeDecimalField.to_python()


class MonthFilterForm(forms.Form):
    month = forms.DateField(
        required=False,
        input_formats=["%Y-%m"],
        widget=forms.DateInput(
            format="%Y-%m",
            attrs={"type": "month", "class": "form-control"}
        ),
        help_text="Filter by month",
    )


class IncomeForm(forms.ModelForm):
    from .models import Income
    amount = SafeDecimalField(
        widget=SafeMoneyInput(attrs={
            'class': 'form-control',
            **_MONEY_WIDGET_ATTRS,
        }),
    )

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
        return amount  # already quantized by SafeDecimalField.to_python()


class SavingGoalForm(forms.ModelForm):
    from .models import SavingGoal
    target_amount = SafeDecimalField(
        widget=SafeMoneyInput(attrs={
            'class': 'form-control',
            **_MONEY_WIDGET_ATTRS,
        }),
    )
    saved_amount = SafeDecimalField(
        required=False,
        widget=SafeMoneyInput(attrs={
            'class': 'form-control',
            **_MONEY_WIDGET_ATTRS,
        }),
    )

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
        return amount  # already quantized

    def clean_saved_amount(self):
        amount = self.cleaned_data.get('saved_amount')
        if amount is None:
            return Decimal('0.00')
        if amount < 0:
            raise ValidationError("Saved amount cannot be negative.")
        return amount  # already quantized

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


class DepositForm(forms.Form):
    amount = SafeDecimalField(
        widget=SafeMoneyInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": "e.g. 500",
            "autofocus": True,
        }),
        label=""
    )

    def __init__(self, *args, **kwargs):
        self.goal = kwargs.pop('goal', None)
        super().__init__(*args, **kwargs)

        if self.goal is not None:
            remaining_amount = max(self.goal.target_amount - self.goal.saved_amount, Decimal('0.00'))
            self.fields['amount'].widget.attrs['max'] = f"{remaining_amount:.2f}"

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise ValidationError("Amount is required.")

        if self.goal is not None:
            remaining_amount = self.goal.target_amount - self.goal.saved_amount
            if amount > remaining_amount:
                raise ValidationError("Amount exceeds remaining goal")

        return amount  # already quantized


class BillForm(forms.ModelForm):
    from .models import Bill
    amount = SafeDecimalField(
        widget=SafeMoneyInput(attrs={
            'class': 'form-control',
            **_MONEY_WIDGET_ATTRS,
        }),
    )

    class Meta:
        from .models import Bill
        model = Bill
        fields = ('title', 'category', 'amount', 'due_date')
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Netflix Subscription',
                'style': 'min-height: 42px; padding: 0.6rem 0.75rem;'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'style': 'min-height: 42px; padding: 0.6rem 0.75rem;'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'style': 'min-height: 42px; padding: 0.6rem 0.75rem;'
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError('Amount is required.')
        if amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount  # already quantized


class BudgetForm(forms.ModelForm):
    from .models import Budget
    monthly_budget = SafeDecimalField(
        widget=SafeMoneyInput(attrs={
            'class': 'form-control',
            **_MONEY_WIDGET_ATTRS,
        }),
    )

    class Meta:
        from .models import Budget
        model = Budget
        fields = ('category', 'monthly_budget')
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select',
                'style': 'min-height: 42px; padding: 0.6rem 0.75rem;'
            }),
        }

    def clean_monthly_budget(self):
        amount = self.cleaned_data.get('monthly_budget')
        if amount is None:
            raise forms.ValidationError('Monthly budget is required.')
        if amount <= 0:
            raise forms.ValidationError('Budget must be greater than zero.')
        return amount  # already quantized


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'style': 'min-height: 42px; padding: 0.6rem 0.75rem;'
            })


class ProfileUpdateForm(forms.ModelForm):
    from .models import Profile
    CURRENCY_CHOICES = [
        ('INR', 'Indian Rupee (\u20b9)'),
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (\u20ac)'),
        ('GBP', 'British Pound (\xa3)'),
    ]
    currency = forms.ChoiceField(choices=CURRENCY_CHOICES)

    class Meta:
        from .models import Profile
        model = Profile
        fields = ['profile_image', 'currency']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profile_image'].widget.attrs.update({'class': 'form-control'})
        self.fields['currency'].widget.attrs.update({'class': 'form-select'})
