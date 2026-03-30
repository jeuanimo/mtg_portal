"""
Forms for the invoicing app.
"""
from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div, HTML, Submit, Field

from apps.crm.models import Organization, Contact
from .models import Invoice, InvoiceItem, Payment, RecurringInvoice, RecurringInvoiceItem


class InvoiceForm(forms.ModelForm):
    """Form for creating and editing invoices."""
    
    class Meta:
        model = Invoice
        fields = [
            'organization', 'contact', 'invoice_number', 
            'issue_date', 'due_date', 'tax_rate', 'discount_amount',
            'discount_description', 'terms', 'notes', 'footer',
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'terms': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'footer': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter contacts based on selected organization
        if self.instance.pk and self.instance.organization:
            self.fields['contact'].queryset = Contact.objects.filter(
                organization=self.instance.organization
            )
        else:
            self.fields['contact'].queryset = Contact.objects.none()
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('organization', css_class='col-md-6'),
                Column('contact', css_class='col-md-6'),
            ),
            Row(
                Column('invoice_number', css_class='col-md-4'),
                Column('issue_date', css_class='col-md-4'),
                Column('due_date', css_class='col-md-4'),
            ),
            Row(
                Column('tax_rate', css_class='col-md-4'),
                Column('discount_amount', css_class='col-md-4'),
                Column('discount_description', css_class='col-md-4'),
            ),
            'terms',
            'notes',
            'footer',
        )


class InvoiceItemForm(forms.ModelForm):
    """Form for invoice line items."""
    
    class Meta:
        model = InvoiceItem
        fields = ['description', 'quantity', 'unit_price']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }


# Formset for invoice items
InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class QuickInvoiceForm(forms.Form):
    """Quick form for creating simple invoices."""
    
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    description = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service description'}),
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
    )
    due_days = forms.ChoiceField(
        choices=[
            (15, 'Net 15'),
            (30, 'Net 30'),
            (60, 'Net 60'),
            (90, 'Net 90'),
        ],
        initial=30,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'organization',
            'description',
            Row(
                Column('amount', css_class='col-md-6'),
                Column('due_days', css_class='col-md-6'),
            ),
            Submit('submit', 'Create Invoice', css_class='btn btn-primary'),
        )
    
    def create_invoice(self, user):
        """Create invoice from form data."""
        from datetime import date, timedelta
        
        org = self.cleaned_data['organization']
        due_days = int(self.cleaned_data['due_days'])
        
        invoice = Invoice.objects.create(
            organization=org,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=due_days),
            created_by=user,
        )
        
        InvoiceItem.objects.create(
            invoice=invoice,
            description=self.cleaned_data['description'],
            quantity=1,
            unit_price=self.cleaned_data['amount'],
        )
        
        return invoice


class PaymentForm(forms.ModelForm):
    """Form for recording manual payments."""
    
    class Meta:
        model = Payment
        fields = ['amount', 'method', 'reference_number', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        
        # Set initial amount to remaining balance
        if invoice:
            self.fields['amount'].initial = invoice.balance_due
        
        # Exclude Stripe from manual payment options
        self.fields['method'].choices = [
            (k, v) for k, v in Payment.Method.choices if k != 'stripe'
        ]
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('amount', css_class='col-md-6'),
                Column('method', css_class='col-md-6'),
            ),
            'reference_number',
            'notes',
            Submit('submit', 'Record Payment', css_class='btn btn-success'),
        )


class RecurringInvoiceForm(forms.ModelForm):
    """Form for creating recurring invoices."""
    
    class Meta:
        model = RecurringInvoice
        fields = [
            'name', 'organization', 'contact', 'frequency',
            'start_date', 'end_date', 'days_until_due', 'tax_rate', 'terms',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'terms': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'name',
            Row(
                Column('organization', css_class='col-md-6'),
                Column('contact', css_class='col-md-6'),
            ),
            Row(
                Column('frequency', css_class='col-md-4'),
                Column('start_date', css_class='col-md-4'),
                Column('end_date', css_class='col-md-4'),
            ),
            Row(
                Column('days_until_due', css_class='col-md-6'),
                Column('tax_rate', css_class='col-md-6'),
            ),
            'terms',
        )


class RecurringInvoiceItemForm(forms.ModelForm):
    """Form for recurring invoice line items."""
    
    class Meta:
        model = RecurringInvoiceItem
        fields = ['description', 'quantity', 'unit_price']


RecurringInvoiceItemFormSet = inlineformset_factory(
    RecurringInvoice,
    RecurringInvoiceItem,
    form=RecurringInvoiceItemForm,
    extra=2,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class InvoiceEmailForm(forms.Form):
    """Form for sending invoice by email."""
    
    to_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    cc_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
    )
    attach_pdf = forms.BooleanField(
        initial=True,
        required=False,
        label='Attach PDF',
    )
    
    def __init__(self, invoice=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if invoice:
            # Pre-fill with invoice details
            if invoice.contact and invoice.contact.email:
                self.fields['to_email'].initial = invoice.contact.email
            elif invoice.organization.email:
                self.fields['to_email'].initial = invoice.organization.email
            
            self.fields['subject'].initial = f"Invoice #{invoice.invoice_number} from Mitchell Technology Group"
            self.fields['message'].initial = f"""Dear {invoice.organization.name},

Please find attached Invoice #{invoice.invoice_number} for ${invoice.total}.

Payment is due by {invoice.due_date.strftime('%B %d, %Y')}.

If you have any questions, please don't hesitate to contact us.

Best regards,
Mitchell Technology Group"""


class InvoiceFilterForm(forms.Form):
    """Form for filtering invoices."""
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(Invoice.Status.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.all(),
        required=False,
        empty_label='All Organizations',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search invoice number...',
        }),
    )
